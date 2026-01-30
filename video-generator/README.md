# Video Generator

AI-orchestrated video generation through the `vg` CLI.

## Quick Start

```bash
# The ONE command (recommended)
vg request generate --file demo.md

# With existing video
vg request generate --file demo.md --skip-record --video existing.mp4
```

**No request file?** AI Agent generates one - see SKILL.md Workflow E.

## Files

All documentation is in `.claude/skills/video-generator/`:

| File | Purpose |
|------|---------|
| `SKILL.md` | **AI Agent skill** - auto-discovered by Claude Code |
| `docs/VIDEO_GENERATOR_CAPABILITIES.md` | Full reference |
| `docs/TOOLS.md` | Complete CLI command reference |
| `docs/EXAMPLES.md` | Workflow examples |
| `docs/CAPTIONS.md` | Caption styling guide |

## Architecture

```
.claude/skills/video-generator/
├── SKILL.md              # AI Agent skill (auto-discovered)
└── docs/                 # Documentation
    ├── VIDEO_GENERATOR_CAPABILITIES.md
    ├── EXAMPLES.md
    ├── TOOLS.md
    └── CAPTIONS.md

video-generator/
└── scripts/
    ├── vg                # CLI entry point
    └── vg_*.py           # Implementation modules
```

## Output Structure

```
videos/runs/<run_id>/
├── raw/                  # Raw recordings
├── audio/                # Generated TTS
├── timeline.md           # Timeline markers
├── demo.mp4              # Converted video
└── final.mp4             # Final output
```

## Environment

```bash
export ELEVENLABS_API_KEY=...  # Required for TTS
export FAL_API_KEY=...         # Required for talking heads
```

## Usage

See `../.claude/skills/video-generator/SKILL.md` for complete AI Agent workflow documentation.

Claude Code automatically discovers this skill when you mention video creation, demos, or recordings.
