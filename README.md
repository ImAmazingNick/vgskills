# Video Generator

AI-orchestrated video generation for product demos, tutorials, and marketing content.

Record browser sessions, generate voiceovers, add talking head presenters, and compose professional videos — all through a single CLI.

## Features

- **Browser Recording** — Automated Playwright-based screen capture with timeline markers
- **Text-to-Speech** — ElevenLabs integration for professional voiceovers
- **Talking Heads** — AI-generated presenters via FAL.ai (OmniHuman, SadTalker)
- **Video Editing** — Trim, cut, speed up, concatenate videos
- **Audio Distribution** — Timeline-based narration placement with overlap fixing
- **Captions** — Generate and burn SRT/VTT subtitles with multiple style presets
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

# Or with an existing video
python3 video-generator/scripts/vg request generate --file my_demo.md --skip-record --video existing.mp4
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
│   └── scripts/
│       ├── vg                      # CLI entry point
│       └── vg_*.py                 # Implementation modules
├── requests/
│   └── _template.md                # Template for new request files
├── videos/
│   └── runs/                       # Generated video outputs
├── CLAUDE.md                       # Project context for Claude Code
├── requirements.txt                # Python dependencies
└── package.json                    # Node dependencies
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `vg request generate` | Full pipeline from request file |
| `vg record` | Record browser session |
| `vg audio tts` | Generate voiceover |
| `vg compose sync` | Combine video + audio |
| `vg compose place` | Place audio at AI-calculated times |
| `vg edit trim/cut/speed` | Video editing |
| `vg captions streaming` | Word-by-word captions (TikTok style) |
| `vg captions burn` | Burn SRT captions into video |
| `vg talking-head generate` | AI presenter video |
| `vg talking-head overlay` | Overlay talking head at time |

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

## API Keys Required

| Service | Purpose | Required |
|---------|---------|----------|
| [ElevenLabs](https://elevenlabs.io) | Text-to-Speech | Yes (for voiceovers) |
| [FAL.ai](https://fal.ai) | Talking head generation | No (optional feature) |

## Output

All generated files are saved to `videos/runs/<run_id>/`:

```
videos/runs/my_demo_20260129/
├── raw/              # Raw recordings
├── audio/            # Generated TTS segments
├── timeline.md       # Timeline markers
├── demo.mp4          # Converted video
├── final.mp4         # Final output
└── run_report.md     # Generation report
```

## For AI Agents

This project includes a [SKILL.md](.claude/skills/video-generator/SKILL.md) file designed for AI agent integration:

- Decision trees for workflow selection
- Token estimation for each command
- Error recovery guidance
- Native FFmpeg fallbacks

## Tech Stack

- **Python 3.10+** — Core implementation
- **Playwright** — Browser automation
- **FFmpeg** — Video/audio processing
- **ElevenLabs API** — Text-to-speech
- **FAL.ai API** — Talking head generation

## License

MIT
