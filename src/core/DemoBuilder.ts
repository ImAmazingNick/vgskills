/**
 * Fluent API for building demo configurations
 */

import {
  DemoConfig,
  DemoScenario,
  CaptureConfig,
  NarrationConfig,
  CompositionConfig,
  AIEnhancement,
  VoiceConfig,
  NarrationSegment,
  Resolution
} from '../types/demo';

export class DemoBuilder {
  private config: Partial<DemoConfig> = {};

  constructor() {
    this.config.id = `demo_${Date.now()}`;
  }

  /**
   * Set the demo scenario
   */
  withScenario(scenario: DemoScenario): this {
    this.config.scenario = scenario;
    return this;
  }

  /**
   * Configure capture settings
   */
  withCapture(config: Partial<CaptureConfig>): this {
    this.config.capture = {
      url: config.url || 'https://report.improvado.io/experimental/agent/new-agent/?workspace=121',
      scenario: this.config.scenario || 'ai_agent_demo',
      resolution: config.resolution || '1080p',
      fps: config.fps || 30,
      headless: config.headless || false,
      incognito: config.incognito !== false, // Default true
      timeout_s: config.timeout_s || 300,
      ...config
    };
    return this;
  }

  /**
   * Configure narration settings
   */
  withNarration(config: Partial<NarrationConfig>): this {
    this.config.narration = {
      segments: config.segments || this.getDefaultSegments(),
      voice: config.voice || {
        provider: 'elevenlabs',
        voice_id: '21m00Tcm4TlvDq8ikWAM', // Default professional voice
        model: 'eleven_monolingual_v1',
        language: 'en'
      },
      conditional_segments: config.conditional_segments || [],
      filler_segments: config.filler_segments || [],
      include_captions: config.include_captions !== false, // Default true
      ...config
    };
    return this;
  }

  /**
   * Configure voice settings
   */
  withVoice(voice: VoiceConfig): this {
    if (!this.config.narration) {
      this.withNarration({});
    }
    this.config.narration!.voice = voice;
    return this;
  }

  /**
   * Configure composition settings
   */
  withComposition(config: Partial<CompositionConfig>): this {
    this.config.composition = {
      output_resolution: config.output_resolution || '1080p',
      effects: config.effects || [],
      branding: config.branding,
      compression_strategy: config.compression_strategy || 'no_compression',
      ...config
    };
    return this;
  }

  /**
   * Add AI enhancements
   */
  withEnhancements(...enhancements: AIEnhancement[]): this {
    this.config.ai_enhancements = enhancements;
    return this;
  }

  /**
   * Set demo metadata
   */
  withMetadata(metadata: DemoConfig['metadata']): this {
    this.config.metadata = metadata;
    return this;
  }

  /**
   * Set custom demo ID
   */
  withId(id: string): this {
    this.config.id = id;
    return this;
  }

  /**
   * Build the final configuration
   */
  build(): DemoConfig {
    if (!this.config.scenario) {
      throw new Error('Demo scenario must be specified');
    }
    if (!this.config.capture) {
      this.withCapture({});
    }
    if (!this.config.narration) {
      this.withNarration({});
    }
    if (!this.config.composition) {
      this.withComposition({});
    }

    return this.config as DemoConfig;
  }

  /**
   * Create a pre-configured AI agent demo
   */
  static aiAgentDemo(): DemoBuilder {
    return new DemoBuilder()
      .withScenario('ai_agent_demo')
      .withCapture({
        url: 'https://report.improvado.io/experimental/agent/new-agent/?workspace=121',
        session_credentials: {
          cookie_name: 'dts_sessionid',
          cookie_value: process.env.DTS_SESSIONID || 'p4o74jjr8u9j0jaufvuw8cw8it6dq6c0',
          domain: '.improvado.io'
        }
      })
      .withNarration({
        segments: [
          {
            id: 'intro',
            anchor: 't_page_loaded',
            offset_s: 0.5,
            text: 'Connect any marketing or sales data — Google, LinkedIn, Salesforce, anything. Automatically pulled, cleaned, structured, instantly ready.'
          },
          {
            id: 'prompt1',
            anchor: 't_prompt1_focus',
            offset_s: 0.2,
            text: 'Here\'s where it gets magical. Open the AI agent and type exactly what you need: \'Create cross-channel marketing analytics dashboard.\''
          },
          {
            id: 'processing1',
            anchor: 't_processing1_started',
            offset_s: 2.0,
            text: 'While the agent is processing, it discovers your data and starts building a full editable dashboard—charts, KPIs, and insights—automatically.'
          },
          {
            id: 'reveal1',
            anchor: 't_agent_done_1',
            offset_s: 0.5,
            text: 'Done. On the left, you have chat. On the right, your generated dashboard—ready to edit.'
          }
        ]
      })
      .withComposition({
        output_resolution: '1080p'
      })
      .withEnhancements('captions');
  }

  /**
   * Create a pre-configured feature walkthrough demo
   */
  static featureWalkthrough(): DemoBuilder {
    return new DemoBuilder()
      .withScenario('feature_walkthrough')
      .withCapture({
        url: 'https://example.com/feature-page'
      })
      .withNarration({
        segments: [
          {
            id: 'intro',
            anchor: 't_page_loaded',
            offset_s: 0.5,
            text: 'Let me show you this powerful new feature that will transform how you work.'
          }
        ]
      })
      .withComposition({
        output_resolution: '1080p'
      })
      .withEnhancements('captions', 'editorial_cuts');
  }

  private getDefaultSegments(): NarrationSegment[] {
    return [
      {
        id: 'intro',
        anchor: 't_page_loaded',
        offset_s: 0.5,
        text: 'Welcome to this demo.'
      },
      {
        id: 'main',
        anchor: 't_start_recording',
        offset_s: 2.0,
        text: 'Let me show you how this works.'
      },
      {
        id: 'conclusion',
        anchor: 't_end_recording',
        offset_s: -3.0,
        text: 'That concludes our demo.'
      }
    ];
  }
}