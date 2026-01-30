#!/usr/bin/env node
/**
 * Video Demo Pipeline CLI
 */

import { createDemoGenerator, DemoBuilder } from './index';
import { promises as fs } from 'fs';
import * as path from 'path';

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === '--help') {
    console.log(`
Video Demo Pipeline CLI

Usage:
  npm run demo ai-agent        Generate AI agent demo
  npm run demo feature-walkthrough  Generate feature walkthrough demo
  npm run demo custom <config.json>  Generate demo from config file

Environment Variables:
  ELEVENLABS_API_KEY    Required for narration
  DTS_SESSIONID         Required for AI agent demo

Examples:
  npm run demo ai-agent
  npm run demo custom my-config.json
`);
    return;
  }

  const generator = createDemoGenerator();

  let config;

  if (args[0] === 'ai-agent') {
    console.log('🎬 Generating AI Agent Demo...');
    config = DemoBuilder.aiAgentDemo().build();

  } else if (args[0] === 'feature-walkthrough') {
    console.log('🎬 Generating Feature Walkthrough Demo...');
    config = DemoBuilder.featureWalkthrough().build();

  } else if (args[0] === 'custom' && args[1]) {
    const configPath = path.resolve(args[1]);
    console.log(`🎬 Generating custom demo from ${configPath}...`);

    try {
      const configContent = await fs.readFile(configPath, 'utf-8');
      config = JSON.parse(configContent);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Failed to load config file: ${msg}`);
      process.exit(1);
    }

  } else {
    console.error('❌ Invalid command. Use --help for usage information.');
    process.exit(1);
  }

  try {
    console.log('🚀 Starting demo generation...');
    const startTime = Date.now();

    const result = await generator.generateDemo(config, {
      onProgress: (progress) => {
        console.log(`📊 ${progress.status}: ${progress.message} (${Math.round(progress.progress * 100)}%)`);
      },
      onComplete: (result) => {
        console.log('✅ Demo generation completed!');
        console.log(`📹 Video: ${result.video_url}`);
        console.log(`⏱️  Duration: ${result.duration}s`);
        console.log(`📏 Size: ${(result.size_bytes / 1024 / 1024).toFixed(2)} MB`);
      },
      onError: (error) => {
        console.error('❌ Demo generation failed:', error.message);
      }
    });

    const duration = (Date.now() - startTime) / 1000;
    console.log(`🎉 Total time: ${duration.toFixed(1)}s`);
    console.log(`🏆 Success! Demo available at: ${result.video_url}`);

  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error('💥 Demo generation failed:', msg);
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch(console.error);
}