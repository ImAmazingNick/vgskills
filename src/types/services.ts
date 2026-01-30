/**
 * Service layer interfaces for the video demo pipeline
 */

import {
  CaptureConfig,
  NarrationConfig,
  CompositionConfig,
  TimelineData,
  DemoResult,
  QualityMetrics,
  NarrationSegment,
  JobProgress,
  EffectConfig
} from './demo';

export interface CaptureService {
  /**
   * Record a demo session and extract timeline markers
   */
  record(config: CaptureConfig): Promise<CaptureResult>;

  /**
   * Validate capture result quality
   */
  validate(result: CaptureResult): Promise<ValidationResult>;
}

export interface CaptureResult {
  video_url: string;
  timeline: TimelineData;
  metadata: {
    duration: number;
    resolution: { width: number; height: number };
    fps: number;
    file_size_bytes: number;
  };
}

export interface NarrationService {
  /**
   * Generate audio narration from segments
   */
  generate(config: NarrationConfig, timeline: TimelineData): Promise<NarrationResult>;

  /**
   * Generate SRT captions from narration segments
   */
  generateCaptions(segments: NarrationSegment[], timeline: TimelineData): Promise<string>;
}

export interface NarrationResult {
  audio_segments: AudioSegment[];
  total_duration: number;
  captions_srt?: string;
}

export interface AudioSegment {
  id: string;
  audio_url: string;
  start_time: number; // seconds
  duration: number;
  text: string;
}

export interface CompositionService {
  /**
   * Compose final video from assets
   */
  compose(assets: CompositionAssets, config: CompositionConfig): Promise<CompositionResult>;

  /**
   * Validate composition result
   */
  validate(result: CompositionResult): Promise<ValidationResult>;
}

export interface CompositionAssets {
  video_url: string;
  audio_segments: AudioSegment[];
  timeline: TimelineData;
  effects?: EffectConfig[];
}

export interface CompositionResult {
  video_url: string;
  duration: number;
  file_size_bytes: number;
  quality_metrics: QualityMetrics;
}

export interface QualityService {
  /**
   * Validate timeline marker alignment
   */
  validateTimeline(timeline: TimelineData): ValidationResult;

  /**
   * Check audio-video synchronization
   */
  validateSync(video: string, audio: AudioSegment[]): Promise<SyncValidation>;

  /**
   * Calculate quality metrics
   */
  calculateMetrics(result: DemoResult): QualityMetrics;
}

export interface ValidationResult {
  isValid: boolean;
  issues: ValidationIssue[];
  score: number; // 0-1
}

export interface ValidationIssue {
  type: 'error' | 'warning';
  field: string;
  message: string;
  suggestion?: string;
}

export interface SyncValidation {
  max_drift_ms: number;
  average_drift_ms: number;
  sync_score: number; // 0-1
  issues: SyncIssue[];
}

export interface SyncIssue {
  segment_id: string;
  expected_time: number;
  actual_time: number;
  drift_ms: number;
  severity: 'low' | 'medium' | 'high';
}

export interface ProgressObserver {
  onProgress(progress: JobProgress): void;
  onComplete(result: DemoResult): void;
  onError(error: Error): void;
}

export interface CacheService {
  /**
   * Get cached item
   */
  get<T>(key: string): Promise<T | null>;

  /**
   * Set cached item
   */
  set<T>(key: string, value: T, ttl?: number): Promise<void>;

  /**
   * Check if item exists in cache
   */
  exists(key: string): Promise<boolean>;

  /**
   * Clear cache
   */
  clear(pattern?: string): Promise<void>;
}

export interface StorageService {
  /**
   * Upload file to storage
   */
  upload(filePath: string, key: string, metadata?: Record<string, any>): Promise<string>;

  /**
   * Download file from storage
   */
  download(key: string, destination: string): Promise<void>;

  /**
   * Get signed URL for file access
   */
  getSignedUrl(key: string, expiresIn?: number): Promise<string>;

  /**
   * Delete file from storage
   */
  delete(key: string): Promise<void>;
}