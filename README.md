# Video Generator

AI-orchestrated video generation for product demos, tutorials, and marketing content.

Record browser sessions, generate voiceovers, add talking head presenters, and compose professional videos — all through a single CLI.

## Features

- **Browser Recording** — Playwright CSS selectors or agent-browser ref-based element selection
- **AI Agent Browser** — Vercel Labs agent-browser integration for dynamic, ref-based UI automation
- **Text-to-Speech** — ElevenLabs integration for professional voiceovers
- **Talking Heads** — AI-generated presenters via FAL.ai (OmniHuman, SadTalker)
- **Title Cards** — AI-generated title videos via xAI Grok Imagine
- **Character Generation** — Custom AI presenter images via FAL.ai Flux Schnell
- **Video Editing** — Trim, cut, speed up, concatenate videos
- **Audio Distribution** — Timeline-based narration placement with overlap fixing
- **Captions** — Generate and burn SRT/VTT subtitles with multiple style presets
- **Quality Assurance** — Automatic evaluation system with quality scoring
- **Cost Tracking** — Built-in cost monitoring and optimization
- **Request Files** — Declarative markdown files define entire video workflows

## Quick Start

### 1. Install Dependencies

```bash
# Node dependencies (FFmpeg binary + Playwright)
npm install

# Python dependencies
pip install -r requirements.txt

# Install browser for recording
playwright install chromium
```

### 2. Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys:
# - ELEVENLABS_API_KEY (required for TTS)
# - FAL_API_KEY (optional, for talking heads)
```

### 3. Create a Video

```bash
# From a request file (recommended)
python3 video-generator/scripts/vg request generate --file requests/_template.md

# For dynamic platforms (use agent-browser)
python3 video-generator/scripts/vg request generate --file requests/_template_agentic.md

# Or with an existing video
python3 video-generator/scripts/vg request generate --file demo.md --skip-record --video existing.mp4
```

### 4. Agent Browser Setup (Optional)

For dynamic or complex platforms, install Vercel Labs agent-browser:

```bash
npm install -g agent-browser
```

Add to your request file:
```markdown
### Browser Driver
agent-browser  <!-- Use "current" for Playwright, "agent-browser" for ref-based -->
```

## Project Structure

```
├── .claude/
│   └── skills/
│       └── video-generator/
│           ├── SKILL.md            # AI Agent skill (auto-discovered by Claude Code)
│           └── docs/               # Documentation
│               ├── VIDEO_GENERATOR_CAPABILITIES.md
│               ├── EXAMPLES.md
│               ├── TOOLS.md
│               └── CAPTIONS.md
├── video-generator/
│   ├── QUICK_REF.md                # Quick reference guide
│   └── scripts/
│       ├── vg                      # CLI entry point
│       ├── vg_agent_browser.py     # Agent browser integration
│       └── vg_*.py                 # Implementation modules
├── requests/
│   ├── _template.md                # Legacy template
│   ├── _template_agentic.md        # Simplified agentic template (recommended)
│   └── *.md                        # Request files for video generation
├── videos/
│   ├── runs/                       # Generated video outputs
│   └── talking_heads/              # AI presenter assets
├── src/                            # TypeScript source (if applicable)
├── CLAUDE.md                       # Project context for Claude Code
├── evaluations.md                  # Quality evaluation results
├── requirements.txt                # Python dependencies
├── package.json                    # Node dependencies
├── *dashboard.html                 # HTML dashboards for run analytics
└── quality_check.html              # Quality assurance interface
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `vg request generate` | Full pipeline from request file |
| `vg record session start/do/stop` | Record with Playwright (CSS selectors) |
| `vg record session agent-start/do/stop` | Record with agent-browser (ref-based) |
| `vg audio tts` | Generate voiceover |
| `vg compose sync` | Combine video + audio |
| `vg compose place` | Place audio at AI-calculated times |
| `vg edit trim/cut/speed` | Video editing |
| `vg captions streaming` | Word-by-word captions (TikTok style) |
| `vg captions burn` | Burn SRT captions into video |
| `vg talking-head generate` | AI presenter video |
| `vg talking-head overlay` | Overlay talking head at time |
| `vg narration template render` | Generate narration from templates |
| `vg run evaluate` | Manual quality evaluation |
| `vg run dashboard` | Generate run analytics dashboard |
| `vg run list/summary` | View run history and analytics |
See:
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture and workflow diagrams
- [.claude/skills/video-generator/SKILL.md](.claude/skills/video-generator/SKILL.md) — Complete workflow documentation

## Request File Format

Request files are markdown documents that define the entire video workflow:

```markdown
## Platform
**URL:** https://app.example.com

## Authentication
**Type:** cookie
**Cookie Name:** session_id
**Cookie Value:** From environment variable `SESSION_TOKEN`

<!-- VOICEOVER_SEGMENTS_START -->
| Segment | Anchor Marker | Offset | Text |
|---------|---------------|--------|------|
| intro | t_page_loaded | 0.5s | Welcome to our platform... |
| wrap | t_agent_done_1 | 1.0s | That's how easy it is! |
<!-- VOICEOVER_SEGMENTS_END -->
```

### Narration Templates

Pre-built narration templates for common scenarios:

```bash
# Use AI agent template
vg narration template render --template ai_agent_default --overrides '{"prompt_text":"Create KPI dashboard"}'
```

Available templates: `ai_agent_default`, `cross_channel_demo`, `dashboard_walkthrough`

### Caching System

Automatic caching reduces API costs and improves performance:
- TTS audio segments
- Generated images/characters
- Title card videos
- Quality evaluation results

## API Keys Required

| Service | Purpose | Required |
|---------|---------|----------|
| [ElevenLabs](https://elevenlabs.io) | Text-to-Speech | Yes (for voiceovers) |
| [FAL.ai](https://fal.ai) | Talking heads & character generation | No (optional feature) |
| [xAI](https://x.ai) | Title card generation | No (optional feature) |
| Vercel Labs | agent-browser CLI | No (optional, for dynamic UIs) |

## Output

All generated files are saved to `videos/runs/<run_id>/`:

```
videos/runs/my_demo_20260129/
├── raw/              # Raw recordings
├── audio/            # Generated TTS segments
├── timeline.md       # Timeline markers
├── demo.mp4          # Converted video
├── final.mp4         # Final output
├── run_report.md     # Generation report
├── evaluation/       # Quality evaluation results
│   ├── evaluation.md # Detailed quality report
│   └── scores.json   # Quality metrics
└── cost_tracking.json # API usage costs
```

### Quality Assurance

Every video generation includes automatic quality evaluation:
- **Quality Score**: 0.0-1.0 rating
- **Issue Detection**: Automatic problem identification
- **Recommendations**: Actionable improvement suggestions
- **Analytics**: Cost tracking and performance metrics

View results with: `vg run dashboard`

## For AI Agents

This project includes a [SKILL.md](.claude/skills/video-generator/SKILL.md) file designed for AI agent integration:

- **Agentic Architecture**: AI calculates exact timings, Python executes
- **Quality Assurance**: Automatic evaluation with actionable feedback
- **Decision Trees**: Workflow selection based on platform complexity
- **Token Estimation**: Cost prediction for each command
- **Error Recovery**: Built-in fallback strategies
- **Native FFmpeg**: Direct video processing when needed

### Agent Browser Integration

For dynamic platforms, use agent-browser with ref-based element selection:

```bash
# Start agent-browser session
vg record session agent-start --run-id demo --url "https://app.example.com"

# Execute actions by reference
vg record session agent-do --run-id demo --action click --ref "@e5"

# Stop and generate video
vg record session agent-stop --run-id demo
```

## Tech Stack

- **Python 3.10+** — Core implementation
- **Playwright** — Browser automation (CSS selectors)
- **Vercel Labs agent-browser** — AI-powered browser control (ref-based)
- **FFmpeg** — Video/audio processing
- **ElevenLabs API** — Text-to-speech
- **FAL.ai API** — Talking heads & character generation
- **xAI Grok API** — Title card generation
- **TypeScript** — Additional tooling (optional)

## License

MIT
