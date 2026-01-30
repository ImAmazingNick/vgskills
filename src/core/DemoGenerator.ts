/**
 * Main facade for demo generation - orchestrates all services
 */

import {
  DemoConfig,
  DemoResult,
  JobProgress,
  JobStatus
} from '../types/demo';
import {
  CaptureService,
  NarrationService,
  CompositionService,
  QualityService,
  ProgressObserver
} from '../types/services';
import { Logger } from './Logger';

export class DemoGenerator {
  constructor(
    private captureService: CaptureService,
    private narrationService: NarrationService,
    private compositionService: CompositionService,
    private qualityService: QualityService,
    private logger: Logger = new Logger('DemoGenerator')
  ) {}

  /**
   * Generate a complete demo video from configuration
   */
  async generateDemo(config: DemoConfig, observer?: ProgressObserver): Promise<DemoResult> {
    const startTime = Date.now();
    const jobId = config.id;

    this.logger.info(`Starting demo generation`, { jobId, scenario: config.scenario });

    try {
      // Phase 1: Capture
      this.notifyProgress(observer, {
        job_id: jobId,
        status: 'capturing',
        progress: 0.1,
        stage: 'capture',
        message: 'Recording browser session and extracting timeline markers',
        current_step: 1,
        total_steps: 5
      });

      const captureResult = await this.captureService.record(config.capture);

      // Validate capture quality
      const captureValidation = await this.captureService.validate(captureResult);
      if (!captureValidation.isValid) {
        this.logger.warn(`Capture validation issues`, { issues: captureValidation.issues });
      }

      // Phase 2: Narration
      this.notifyProgress(observer, {
        job_id: jobId,
        status: 'narrating',
        progress: 0.3,
        stage: 'narration',
        message: 'Generating audio narration and captions',
        current_step: 2,
        total_steps: 5
      });

      const narrationResult = await this.narrationService.generate(
        config.narration,
        captureResult.timeline
      );

      // Phase 3: Composition
      this.notifyProgress(observer, {
        job_id: jobId,
        status: 'composing',
        progress: 0.6,
        stage: 'composition',
        message: 'Composing final video with effects and synchronization',
        current_step: 3,
        total_steps: 5
      });

      const compositionAssets = {
        video_url: captureResult.video_url,
        audio_segments: narrationResult.audio_segments,
        timeline: captureResult.timeline,
        effects: config.composition.effects
      };

      const compositionResult = await this.compositionService.compose(
        compositionAssets,
        config.composition
      );

      // Phase 4: Quality Validation
      this.notifyProgress(observer, {
        job_id: jobId,
        status: 'post_processing',
        progress: 0.9,
        stage: 'validation',
        message: 'Validating final video quality and synchronization',
        current_step: 4,
        total_steps: 5
      });

      // Validate final composition
      const compositionValidation = await this.compositionService.validate(compositionResult);
      const syncValidation = await this.qualityService.validateSync(
        compositionResult.video_url,
        narrationResult.audio_segments
      );

      const qualityMetrics = this.qualityService.calculateMetrics({
        id: jobId,
        video_url: compositionResult.video_url,
        timeline_url: '', // Will be set below
        duration: compositionResult.duration,
        size_bytes: compositionResult.file_size_bytes,
        metadata: {
          scenario: config.scenario,
          enhancements_used: config.ai_enhancements || [],
          generation_time_s: (Date.now() - startTime) / 1000,
          quality_metrics: compositionResult.quality_metrics
        }
      });

      // Phase 5: Finalize
      const result: DemoResult = {
        id: jobId,
        video_url: compositionResult.video_url,
        timeline_url: captureResult.timeline.metadata?.generated_at || '',
        captions_url: narrationResult.captions_srt ? `captions/${jobId}.srt` : undefined,
        duration: compositionResult.duration,
        size_bytes: compositionResult.file_size_bytes,
        metadata: {
          scenario: config.scenario,
          enhancements_used: config.ai_enhancements || [],
          generation_time_s: (Date.now() - startTime) / 1000,
          quality_metrics: qualityMetrics
        }
      };

      this.notifyProgress(observer, {
        job_id: jobId,
        status: 'completed',
        progress: 1.0,
        stage: 'complete',
        message: 'Demo generation completed successfully',
        current_step: 5,
        total_steps: 5
      });

      this.logger.info(`Demo generation completed`, {
        jobId,
        duration: result.metadata.generation_time_s,
        videoSize: result.size_bytes
      });

      observer?.onComplete(result);
      return result;

    } catch (error: unknown) {
      const err = error instanceof Error ? error : new Error(String(error));
      this.logger.error(`Demo generation failed`, { jobId, error: err.message });

      this.notifyProgress(observer, {
        job_id: jobId,
        status: 'failed',
        progress: 0,
        stage: 'error',
        message: `Generation failed: ${err.message}`
      });

      observer?.onError(err);
      throw err;
    }
  }

  private notifyProgress(observer: ProgressObserver | undefined, progress: JobProgress): void {
    if (observer) {
      observer.onProgress(progress);
    }
  }

  /**
   * Get current job status (for async monitoring)
   */
  getJobStatus(jobId: string): Promise<JobProgress> {
    // In a real implementation, this would check a job store
    throw new Error('Async job monitoring not implemented yet');
  }

  /**
   * Cancel a running job
   */
  cancelJob(jobId: string): Promise<void> {
    // In a real implementation, this would signal cancellation
    throw new Error('Job cancellation not implemented yet');
  }
}