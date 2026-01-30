/**
 * Core demo generation types and interfaces
 */

export interface TimelineMarker {
  id: string;
  timestamp: number; // seconds from start
  type: 'user_action' | 'system_event' | 'milestone';
  description: string;
  metadata?: Record<string, any>;
}

export interface TimelineData {
  markers: Record<string, number>; // marker_id -> timestamp
  duration?: number;
  metadata?: {
    scenario?: string;
    version?: string;
    generated_at?: string;
  };
}

export interface NarrationSegment {
  id: string;
  anchor: string; // timeline marker id
  offset_s: number; // seconds from anchor
  text: string;
  voice?: VoiceConfig;
  timing?: {
    duration?: number;
    emphasis?: EmphasisConfig[];
  };
}

export interface NarrationConfig {
  segments: NarrationSegment[];
  conditional_segments?: ConditionalSegment[];
  filler_segments?: FillerSegment[];
  voice: VoiceConfig;
  include_captions?: boolean;
}

export interface ConditionalSegment extends NarrationSegment {
  condition: SegmentCondition;
  repeatable?: boolean;
  max_repeats?: number;
  repeat_interval_s?: number;
}

export interface FillerSegment {
  id: string;
  text: string;
  duration_s: number;
}

export interface SegmentCondition {
  type: 'duration_between' | 'marker_exists' | 'activity_level';
  start_marker?: string;
  end_marker?: string;
  min_duration_s?: number;
  marker_id?: string;
  min_activity?: number;
}

export interface VoiceConfig {
  provider: 'elevenlabs' | 'varg';
  voice_id: string;
  model?: string;
  settings?: {
    stability?: number; // 0-1
    similarity?: number; // 0-1
    style?: number; // 0-1
  };
  language?: string;
}

export interface EmphasisConfig {
  start: number; // relative to segment start
  end: number;
  intensity: number; // 0-1
}

export interface CaptureConfig {
  url: string;
  scenario: DemoScenario;
  session_credentials?: SessionCredentials;
  resolution?: Resolution;
  fps?: number;
  headless?: boolean;
  incognito?: boolean;
  timeout_s?: number;
}

export interface SessionCredentials {
  cookie_name: string;
  cookie_value: string;
  domain: string;
}

export type Resolution = '720p' | '1080p' | '4k';

export type DemoScenario =
  | 'ai_agent_demo'
  | 'feature_walkthrough'
  | 'api_demo'
  | 'custom';

export interface CompositionConfig {
  output_resolution: Resolution;
  effects?: EffectConfig[];
  branding?: BrandingConfig;
  compression_strategy?: CompressionStrategy;
}

export interface EffectConfig {
  type: 'zoom' | 'pan' | 'highlight' | 'transition';
  timing: {
    start: number; // frame
    duration: number; // frames
    easing?: EasingFunction;
  };
  parameters: Record<string, any>;
}

export interface BrandingConfig {
  logo?: {
    url: string;
    position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
    size: { width: number; height: number };
  };
  colors?: {
    primary: string;
    secondary: string;
  };
  watermark?: {
    text: string;
    opacity: number;
  };
}

export type EasingFunction = 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';

export type CompressionStrategy =
  | 'no_compression'
  | 'speed_ramp'
  | 'selective_compression'
  | 'editorial_cuts'
  | 'ai_presenter';

export interface DemoConfig {
  id: string;
  scenario: DemoScenario;
  capture: CaptureConfig;
  narration: NarrationConfig;
  composition: CompositionConfig;
  ai_enhancements?: AIEnhancement[];
  metadata?: {
    title?: string;
    description?: string;
    tags?: string[];
    created_by?: string;
  };
}

export type AIEnhancement =
  | 'talking_head'
  | 'advanced_effects'
  | 'multi_language'
  | 'editorial_cuts'
  | 'captions'
  | 'auto_captions';

export interface DemoResult {
  id: string;
  video_url: string;
  timeline_url: string;
  captions_url?: string;
  duration: number;
  size_bytes: number;
  metadata: {
    scenario: DemoScenario;
    enhancements_used: AIEnhancement[];
    generation_time_s: number;
    quality_metrics: QualityMetrics;
  };
}

export interface QualityMetrics {
  audio_sync_accuracy_ms: number;
  marker_alignment_score: number; // 0-1
  video_quality_score: number; // 0-1
  compression_efficiency: number; // 0-1
}

export interface DemoJobRequest {
  id: string;
  config: DemoConfig;
  callbacks?: {
    on_progress?: WebhookConfig;
    on_complete?: WebhookConfig;
    on_error?: WebhookConfig;
  };
}

export interface WebhookConfig {
  url: string;
  headers?: Record<string, string>;
  retries?: number;
}

export type JobStatus =
  | 'queued'
  | 'capturing'
  | 'narrating'
  | 'composing'
  | 'post_processing'
  | 'completed'
  | 'failed';

export interface JobProgress {
  job_id: string;
  status: JobStatus;
  progress: number; // 0-1
  stage: string;
  message: string;
  eta_seconds?: number;
  current_step?: number;
  total_steps?: number;
}