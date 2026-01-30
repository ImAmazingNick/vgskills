/**
 * Video Demo Pipeline - Main entry point
 *
 * Professional video demo generation that transforms AI agent workflows
 * into polished, professional video content.
 */

// Core services
export { DemoGenerator } from './core/DemoGenerator';
export { DemoBuilder } from './core/DemoBuilder';
export { Logger } from './core/Logger';

// Service implementations
export { CaptureService } from './services/CaptureService';
export { NarrationService } from './services/NarrationService';
export { CompositionService } from './services/CompositionService';
export { QualityService } from './services/QualityService';

// Type definitions
export * from './types/demo';
export * from './types/services';

// Factory function for easy setup
import { DemoGenerator } from './core/DemoGenerator';
import { DemoBuilder } from './core/DemoBuilder';
import { CaptureService } from './services/CaptureService';
import { NarrationService } from './services/NarrationService';
import { CompositionService } from './services/CompositionService';
import { QualityService } from './services/QualityService';
import { Logger } from './core/Logger';

/**
 * Create a fully configured demo generator
 */
export function createDemoGenerator(logger?: Logger): DemoGenerator {
  const log = logger || new Logger('DemoGenerator');

  const captureService = new CaptureService(undefined, log.child({ service: 'Capture' }));
  const narrationService = new NarrationService(undefined, log.child({ service: 'Narration' }));
  const compositionService = new CompositionService(undefined, log.child({ service: 'Composition' }));
  const qualityService = new QualityService(log.child({ service: 'Quality' }));

  return new DemoGenerator(
    captureService,
    narrationService,
    compositionService,
    qualityService,
    log
  );
}

// Example usage
export const exampleUsage = async () => {
  const generator = createDemoGenerator();

  const config = DemoBuilder.aiAgentDemo().build();

  try {
    const result = await generator.generateDemo(config);
    console.log('Demo generated successfully:', result.video_url);
  } catch (error) {
    console.error('Demo generation failed:', error);
  }
};