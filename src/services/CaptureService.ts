/**
 * CaptureService - Wraps ai_agent_demo_complete.py for browser automation
 */

import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import * as path from 'path';
import {
  CaptureService as ICaptureService,
  CaptureResult,
  ValidationResult,
  ValidationIssue
} from '../types/services';
import { CaptureConfig, TimelineData } from '../types/demo';
import { Logger } from '../core/Logger';

export class CaptureService implements ICaptureService {
  private readonly scriptPath: string;
  private readonly logger: Logger;

  constructor(
    scriptPath: string = path.join(process.cwd(), 'product-demo-videos', 'scripts', 'ai_agent_demo_complete.py'),
    logger?: Logger
  ) {
    this.scriptPath = scriptPath;
    this.logger = logger || new Logger('CaptureService');
  }

  async record(config: CaptureConfig): Promise<CaptureResult> {
    this.logger.info('Starting demo capture', { scenario: config.scenario, url: config.url });

    // Set environment variables for the Python script
    const env = {
      ...process.env,
      DTS_SESSIONID: config.session_credentials?.cookie_value || process.env.DTS_SESSIONID,
      VOICEOVER_ENABLED: 'false', // Disable voiceover for capture-only
      HEADLESS: config.headless ? 'true' : 'false'
    };

    // Build command arguments
    const args = ['auto'];

    if (config.headless) {
      args[0] = 'headless';
    }

    return new Promise((resolve, reject) => {
      this.logger.debug('Executing Python capture script', { script: this.scriptPath, args });

      const pythonProcess = spawn('python3', [this.scriptPath, ...args], {
        cwd: path.dirname(this.scriptPath),
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

      pythonProcess.on('close', async (code) => {
        if (code !== 0) {
          this.logger.error('Capture script failed', { code, stderr });
          reject(new Error(`Capture failed with exit code ${code}: ${stderr}`));
          return;
        }

        try {
          const result = await this.parseCaptureResult(stdout, stderr);
          this.logger.info('Capture completed successfully', {
            videoPath: result.video_url,
            duration: result.metadata.duration,
            markers: Object.keys(result.timeline.markers).length
          });
          resolve(result);
        } catch (error: unknown) {
          const err = error instanceof Error ? error : new Error(String(error));
          this.logger.error('Failed to parse capture result', { error: err.message });
          reject(err);
        }
      });

      pythonProcess.on('error', (error) => {
        this.logger.error('Failed to start capture process', { error: error.message });
        reject(error);
      });
    });
  }

  async validate(result: CaptureResult): Promise<ValidationResult> {
    const issues: ValidationIssue[] = [];

    // Check video file exists and is readable
    try {
      await fs.access(result.video_url);
    } catch {
      issues.push({
        type: 'error',
        field: 'video_url',
        message: 'Video file does not exist or is not accessible',
        suggestion: 'Check file permissions and storage configuration'
      });
    }

    // Validate timeline markers
    const markers = result.timeline.markers;
    const requiredMarkers = ['t_start_recording', 't_page_loaded', 't_end_recording'];

    for (const marker of requiredMarkers) {
      if (!(marker in markers)) {
        issues.push({
          type: 'error',
          field: 'timeline',
          message: `Required marker '${marker}' is missing`,
          suggestion: 'Ensure the capture script runs to completion'
        });
      }
    }

    // Check for reasonable duration
    if (result.metadata.duration < 10) {
      issues.push({
        type: 'warning',
        field: 'duration',
        message: `Video duration (${result.metadata.duration}s) seems too short`,
        suggestion: 'Verify the demo scenario completed successfully'
      });
    }

    if (result.metadata.duration > 600) { // 10 minutes
      issues.push({
        type: 'warning',
        field: 'duration',
        message: `Video duration (${result.metadata.duration}s) is very long`,
        suggestion: 'Consider using compression strategies for long recordings'
      });
    }

    // Check marker ordering
    const markerTimes = Object.values(markers);
    const sortedTimes = [...markerTimes].sort((a, b) => a - b);

    if (JSON.stringify(markerTimes) !== JSON.stringify(sortedTimes)) {
      issues.push({
        type: 'warning',
        field: 'timeline',
        message: 'Timeline markers are not in chronological order',
        suggestion: 'Review marker extraction logic'
      });
    }

    const score = Math.max(0, 1 - (issues.length * 0.2));

    return {
      isValid: issues.filter(i => i.type === 'error').length === 0,
      issues,
      score
    };
  }

  private async parseCaptureResult(stdout: string, stderr: string): Promise<CaptureResult> {
    // Parse the output to find video and timeline files
    const videoDir = path.join(process.cwd(), 'product-demo-videos', 'videos');
    const processedDir = path.join(videoDir, 'processed');

    // Look for the most recent video file
    const videoFiles = await fs.readdir(path.join(processedDir));
    const mp4Files = videoFiles
      .filter(f => f.endsWith('.mp4') && !f.includes('.voice'))
      .sort()
      .reverse();

    if (mp4Files.length === 0) {
      throw new Error('No video file found after capture');
    }

    const latestVideo = path.join(processedDir, mp4Files[0]);
    const videoStats = await fs.stat(latestVideo);

    // Find corresponding timeline file
    const timelineDir = path.join(processedDir, 'timeline');
    const timelineFiles = await fs.readdir(timelineDir);
    const jsonFiles = timelineFiles
      .filter(f => f.endsWith('.json'))
      .sort()
      .reverse();

    if (jsonFiles.length === 0) {
      throw new Error('No timeline file found after capture');
    }

    const latestTimeline = path.join(timelineDir, jsonFiles[0]);
    const timelineContent = await fs.readFile(latestTimeline, 'utf-8');
    const timelineData: TimelineData = JSON.parse(timelineContent);

    // Extract video metadata using ffprobe (simplified)
    const duration = timelineData.markers.t_end_recording || 0;

    return {
      video_url: latestVideo,
      timeline: timelineData,
      metadata: {
        duration,
        resolution: { width: 1920, height: 1080 }, // Default, could be extracted
        fps: 30, // Default
        file_size_bytes: videoStats.size
      }
    };
  }
}