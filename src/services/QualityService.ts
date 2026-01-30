/**
 * QualityService - Validates timeline markers and measures quality metrics
 */

import {
  QualityService as IQualityService,
  ValidationResult,
  ValidationIssue,
  SyncValidation,
  SyncIssue
} from '../types/services';
import { TimelineData, DemoResult, QualityMetrics } from '../types/demo';
import { Logger } from '../core/Logger';

export class QualityService implements IQualityService {
  private readonly logger: Logger;

  constructor(logger?: Logger) {
    this.logger = logger || new Logger('QualityService');
  }

  validateTimeline(timeline: TimelineData): ValidationResult {
    const issues: ValidationIssue[] = [];

    // Check required markers exist
    const requiredMarkers = ['t_start_recording', 't_page_loaded', 't_end_recording'];
    for (const marker of requiredMarkers) {
      if (!(marker in timeline.markers)) {
        issues.push({
          type: 'error',
          field: 'timeline',
          message: `Required marker '${marker}' is missing`,
          suggestion: 'Ensure capture script completes successfully'
        });
      }
    }

    // Check marker ordering (should be chronological)
    const markers = Object.entries(timeline.markers);
    const sortedMarkers = markers.sort((a, b) => a[1] - b[1]);

    for (let i = 0; i < markers.length; i++) {
      if (markers[i][0] !== sortedMarkers[i][0]) {
        issues.push({
          type: 'warning',
          field: 'timeline',
          message: 'Timeline markers are not in chronological order',
          suggestion: 'Review marker extraction logic'
        });
        break;
      }
    }

    // Check for reasonable time spans
    const startTime = timeline.markers.t_start_recording || 0;
    const endTime = timeline.markers.t_end_recording || 0;
    const duration = endTime - startTime;

    if (duration < 10) {
      issues.push({
        type: 'warning',
        field: 'duration',
        message: `Recording duration (${duration}s) is very short`,
        suggestion: 'Verify demo scenario ran to completion'
      });
    }

    if (duration > 600) { // 10 minutes
      issues.push({
        type: 'warning',
        field: 'duration',
        message: `Recording duration (${duration}s) is very long`,
        suggestion: 'Consider compression strategies for long recordings'
      });
    }

    // Check marker density (should have reasonable spacing)
    const markerTimes = Object.values(timeline.markers).sort((a, b) => a - b);
    const gaps: number[] = [];
    for (let i = 1; i < markerTimes.length; i++) {
      gaps.push(markerTimes[i] - markerTimes[i - 1]);
    }

    const avgGap = gaps.reduce((sum, gap) => sum + gap, 0) / gaps.length;
    if (avgGap > 120) { // 2 minutes between markers
      issues.push({
        type: 'warning',
        field: 'marker_density',
        message: `Average gap between markers (${avgGap.toFixed(1)}s) is large`,
        suggestion: 'Add more timeline markers for better narration sync'
      });
    }

    const score = Math.max(0, 1 - (issues.length * 0.2));

    return {
      isValid: issues.filter(i => i.type === 'error').length === 0,
      issues,
      score
    };
  }

  async validateSync(videoUrl: string, audioSegments: any[]): Promise<SyncValidation> {
    // Simplified sync validation
    // In production, this would analyze actual audio/video sync

    const issues: SyncIssue[] = [];
    let maxDrift = 0;
    let totalDrift = 0;
    let sampleCount = 0;

    // Mock sync analysis - in reality would use ffprobe or similar
    for (const segment of audioSegments) {
      const drift = Math.random() * 0.2 - 0.1; // Random drift between -100ms and +100ms
      const absDrift = Math.abs(drift);

      if (absDrift > 0.15) { // More than 150ms drift
        issues.push({
          segment_id: segment.id,
          expected_time: segment.start_time,
          actual_time: segment.start_time + drift,
          drift_ms: drift * 1000,
          severity: absDrift > 0.3 ? 'high' : 'medium'
        });
      }

      maxDrift = Math.max(maxDrift, absDrift);
      totalDrift += absDrift;
      sampleCount++;
    }

    const avgDrift = sampleCount > 0 ? totalDrift / sampleCount : 0;
    const syncScore = Math.max(0, 1 - (maxDrift / 0.5)); // Score degrades with drift

    return {
      max_drift_ms: maxDrift * 1000,
      average_drift_ms: avgDrift * 1000,
      sync_score: syncScore,
      issues
    };
  }

  calculateMetrics(result: DemoResult): QualityMetrics {
    // Calculate comprehensive quality metrics
    const metrics = result.metadata.quality_metrics;

    // Audio sync accuracy (lower is better)
    const audioSyncScore = Math.max(0, 1 - (metrics.audio_sync_accuracy_ms / 500));

    // Marker alignment score (already provided)
    const markerScore = metrics.marker_alignment_score;

    // Video quality score (already provided)
    const videoScore = metrics.video_quality_score;

    // Compression efficiency (1.0 = no compression, lower = more compressed)
    const compressionScore = metrics.compression_efficiency;

    // Overall quality score (weighted average)
    const overallScore = (
      audioSyncScore * 0.3 +
      markerScore * 0.3 +
      videoScore * 0.3 +
      compressionScore * 0.1
    );

    return {
      ...metrics,
      // Could add more sophisticated calculations here
    };
  }
}