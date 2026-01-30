/**
 * NarrationService - Handles audio generation and caption creation
 */

import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import * as path from 'path';
import {
  NarrationService as INarrationService,
  NarrationResult,
  AudioSegment
} from '../types/services';
import { NarrationConfig, NarrationSegment, TimelineData } from '../types/demo';
import { Logger } from '../core/Logger';

export class NarrationService implements INarrationService {
  private readonly scriptDir: string;
  private readonly logger: Logger;

  constructor(
    scriptDir: string = path.join(process.cwd(), 'product-demo-videos', 'scripts'),
    logger?: Logger
  ) {
    this.scriptDir = scriptDir;
    this.logger = logger || new Logger('NarrationService');
  }

  async generate(config: NarrationConfig, timeline: TimelineData): Promise<NarrationResult> {
    this.logger.info('Starting narration generation', {
      segments: config.segments.length,
      provider: config.voice.provider
    });

    // Write narration config to temporary file
    const configPath = await this.writeNarrationConfig(config);
    const audioSegments: AudioSegment[] = [];

    try {
      // Generate audio for each segment
      for (const segment of config.segments) {
        const audioSegment = await this.generateSegmentAudio(segment, config.voice);
        audioSegments.push(audioSegment);
      }

      // Generate captions if requested
      let captionsSrt: string | undefined;
      if (config.include_captions) {
        captionsSrt = await this.generateCaptions(config.segments, timeline);
      }

      const totalDuration = audioSegments.reduce((sum, seg) => sum + seg.duration, 0);

      this.logger.info('Narration generation completed', {
        segmentsGenerated: audioSegments.length,
        totalDuration,
        captionsGenerated: !!captionsSrt
      });

      return {
        audio_segments: audioSegments,
        total_duration: totalDuration,
        captions_srt: captionsSrt
      };

    } finally {
      // Clean up temporary config file
      try {
        await fs.unlink(configPath);
      } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : String(error);
        this.logger.warn('Failed to clean up temporary config file', { error: msg });
      }
    }
  }

  async generateCaptions(segments: NarrationSegment[], timeline: TimelineData): Promise<string> {
    this.logger.debug('Generating SRT captions', { segmentCount: segments.length });

    const srtEntries: string[] = [];

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      const markerTime = timeline.markers[segment.anchor];

      if (markerTime === undefined) {
        this.logger.warn(`Marker ${segment.anchor} not found in timeline, skipping segment`);
        continue;
      }

      const startTime = markerTime + segment.offset_s;
      const endTime = startTime + 3.0; // Estimate 3 seconds per segment, could be improved

      const startTimestamp = this.formatSrtTimestamp(startTime);
      const endTimestamp = this.formatSrtTimestamp(endTime);

      srtEntries.push(`${i + 1}\n${startTimestamp} --> ${endTimestamp}\n${segment.text}\n`);
    }

    return srtEntries.join('\n');
  }

  private async generateSegmentAudio(segment: NarrationSegment, voice: NarrationConfig['voice']): Promise<AudioSegment> {
    // For now, we'll use the existing elevenlabs_tts.py script
    // In the future, this could be enhanced with caching and direct API calls

    const audioDir = path.join(process.cwd(), 'product-demo-videos', 'videos', 'processed', 'audio_segments');
    await fs.mkdir(audioDir, { recursive: true });

    const audioPath = path.join(audioDir, `${segment.id}.mp3`);

    // Check if audio already exists (caching)
    try {
      await fs.access(audioPath);
      const stats = await fs.stat(audioPath);
      if (stats.size > 0) {
        this.logger.debug(`Using cached audio for segment ${segment.id}`);
        return {
          id: segment.id,
          audio_url: audioPath,
          start_time: 0, // Will be calculated based on timeline
          duration: 3.0, // Estimate, could be calculated from actual audio
          text: segment.text
        };
      }
    } catch {
      // File doesn't exist, generate it
    }

    // Generate audio using elevenlabs script
    const env = {
      ...process.env,
      ELEVENLABS_API_KEY: process.env.ELEVENLABS_API_KEY || '',
      VOICE_ID: voice.voice_id
    };

    return new Promise((resolve, reject) => {
      const pythonProcess = spawn('python3', [
        path.join(this.scriptDir, 'elevenlabs_tts.py'),
        '--text', segment.text,
        '--output', audioPath
      ], {
        cwd: this.scriptDir,
        env,
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stderr = '';

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      pythonProcess.on('close', async (code) => {
        if (code !== 0) {
          this.logger.error(`Audio generation failed for segment ${segment.id}`, { code, stderr });
          reject(new Error(`Audio generation failed: ${stderr}`));
          return;
        }

        try {
          // Get actual duration (simplified - could use ffprobe)
          const duration = await this.getAudioDuration(audioPath);

          resolve({
            id: segment.id,
            audio_url: audioPath,
            start_time: 0, // Will be set by timeline calculation
            duration,
            text: segment.text
          });
        } catch (error) {
          reject(error);
        }
      });

      pythonProcess.on('error', (error) => {
        this.logger.error(`Failed to start audio generation for segment ${segment.id}`, { error: error.message });
        reject(error);
      });
    });
  }

  private async writeNarrationConfig(config: NarrationConfig): Promise<string> {
    const configPath = path.join(process.cwd(), 'temp', `narration_config_${Date.now()}.json`);
    await fs.mkdir(path.dirname(configPath), { recursive: true });

    const configData = {
      segments: config.segments,
      conditional_segments: config.conditional_segments || [],
      filler_segments: config.filler_segments || [],
      voice: config.voice
    };

    await fs.writeFile(configPath, JSON.stringify(configData, null, 2), 'utf-8');
    return configPath;
  }

  private formatSrtTimestamp(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const milliseconds = Math.floor((seconds % 1) * 1000);

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${milliseconds.toString().padStart(3, '0')}`;
  }

  private async getAudioDuration(audioPath: string): Promise<number> {
    // Simplified duration estimation - in production, use ffprobe
    // For now, estimate based on text length (rough approximation)
    try {
      const stats = await fs.stat(audioPath);
      // Rough estimation: ~150 words per minute, ~2.5 words per second
      // This should be replaced with actual audio duration detection
      return Math.max(2.0, Math.min(10.0, stats.size / 50000)); // Rough heuristic
    } catch {
      return 3.0; // Default fallback
    }
  }
}