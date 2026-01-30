# Video Generator

AI-orchestrated video generation CLI. Creates product demos with voiceover, captions, and talking heads.

## Quick Start

```bash
# Full video from request file
python3 video-generator/scripts/vg request generate --file requests/_template.md

# With existing video
python3 video-generator/scripts/vg request generate --file demo.md --skip-record --video existing.mp4
```

## Agentic Commands (AI Provides Exact Times)

| Task | Command |
|------|---------|
| Place audio at times | `vg compose place --video v.mp4 --audio a.mp3:33.6 --audio b.mp3:107.3 -o out.mp4` |
| Overlay talking heads | `vg talking-head overlay --video v.mp4 --overlay th.mp4:47.6 --position bottom-right -o out.mp4` |

**Returns from tools (AI uses to recalculate):**
- `vg audio tts` → `{"duration_s": 4.2, "path": "..."}`
- `vg edit trim` → `{"adjustment": {"type": "offset", "seconds": -8}}`
- `vg edit speed-gaps` → `{"time_map": [[33.6, 12.8], ...], "scale_factor": 0.38}`

## Core Commands

| Task | Command |
|------|---------|
| Full pipeline | `vg request generate --file demo.md` |
| Record (CSS selectors) | `vg record session start/do/stop --run-id demo` |
| Record (ref-based) | `vg record session agent-start/do/stop --run-id demo` |
| Generate TTS | `vg audio tts --text "..." -o audio.mp3` |
| Add audio to video | `vg compose sync --video v.mp4 --audio a.mp3 -o final.mp4` |
| Trim video | `vg edit trim --video v.mp4 --start 5 --end 60 -o out.mp4` |
| Speed up gaps | `vg edit speed-gaps --video v.mp4 --factor 3 -o out.mp4` |
| Generate captions | `vg captions streaming --video v.mp4 --request r.md -o final.mp4` |

All `vg` commands: `python3 video-generator/scripts/vg <command>`

## Key Files

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture, workflows, and data flows
- **[.claude/skills/video-generator/SKILL.md](.claude/skills/video-generator/SKILL.md)** — Complete workflow guide (auto-discovered by Claude)
- **[requests/_template.md](requests/_template.md)** — Legacy template for video requests
- **[requests/_template_agentic.md](requests/_template_agentic.md)** — Simplified agentic template (recommended)
- **[.claude/skills/video-generator/docs/](.claude/skills/video-generator/docs/)** — Full documentation
  - `VIDEO_GENERATOR_CAPABILITIES.md` — Complete reference
  - `EXAMPLES.md` — Workflow examples
  - `TOOLS.md` — CLI commands
  - `CAPTIONS.md` — Caption styling

## Output Location

All outputs: `videos/runs/<run_id>/`
- `final.mp4` — Final video
- `audio/` — TTS segments  
- `timeline.md` — Timeline markers

## Environment

```bash
export ELEVENLABS_API_KEY=...  # Required for TTS
export FAL_API_KEY=...         # Optional, for talking heads
```

## FFmpeg Fallback

If CLI commands fail, use ffmpeg directly:
```bash
./node_modules/ffmpeg-static/ffmpeg -ss 45 -i input.mp4 -c copy output.mp4
```
