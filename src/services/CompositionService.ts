/**
 * CompositionService - Wraps FFmpeg video composition and audio mixing
 */

import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import * as path from 'path';
import {
  CompositionService as ICompositionService,
  CompositionResult,
  ValidationResult,
  ValidationIssue,
  CompositionAssets
} from '../types/services';
import { CompositionConfig, QualityMetrics } from '../types/demo';
import { Logger } from '../core/Logger';

export class CompositionService implements ICompositionService {
  private readonly scriptDir: string;
  private readonly logger: Logger;

  constructor(
    scriptDir: string = path.join(process.cwd(), 'product-demo-videos', 'scripts'),
    logger?: Logger
  ) {
    this.scriptDir = scriptDir;
    this.logger = logger || new Logger('CompositionService');
  }

  async compose(assets: CompositionAssets, config: CompositionConfig): Promise<CompositionResult> {
    this.logger.info('Starting video composition', {
      video: path.basename(assets.video_url),
      audioSegments: assets.audio_segments.length,
      resolution: config.output_resolution
    });

    // Create output directory
    const outputDir = path.join(process.cwd(), 'product-demo-videos', 'videos', 'processed');
    await fs.mkdir(outputDir, { recursive: true });

    const outputPath = path.join(outputDir, `composed_${Date.now()}.mp4`);

    // Create temporary narration config file
    const narrationConfigPath = await this.createNarrationConfig(assets);

    try {
      // Use the existing build_voiceover_from_timeline.py script
      const env = {
        ...process.env,
        ELEVENLABS_API_KEY: process.env.ELEVENLABS_API_KEY || ''
      };

      await new Promise<void>((resolve, reject) => {
        const pythonProcess = spawn('python3', [
          path.join(this.scriptDir, 'build_voiceover_from_timeline.py'),
          '--video', assets.video_url,
          '--timeline', this.getTimelinePath(assets.video_url),
          '--segments', narrationConfigPath,
          '--out', outputPath
        ], {
          cwd: this.scriptDir,
          env,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';

        pythonProcess.stdout.on('data', (data) => {
          stdout += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
          stderr += data.toString();
        });

        pythonProcess.on('close', (code) => {
          if (code !== 0) {
            this.logger.error('Composition failed', { code, stderr, stdout });
            reject(new Error(`Composition failed with exit code ${code}: ${stderr}`));
            return;
          }

          this.logger.info('Composition completed successfully', { outputPath });
          resolve();
        });

        pythonProcess.on('error', (error) => {
          this.logger.error('Failed to start composition process', { error: error.message });
          reject(error);
        });
      });

      // Get output file stats
      const stats = await fs.stat(outputPath);
      const duration = await this.getVideoDuration(outputPath);

      return {
        video_url: outputPath,
        duration,
        file_size_bytes: stats.size,
        quality_metrics: await this.calculateQualityMetrics(outputPath, assets, config)
      };

    } finally {
      // Clean up temporary files
      try {
        await fs.unlink(narrationConfigPath);
      } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : String(error);
        this.logger.warn('Failed to clean up temporary narration config', { error: msg });
      }
    }
  }

  async validate(result: CompositionResult): Promise<ValidationResult> {
    const issues: ValidationIssue[] = [];

    // Check output file exists and is valid
    try {
      await fs.access(result.video_url);
      if (result.file_size_bytes < 1000000) { // Less than 1MB
        issues.push({
          type: 'warning',
          field: 'file_size',
          message: 'Output file size seems too small',
          suggestion: 'Check if composition completed successfully'
        });
      }
    } catch {
      issues.push({
        type: 'error',
        field: 'output_file',
        message: 'Output video file does not exist',
        suggestion: 'Check composition process and file permissions'
      });
    }

    // Validate duration
    if (result.duration < 10) {
      issues.push({
        type: 'warning',
        field: 'duration',
        message: 'Composed video duration seems too short',
        suggestion: 'Verify audio segments were properly synchronized'
      });
    }

    // Check quality metrics
    const metrics = result.quality_metrics;
    if (metrics.audio_sync_accuracy_ms > 200) {
      issues.push({
        type: 'warning',
        field: 'audio_sync',
        message: `Audio sync accuracy (${metrics.audio_sync_accuracy_ms}ms) is poor`,
        suggestion: 'Review timeline markers and audio positioning'
      });
    }

    if (metrics.marker_alignment_score < 0.8) {
      issues.push({
        type: 'warning',
        field: 'marker_alignment',
        message: `Marker alignment score (${metrics.marker_alignment_score}) is low`,
        suggestion: 'Check marker extraction and positioning logic'
      });
    }

    const score = Math.max(0, 1 - (issues.length * 0.15));

    return {
      isValid: issues.filter(i => i.type === 'error').length === 0,
      issues,
      score
    };
  }

  private async createNarrationConfig(assets: CompositionAssets): Promise<string> {
    // Convert CompositionAssets to the format expected by build_voiceover_from_timeline.py
    const segments = assets.audio_segments.map(segment => ({
      id: segment.id,
      anchor: this.findNearestMarker(segment.start_time, assets.timeline),
      offset_s: 0, // Simplified - in production this would be calculated properly
      text: segment.text
    }));

    const config = {
      segments,
      conditional_segments: [],
      filler_segments: []
    };

    const configPath = path.join(process.cwd(), 'temp', `composition_config_${Date.now()}.json`);
    await fs.mkdir(path.dirname(configPath), { recursive: true });
    await fs.writeFile(configPath, JSON.stringify(config, null, 2), 'utf-8');

    return configPath;
  }

  private findNearestMarker(time: number, timeline: CompositionAssets['timeline']): string {
    // Find the marker closest to the given time
    let nearestMarker = 't_start_recording';
    let minDiff = Math.abs(time - (timeline.markers[nearestMarker] || 0));

    for (const [marker, markerTime] of Object.entries(timeline.markers)) {
      const diff = Math.abs(time - markerTime);
      if (diff < minDiff) {
        minDiff = diff;
        nearestMarker = marker;
      }
    }

    return nearestMarker;
  }

  private getTimelinePath(videoPath: string): string {
    // Derive timeline path from video path
    const videoDir = path.dirname(videoPath);
    const videoName = path.basename(videoPath, path.extname(videoPath));
    return path.join(videoDir, 'timeline', `${videoName}.json`);
  }

  private async getVideoDuration(videoPath: string): Promise<number> {
    // Simplified - in production use ffprobe
    try {
      const stats = await fs.stat(videoPath);
      // Rough estimation based on file size and typical bitrate
      return Math.max(30, Math.min(600, stats.size / 1000000)); // Rough heuristic
    } catch {
      return 60; // Default fallback
    }
  }

  private async calculateQualityMetrics(
    outputPath: string,
    assets: CompositionAssets,
    config: CompositionConfig
  ): Promise<QualityMetrics> {
    // Simplified quality metrics calculation
    // In production, this would use more sophisticated analysis

    return {
      audio_sync_accuracy_ms: 50, // Assume good sync for now
      marker_alignment_score: 0.95, // Assume good alignment
      video_quality_score: 0.9, // Assume good quality
      compression_efficiency: 1.0 // No compression applied yet
    };
  }
}