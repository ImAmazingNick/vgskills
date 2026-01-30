# Video Generator - Complete Capabilities Reference

> **Version**: 1.1  
> **Last Updated**: January 2026  
> **Entry Point**: `scripts/vg` (CLI)

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Architecture Overview](#architecture-overview)
3. [CLI Command Reference](#cli-command-reference)
4. [Capabilities by Category](#capabilities-by-category)
   - [Recording & Browser Automation](#1-recording--browser-automation)
   - [Audio Generation & Processing](#2-audio-generation--processing)
   - [Video Composition & Synchronization](#3-video-composition--synchronization)
   - [Video Editing](#4-video-editing)
   - [Talking Head Generation](#5-talking-head-generation)
   - [Quality & Optimization](#6-quality--optimization)
   - [Request File Processing](#7-request-file-processing)
   - [Narration Templates](#8-narration-templates)
   - [Timeline Management](#9-timeline-management)
   - [Caption Generation & Subtitles](#10-caption-generation--subtitles)
   - [Authentication & Security](#11-authentication--security)
   - [Cost Tracking](#12-cost-tracking)
   - [Caching System](#13-caching-system)
   - [Utility Functions](#14-utility-functions)
5. [File Structure](#file-structure)
6. [External Integrations](#external-integrations)
7. [Token Estimation for AI Agents](#token-estimation-for-ai-agents)

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.10+ | Core implementation |
| **Browser Automation** | Playwright | Recording, screenshots, navigation |
| **Video Processing** | FFmpeg | Editing, conversion, composition |
| **Text-to-Speech** | ElevenLabs API | Voice generation |
| **Talking Heads** | FAL.ai (OmniHuman, SadTalker) | AI presenter generation |
| **Character Generation** | FAL.ai Flux Schnell | AI character images |
| **Media Analysis** | FFprobe | Duration, metadata extraction |
| **CLI Framework** | argparse | Command structure |
| **Output Format** | JSON | Structured responses |

---

## Architecture Overview

### Agentic Architecture (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI AGENT (Claude)                           │
│   Reads request → Calculates placements → Passes explicit times  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │   vg compose place │           │ vg talking-head   │
        │   (Dumb executor)  │           │     overlay       │
        │                   │           │   (Dumb executor)  │
        └───────────────────┘           └───────────────────┘
```

**Key Principle:** AI decides, Python executes. Tools accept explicit times (e.g., `--audio file:33.6`).

### Legacy Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         vg CLI Entry Point                       │
│                         scripts/vg (Python)                      │
└─────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  vg_commands/ │         │  Core Modules │         │  vg_core_utils│
│   (Handlers)  │         │ (Functions)   │         │   (Helpers)   │
└───────────────┘         └───────────────┘         └───────────────┘
    │                           │                           │
    ├─ record.py               ├─ vg_recording.py          ├─ timeline.py
    ├─ audio.py                ├─ vg_tts.py                ├─ md_parser.py
    ├─ edit.py                 ├─ vg_edit.py               └─ __init__.py
    ├─ compose.py              ├─ vg_compose.py
    ├─ talking_head.py         ├─ vg_talking_head.py
    ├─ quality.py              ├─ vg_quality.py
    ├─ narration.py            ├─ vg_narration_templates.py
    ├─ request.py              ├─ vg_auth.py
    └─ utils.py                ├─ vg_cost.py
                               ├─ vg_common.py
                               ├─ vg_utils.py
                               └─ project_paths.py
```

---

## CLI Command Reference

### Entry Point

```bash
./scripts/vg [--json] [--progress] <command> [options]
```

### Command Groups

| Command Group | Description | Subcommands |
|---------------|-------------|-------------|
| `record` | Browser recording | `screenshot`, `session start/do/stop/status`, `session agent-start/do/stop/status` |
| `audio` | Audio operations | `tts`, `batch`, `mix` |
| `edit` | Video editing | `trim`, `cut`, `speed`, `speed-silence`, `speed-gaps`, `concat` |
| `compose` | Video composition | `sync`, `distribute`, `overlay`, **`place`** (agentic) |
| `talking-head` | Talking head ops | `generate`, `composite`, **`overlay`** (agentic) |
| `quality` | Quality operations | `validate`, `analyze`, `optimize` |
| `captions` | Caption generation | `generate`, `burn`, `preview`, **`streaming`** (word-by-word) |
| `request` | Request file ops | `parse`, `generate` |
| `narration` | Narration templates | `template list/render/save`, `batch` |
| `validate` | Validation ops | `timeline`, `request` |
| `cost` | Cost tracking | `estimate`, `history`, `summary`, `budget` |
| `cache` | Cache management | `clear`, `status` |
| `list` | List assets | - |
| `info` | Get file info | - |
| `cleanup` | Cleanup temp files | - |
| `status` | System status | - |

### Agentic Commands (AI Provides Exact Times)

| Command | Purpose | Input Format |
|---------|---------|--------------|
| `vg compose place` | Place audio at AI-calculated times | `--audio file.mp3:33.6` |
| `vg talking-head overlay` | Overlay talking heads at AI-calculated times | `--overlay th.mp4:47.6` |

**Tool Returns (AI uses to recalculate):**
- `vg audio tts` → `{"duration_s": 4.2, "path": "..."}`
- `vg edit trim` → `{"adjustment": {"type": "offset", "seconds": -8}}`
- `vg edit speed-gaps` → `{"time_map": [[33.6, 12.8], ...], "scale_factor": 0.38}`

---

## Capabilities by Category

### 1. Recording & Browser Automation

#### Browser Session Recording
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg record --url <url>` | `vg_commands/record.py`, `vg_recording.py`, `base_demo.py` | Records browser sessions with Playwright |
| **Function** | `record_demo(config)` | `vg_recording.py` | Core recording function |
| **Config** | `RecordingConfig` | `vg_recording.py` | Recording configuration dataclass |

**Capabilities:**
- ✅ Browser automation with Playwright (AI Agent can navigate)
- ✅ Timeline marker extraction during recording
- ✅ Headless mode (`--headless`)
- ✅ Screenshot capture during recording
- ✅ Multi-scenario support: `ai-agent`, `simple-dashboard`, `custom`, `auto`
- ✅ Custom action sequences from request files
- ✅ Auto-trim of loading spinners (>25s)
- ✅ Recording quality validation

**Example:**
```bash
vg record --url "https://app.example.com" --scenario ai-agent --request demo.md
```

#### Live Recording Sessions
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg record session start` | `vg_commands/record.py`, `vg_session_simple.py` | Start live session |
| **Action** | `vg record session do` | `vg_commands/record.py` | Send action to session |
| **Action** | `vg record session stop` | `vg_commands/record.py` | Stop and save session |
| **Function** | `run_session()` | `vg_session_simple.py` | Session control loop |
| **Config** | `SessionConfig` | `vg_session_simple.py` | Session configuration |

**Capabilities:**
- ✅ Start/stop live sessions
- ✅ Stream actions via JSONL queue
- ✅ Actions: `click`, `type`, `fill`, `wait`, `navigate`, `screenshot`, `marker`
- ✅ Wait for responses with timeout
- ✅ Demo cursor effects (`--demo-effects`)

**Example:**
```bash
vg record session start --url "https://app.example.com" --run-id my_session
vg record session do --run-id my_session --action click --selector "#button"
vg record session stop --run-id my_session
```

#### agent-browser Recording Sessions (Recommended for New Platforms)
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg record session agent-start` | `vg_commands/record.py`, `vg_agent_browser.py` | Start agent-browser session |
| **Action** | `vg record session agent-do` | `vg_commands/record.py` | Send action to session |
| **Action** | `vg record session agent-stop` | `vg_commands/record.py` | Stop and save session |
| **Function** | `AgentBrowserSession` | `vg_agent_browser.py` | Session manager class |

**Capabilities:**
- ✅ Ref-based element selection (`@e1`, `@e5`) instead of CSS selectors
- ✅ More stable when UIs change (refs from accessibility tree)
- ✅ Snapshot returns element refs for AI decision-making
- ✅ Actions: `snapshot`, `click`, `fill`, `type`, `press`, `wait`, `scroll`, `marker`, `screenshot`
- ✅ Compatible with existing pipeline (same .webm + timeline.md output)
- ✅ Auto-detection of system Chrome

**Example:**
```bash
vg record session agent-start --run-id demo --url "https://app.example.com" --cookie "s=abc" --cookie-domain ".example.com"
vg record session agent-do --run-id demo --action snapshot -i    # Get refs
vg record session agent-do --run-id demo --action click --ref "@e5"
vg record session agent-do --run-id demo --action type --ref "@e12" --value "Create dashboard"
vg record session agent-do --run-id demo --action marker --value "t_submitted"
vg record session agent-stop --run-id demo
```

**vs CSS Selectors:** Uses `agent-start/do/stop` + refs (`@e5`) instead of `start/do/stop` + CSS selectors. Recommended for new platforms where selectors may change.

#### Screenshot Capture
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg record screenshot` | `vg_commands/record.py` | Capture webpage screenshot |
| **Function** | `cmd_screenshot()` | `vg_commands/record.py` | Screenshot handler |

**Capabilities:**
- ✅ Viewport or full-page screenshots (`--full-page`)
- ✅ Wait for selectors before capture (`--selector`)
- ✅ Authentication support

**Example:**
```bash
vg record screenshot --url "https://app.example.com" --output screen.png --full-page
```

#### Smart Waiting
| Type | Files | Description |
|------|-------|-------------|
| **Helper** | `vg_smart_waiting.py` | Intelligent wait conditions |

**Capabilities:**
- ✅ Wait for AI agent completion
- ✅ Dashboard visibility detection
- ✅ Input field detection (primary/followup)
- ✅ Deep selector queries (shadow DOM)
- ✅ Largest input detection

---

### 2. Audio Generation & Processing

#### Text-to-Speech (TTS)
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg audio tts` | `vg_commands/audio.py`, `vg_tts.py`, `elevenlabs_tts.py` | Generate speech |
| **Function** | `tts_with_json_output()` | `vg_tts.py` | TTS with JSON response |
| **Function** | `batch_tts()` | `vg_tts.py` | Batch TTS generation |

**Capabilities:**
- ✅ Text-to-speech via ElevenLabs API
- ✅ Multiple voice models and settings
- ✅ Audio segment generation with timing
- ✅ Voice caching for performance (MD5-based, 24h expiry)
- ✅ Cost tracking per generation
- ✅ Text file input support

**Example:**
```bash
vg audio tts --text "Hello world" --voice 21m00Tcm4TlvDq8ikWAM --output hello.mp3
vg audio batch --segments segments.json --output-dir ./audio/
```

#### Audio Mixing
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg audio mix` | `vg_commands/audio.py` | Mix/concatenate audio |
| **Function** | `cmd_mix()` | `vg_commands/audio.py` | Audio mixing handler |

**Capabilities:**
- ✅ Concatenate multiple tracks (`--mode concat`)
- ✅ Overlay mixing (`--mode overlay`)
- ✅ FFmpeg-based processing

**Example:**
```bash
vg audio mix --tracks "intro.mp3,main.mp3,outro.mp3" --output combined.mp3 --mode concat
```

---

### 3. Video Composition & Synchronization

#### Audio-Video Sync
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg compose sync` | `vg_commands/compose.py`, `vg_compose.py` | Simple audio-video mux |
| **Function** | `sync_audio_video()` | `vg_compose.py` | Sync function |

**Capabilities:**
- ✅ Simple muxing (audio from start)
- ✅ WebM to MP4 conversion
- ✅ Web optimization (faststart)

**Example:**
```bash
vg compose sync --video demo.webm --audio narration.mp3 --output final.mp4
```

#### Audio Distribution
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg compose distribute` | `vg_commands/compose.py` | Timeline-based audio placement |
| **Function** | `calculate_segment_times_strict()` | `vg_core_utils/timeline.py` | Strict marker positioning |
| **Function** | `calculate_segment_times_lenient()` | `vg_core_utils/timeline.py` | Fallback positioning |
| **Function** | `fix_overlaps_cascading()` | `vg_core_utils/timeline.py` | Overlap fixing |

**Capabilities:**
- ✅ Synchronize audio segments with video timeline
- ✅ Timeline-based audio positioning
- ✅ Strict marker requirements (fails fast if missing)
- ✅ Lenient fallback with fuzzy matching
- ✅ Overlap fixing (300ms cascading delays)
- ✅ Conditional narration fillers
- ✅ Repeatable segments with intervals
- ✅ FFmpeg adelay + amix filters

**Example:**
```bash
vg compose distribute --video demo.mp4 --request demo.md --audio-dir ./audio/ --output final.mp4
```

#### Video Overlay
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg compose overlay` | `vg_commands/compose.py`, `vg_compose.py` | Picture-in-picture |
| **Function** | `overlay_video()` | `vg_compose.py` | Overlay function |

**Capabilities:**
- ✅ Picture-in-picture overlays
- ✅ Position control (`top-left`, `top-right`, `bottom-left`, `bottom-right`)
- ✅ Size percentage control

**Example:**
```bash
vg compose overlay --video main.mp4 --overlay pip.mp4 --position bottom-right --size 30 --output final.mp4
```

#### Agentic Audio Placement (NEW)
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg compose place` | `vg_commands/compose.py` | AI-controlled audio placement |
| **Function** | `cmd_place()` | `vg_commands/compose.py` | Dumb executor |

**Capabilities:**
- ✅ Place multiple audio files at AI-specified times
- ✅ No marker matching logic (AI provides exact times)
- ✅ FFmpeg adelay + amix filters

**Example:**
```bash
vg compose place --video demo.mp4 --audio intro.mp3:33.6 --audio reveal.mp3:261.3 -o final.mp4
```

---

### 4. Video Editing

#### Video Trimming
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg edit trim` | `vg_commands/edit.py`, `vg_edit.py`, `video_editor.py` | Trim start/end |
| **Function** | `trim_video()` | `vg_edit.py` | Trim function |

**Capabilities:**
- ✅ Video trimming (start/end)
- ✅ Duration validation

**Example:**
```bash
vg edit trim --video input.mp4 --start 5 --end 60 --output trimmed.mp4
```

#### Section Cutting
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg edit cut` | `vg_commands/edit.py`, `vg_edit.py` | Remove sections |
| **Function** | `cut_video()` | `vg_edit.py` | Cut function |

**Capabilities:**
- ✅ Section cutting/removal
- ✅ Range parsing ("10-20,30-40")
- ✅ Merge adjacent cuts
- ✅ Extract and concatenate keep segments

**Example:**
```bash
vg edit cut --video input.mp4 --cuts "10-20,45-55" --output edited.mp4
```

#### Speed Adjustment
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg edit speed` | `vg_commands/edit.py`, `vg_edit.py` | Change speed |
| **Action** | `vg edit speed-silence` | `vg_commands/edit.py`, `vg_edit.py` | Speed up silent parts |
| **Function** | `speed_video()` | `vg_edit.py` | Speed function |
| **Function** | `speed_silence()` | `vg_edit.py` | Silence speedup |

**Capabilities:**
- ✅ Speed adjustment (speed up/slow down sections)
- ✅ Global or range-based speed changes
- ✅ Audio pitch preservation during speed changes
- ✅ Speed-silence: detect and speed up silent sections
- ✅ Configurable silence thresholds (dB, min duration, padding)

**Example:**
```bash
vg edit speed --video input.mp4 --factor 2.0 --output fast.mp4
vg edit speed --video input.mp4 --factor 0.5 --range "10-20" --output slow_section.mp4
vg edit speed-silence --video input.mp4 --factor 3.0 --silence-db -35 --output compressed.mp4
```

#### Video Concatenation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg edit concat` | `vg_commands/edit.py`, `vg_edit.py` | Join videos |
| **Function** | `concat_videos()` | `vg_edit.py` | Concat function |

**Capabilities:**
- ✅ Concatenate multiple videos
- ✅ FFmpeg concat demuxer
- ✅ Multiple operation chaining

**Example:**
```bash
vg edit concat --videos "part1.mp4,part2.mp4,part3.mp4" --output combined.mp4
```

---

### 5. Talking Head Generation

#### Character Generation
| Type | Files | Description |
|------|-------|-------------|
| **Function** | `generate_character()` | `vg_talking_head.py`, `generate_talking_head.py` | AI character image |

**Capabilities:**
- ✅ Character image generation (FAL.ai Flux Schnell)
- ✅ Persistent character caching
- ✅ Friendly, professional appearance

#### Talking Head Video Generation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg talking-head generate` | `vg_commands/talking_head.py`, `vg_talking_head.py` | Generate talking head |
| **Function** | `generate_talking_head()` | `vg_talking_head.py` | Generation function |

**Capabilities:**
- ✅ AI-generated talking head videos via fal.ai
- ✅ Multiple models (OmniHuman v1.5, SadTalker)
- ✅ Lip-sync with audio
- ✅ Content-based caching

**Example:**
```bash
vg talking-head generate --audio narration.mp3 --model omnihuman --output presenter.mp4
```

#### Talking Head Compositing
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg talking-head composite` | `vg_commands/talking_head.py`, `vg_talking_head.py` | Overlay talking head |
| **Function** | `composite_talking_head()` | `vg_talking_head.py` | Single overlay |
| **Function** | `composite_talking_heads()` | `vg_talking_head.py` | Multi-segment overlay |

**Capabilities:**
- ✅ Video compositing with talking heads
- ✅ Timed overlays (start_time, duration)
- ✅ Multiple segments support
- ✅ Position and size control
- ✅ Audio stripping to avoid double audio

**Example:**
```bash
vg talking-head composite --video demo.mp4 --talking-head presenter.mp4 --position bottom-right --size 280 --output final.mp4
```

#### Agentic Talking Head Overlay (NEW)
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg talking-head overlay` | `vg_commands/talking_head.py` | AI-controlled overlay |
| **Function** | `cmd_overlay()` | `vg_commands/talking_head.py` | Dumb executor |

**Capabilities:**
- ✅ Overlay multiple talking heads at AI-specified times
- ✅ No marker matching logic (AI provides exact times)
- ✅ FFmpeg overlay filters

**Example:**
```bash
vg talking-head overlay --video demo.mp4 --overlay th.mp4:47.6 --position bottom-right -o final.mp4
```

---

### 6. Quality & Optimization

#### Video Validation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg quality validate` | `vg_commands/quality.py`, `vg_quality.py` | Validate file |
| **Function** | `validate_video()` | `vg_quality.py` | Validation function |

**Capabilities:**
- ✅ File integrity checks
- ✅ Stream analysis (codec, resolution, FPS)
- ✅ FFprobe integration
- ✅ Quality validation

**Example:**
```bash
vg quality validate --file video.mp4
```

#### Quality Analysis
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg quality analyze` | `vg_commands/quality.py`, `vg_quality.py` | Analyze quality |
| **Function** | `analyze_video()` | `vg_quality.py` | Analysis function |

**Capabilities:**
- ✅ Audio-video sync analysis
- ✅ Waveform-based sync offset estimation
- ✅ Duration mismatch detection
- ✅ Quality metrics calculation
- ✅ Quality scoring

**Example:**
```bash
vg quality analyze --video final.mp4 --audio narration.mp3
```

#### Video Optimization
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg quality optimize` | `vg_commands/quality.py`, `vg_quality.py` | Compress/optimize |
| **Function** | `optimize_video()` | `vg_quality.py` | Optimization function |

**Capabilities:**
- ✅ Video compression algorithms
- ✅ Quality presets (`high`, `medium`, `low`)
- ✅ Target size optimization (`--target-size`)
- ✅ CRF-based quality control
- ✅ File size reduction
- ✅ Web optimization (faststart)

**Example:**
```bash
vg quality optimize --input raw.mp4 --output optimized.mp4 --quality medium
vg quality optimize --input raw.mp4 --output small.mp4 --target-size 10
```

---

### 7. Request File Processing

#### Request Parsing
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg request parse` | `vg_commands/request.py` | Parse request file |
| **Function** | `parse_request_file()` | `vg_commands/request.py`, `vg_core_utils/md_parser.py` | Parse function |
| **Function** | `parse_agentic_narration_from_md()` | `vg_core_utils/md_parser.py` | Parse agentic format |
| **Function** | `parse_simple_options_from_md()` | `vg_core_utils/md_parser.py` | Parse simplified options |

**Capabilities:**
- ✅ Parse markdown request files
- ✅ Extract voiceover segments
- ✅ Extract conditional segments
- ✅ Parse authentication config
- ✅ Extract actions table
- ✅ Extract scenario prompts
- ✅ Extract success criteria
- ✅ **Agentic format** — Intent-based narration (NEW)
- ✅ **Simplified options** — Clean key: value format (NEW)
- ✅ Returns `narration_format: "agentic"` or `"legacy"`

**Request Format Templates:**
- `requests/_template.md` — Legacy format (200 lines)
- `requests/_template_agentic.md` — Agentic format (60 lines, recommended)

**Example:**
```bash
vg request parse --file demo.md
```

#### Full Video Generation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg request generate` | `vg_commands/request.py` | Full pipeline |
| **Function** | `cmd_generate()` | `vg_commands/request.py` | Generation handler |

**Capabilities:**
- ✅ Pipeline orchestration
- ✅ One-command workflow
- ✅ Auto-generate TTS for all segments
- ✅ Auto-distribute audio across timeline
- ✅ Auto-generate talking heads if enabled
- ✅ Auto-trim loading spinners
- ✅ Run report generation
- ✅ Timeline marker injection into request file

**Example:**
```bash
vg request generate --file demo.md --run-id my_demo
vg request generate --file demo.md --skip-record --video existing.mp4
```

---

### 8. Narration Templates

#### Template Management
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg narration template list` | `vg_commands/narration.py`, `vg_narration_templates.py` | List templates |
| **Action** | `vg narration template render` | `vg_commands/narration.py` | Render template |
| **Action** | `vg narration template save` | `vg_commands/narration.py` | Save custom template |
| **Function** | `list_templates()` | `vg_narration_templates.py` | List function |
| **Function** | `render_template()` | `vg_narration_templates.py` | Render function |
| **Function** | `save_template()` | `vg_narration_templates.py` | Save function |

**Capabilities:**
- ✅ Dynamic narration generation
- ✅ Template management
- ✅ Built-in templates (`ai_agent_default`, `file_upload_basic`)
- ✅ Custom template saving
- ✅ Template rendering with overrides

**Example:**
```bash
vg narration template list
vg narration template render --template ai_agent_default --overrides '{"platform_name": "MyApp"}'
```

#### Batch Generation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg narration batch` | `vg_commands/narration.py` | Batch generate |
| **Function** | `cmd_batch()` | `vg_commands/narration.py` | Batch handler |

**Capabilities:**
- ✅ Batch template generation
- ✅ Multi-video narration generation

**Example:**
```bash
vg narration batch --examples examples.json --output-dir ./narrations/
```

#### Dynamic Narration Features
| Type | Files | Description |
|------|-------|-------------|
| **Helper** | `vg_narration_templates.py` | Dynamic segment handling |

**Capabilities:**
- ✅ Conditional narration segments (duration-based, marker-based)
- ✅ Repeatable segments with intervals
- ✅ Filler segments for long waits
- ✅ Narration timing optimization
- ✅ Workflow marker definitions

---

### 9. Timeline Management

#### Timeline Loading
| Type | Files | Description |
|------|-------|-------------|
| **Function** | `load_timeline_markers()` | `vg_core_utils/timeline.py` | Load markers |
| **Helper** | `parse_timeline_from_md()` | `vg_core_utils/timeline.py` | Parse MD timeline |

**Capabilities:**
- ✅ Load from JSON or Markdown
- ✅ Parse timeline markers from markdown tables
- ✅ Marker dictionary extraction

#### Timeline Validation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg validate timeline` | `vg_commands/utils.py` | Validate timeline |
| **Function** | `validate_timeline_completeness()` | `vg_core_utils/timeline.py` | Validation function |

**Capabilities:**
- ✅ Timeline validation
- ✅ Validate required markers
- ✅ Missing marker detection
- ✅ Timeline completeness checks

**Example:**
```bash
vg validate timeline --timeline timeline.json --required-markers t_page_loaded t_agent_done_1
```

#### Segment Positioning (Legacy)
| Type | Files | Description |
|------|-------|-------------|
| **Function** | `calculate_segment_times_strict()` | `vg_core_utils/timeline.py` | Strict positioning |
| **Function** | `calculate_segment_times_lenient()` | `vg_core_utils/timeline.py` | Lenient positioning |
| **Function** | `fix_overlaps_cascading()` | `vg_core_utils/timeline.py` | Fix overlaps |
| **Data Class** | `PositionedSegment` | `vg_core_utils/timeline.py` | Segment with timing |

**Capabilities:**
- ✅ Strict marker matching (fails fast)
- ✅ Lenient matching with fuzzy/inference
- ✅ Overlap detection and fixing
- ✅ Cascading delay algorithm (300ms gaps)

#### Agentic Helper Functions (NEW)
| Type | Function | Description |
|------|----------|-------------|
| **Helper** | `get_marker_time(markers, name)` | Look up specific marker time |
| **Helper** | `find_markers_containing(markers, pattern)` | Search markers by pattern |
| **Helper** | `get_timeline_summary(path)` | Get all markers for AI analysis |
| **Helper** | `apply_time_adjustment(placements, adjustment)` | Apply trim offset to placements |
| **Helper** | `check_overlaps(placements)` | Validate placements before composing |

**Capabilities:**
- ✅ AI-friendly timeline access
- ✅ No matching heuristics (AI reasons)
- ✅ Time adjustment after trim/speed operations
- ✅ Overlap validation before composing

---

### 10. Caption Generation & Subtitles

#### Caption Generation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg captions generate` | `vg_commands/captions.py`, `vg_captions.py` | Generate SRT/VTT from request + timeline |
| **Function** | `calculate_caption_times()` | `vg_captions.py` | Calculate caption timing from segments |
| **Function** | `generate_srt_file()` | `vg_captions.py` | Generate SRT subtitle file |
| **Function** | `generate_vtt_file()` | `vg_captions.py` | Generate WebVTT subtitle file |

**Capabilities**:
- ✅ Generate captions from existing voiceover text (no transcription needed)
- ✅ Calculate precise timing from timeline markers + audio durations
- ✅ Support SRT and WebVTT formats
- ✅ Automatic text wrapping (max chars per line)
- ✅ Caption timing validation (overlaps, gaps, speed)

**Example**:
```bash
vg captions generate --request demo.md --timeline timeline.md --audio-dir audio/ -o captions.srt
```

#### Streaming Captions (Word-by-Word)
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg captions streaming` | `vg_commands/captions.py`, `vg_captions.py` | Word-by-word animated captions (TikTok/YouTube style) |
| **Function** | `create_streaming_captions()` | `vg_captions.py` | Create word-level streaming captions |
| **Function** | `calculate_word_timings()` | `vg_captions.py` | Calculate per-word timing |
| **Function** | `generate_word_level_srt()` | `vg_captions.py` | Generate word-level SRT |

**Capabilities**:
- ✅ Word-by-word caption reveal (TikTok/YouTube style)
- ✅ Configurable words per group (default: 3)
- ✅ One-step video + captions output
- ✅ Trim offset support for edited videos
- ✅ Automatic timing from audio segments

**Example**:
```bash
vg captions streaming --video final.mp4 --request demo.md --timeline timeline.md --audio-dir audio/ -o captioned.mp4
vg captions streaming --video trimmed.mp4 --request demo.md --timeline timeline.md --audio-dir audio/ --trim-offset 8 -o captioned.mp4
```

#### Caption Burn-in
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg captions burn` | `vg_commands/captions.py`, `vg_captions.py` | Burn captions into video |
| **Function** | `burn_captions_into_video()` | `vg_captions.py` | FFmpeg subtitle overlay |
| **Function** | `burn_captions_with_animation()` | `vg_captions.py` | Animated caption burn-in |
| **Function** | `parse_caption_style()` | `vg_captions.py` | Parse style from CAPTIONS.md |
| **Reference** | `CAPTIONS.md` | `.claude/skills/video-generator/docs/CAPTIONS.md` | Style presets and guide |

**Capabilities**:
- ✅ Burn captions into video using FFmpeg
- ✅ Multiple style presets (youtube, professional, tiktok, accessibility)
- ✅ Customizable fonts, colors, positioning
- ✅ MD-based style configuration (no JSON)
- ✅ Inline style overrides in request files
- ✅ ASS subtitle format for advanced styling
- ✅ Fade animations (configurable duration)

**Style Presets**:
- `youtube` - Standard YouTube style (white text, black outline, bottom center)
- `professional` - Clean corporate style (subtle styling, clear readability)
- `tiktok` - Bold social media style (large text, top center)
- `accessibility` - High contrast (yellow on black, larger font)

**Example**:
```bash
vg captions burn --video final.mp4 --captions captions.srt --style youtube -o captioned.mp4
vg captions burn --video final.mp4 --captions captions.srt --style professional --no-animate -o captioned.mp4
```

#### Caption Preview
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg captions preview` | `vg_commands/captions.py` | Preview caption timing |
| **Function** | `validate_caption_timing()` | `vg_captions.py` | Timing validation |

**Capabilities**:
- ✅ Preview caption text and timing
- ✅ Validate reading speed and overlaps
- ✅ Filter by time range
- ✅ JSON output with full caption data

**Example**:
```bash
vg captions preview --request demo.md --timeline timeline.md --audio-dir audio/ --start-time 49 --duration 20
```

---

### 11. Authentication & Security

#### Authentication Handling
| Type | Files | Description |
|------|-------|-------------|
| **Function** | `load_auth_config()` | `vg_auth.py` | Load auth from file |
| **Function** | `load_auth_from_request()` | `vg_auth.py` | Load from request |
| **Function** | `_auth_from_request_data()` | `vg_auth.py` | Parse auth data |
| **Helper** | `_resolve_auth_sources()` | `vg_commands/record.py` | Resolve auth |

**Capabilities:**
- ✅ Session credential handling (cookies)
- ✅ Cookie-based authentication
- ✅ Header-based authentication
- ✅ Environment variable resolution
- ✅ Request file auth config
- ✅ JSON auth config files
- ✅ Domain extraction from URLs

---

### 12. Cost Tracking

#### Cost Estimation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg cost estimate` | `vg_commands/utils.py`, `vg_cost.py` | Estimate costs |
| **Function** | `estimate_tts_cost()` | `vg_cost.py` | TTS cost |
| **Function** | `estimate_talking_head_cost()` | `vg_cost.py` | Talking head cost |

**Capabilities:**
- ✅ TTS cost estimation (per character)
- ✅ Talking head cost estimation
- ✅ Service-specific rates

**Example:**
```bash
vg cost estimate --tts-text "Hello world" --talking-head-model omnihuman
```

#### Cost Logging & Budgets
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg cost history` | `vg_commands/utils.py`, `vg_cost.py` | View history |
| **Action** | `vg cost summary` | `vg_commands/utils.py`, `vg_cost.py` | View summary |
| **Action** | `vg cost budget` | `vg_commands/utils.py`, `vg_cost.py` | Check budget |
| **Function** | `get_cost_history()` | `vg_cost.py` | History function |
| **Function** | `get_cost_summary()` | `vg_cost.py` | Summary function |
| **Function** | `check_budget_limit()` | `vg_cost.py` | Budget check |

**Capabilities:**
- ✅ Automatic cost logging
- ✅ Cost history (by days)
- ✅ Cost summary by service
- ✅ Budget limit checking
- ✅ JSON-based cost tracking file

**Example:**
```bash
vg cost history --days 7
vg cost summary
vg cost budget --limit 50.00
```

---

### 13. Caching System

#### Cache Management
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg cache clear` | `vg_commands/utils.py` | Clear cache |
| **Action** | `vg cache status` | `vg_commands/utils.py` | Cache stats |
| **Function** | `cache_clear()` | `vg_utils.py` | Clear function |
| **Function** | `cache_status()` | `vg_utils.py` | Status function |
| **Helper** | `get_cached()` | `vg_common.py` | Get cached item |
| **Helper** | `save_to_cache()` | `vg_common.py` | Save to cache |
| **Helper** | `cache_key()` | `vg_common.py` | Generate cache key |

**Capabilities:**
- ✅ TTS caching (24-hour expiry)
- ✅ Talking head caching (24-hour expiry)
- ✅ Character image caching (persistent)
- ✅ Content-based cache keys (MD5)
- ✅ Cache metadata tracking
- ✅ Cache clearing (by type, by age)

**Example:**
```bash
vg cache status
vg cache clear --type tts --older-than 12
```

---

### 14. Utility Functions

#### Asset Management
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg list` | `vg_commands/utils.py`, `vg_utils.py` | List assets |
| **Action** | `vg info` | `vg_commands/utils.py`, `vg_utils.py` | File info |
| **Action** | `vg cleanup` | `vg_commands/utils.py`, `vg_utils.py` | Cleanup |
| **Action** | `vg status` | `vg_commands/utils.py`, `vg_utils.py` | System status |
| **Function** | `list_assets()` | `vg_utils.py` | List function |
| **Function** | `get_asset_info()` | `vg_utils.py` | Info function |
| **Function** | `cleanup_assets()` | `vg_utils.py` | Cleanup function |
| **Function** | `get_system_status()` | `vg_utils.py` | Status function |

**Capabilities:**
- ✅ List videos, audio, timelines
- ✅ Filter by type
- ✅ Recent assets listing
- ✅ Video metadata extraction (duration, resolution, fps)
- ✅ Disk usage reporting
- ✅ Asset counts
- ✅ Cache statistics
- ✅ Recent runs listing
- ✅ Age-based cleanup
- ✅ Dry-run mode

**Example:**
```bash
vg list --type video --recent 10
vg info --file demo.mp4
vg cleanup --older-than 7 --dry-run
vg status
```

#### Request Validation
| Type | CLI Command | Files | Description |
|------|-------------|-------|-------------|
| **Action** | `vg validate request` | `vg_commands/utils.py` | Validate request |
| **Function** | `validate_request_file()` | `vg_core_utils/__init__.py` | Validation function |

**Example:**
```bash
vg validate request --request demo.md
```

#### Error Handling
| Type | Files | Description |
|------|-------|-------------|
| **Class** | `VGError`, `TransientError`, `ValidationError`, etc. | `vg_common.py` | Error classes |
| **Function** | `classify_error()` | `vg_common.py` | Error classification |
| **Function** | `get_suggestion()` | `vg_common.py` | Actionable suggestions |
| **Function** | `error_response()` | `vg_common.py` | Standard error response |

**Capabilities:**
- ✅ Error type classification (`TRANSIENT`, `VALIDATION`, `AUTH_ERROR`, etc.)
- ✅ Actionable suggestions
- ✅ Standardized error responses

#### FFmpeg Resolution
| Type | Files | Description |
|------|-------|-------------|
| **Function** | `get_ffmpeg()` | `vg_common.py` | Find ffmpeg binary |
| **Function** | `require_ffmpeg()` | `vg_common.py` | Require ffmpeg |

**Capabilities:**
- ✅ System ffmpeg detection
- ✅ Node modules fallback
- ✅ ImageIO-ffmpeg fallback
- ✅ Comprehensive path resolution

#### Path Management
| Type | Files | Description |
|------|-------|-------------|
| **Function** | `run_paths()` | `project_paths.py` | Get run directory paths |
| **Class** | `RunPaths` | `project_paths.py` | Path container |

**Capabilities:**
- ✅ Run-based directory structure (`videos/runs/<run_id>/`)
- ✅ Raw video directory
- ✅ Audio directory
- ✅ Timeline file paths (JSON/MD)
- ✅ Legacy path support

---

## File Structure

```
virthrillove/                           # Workspace root
├── .claude/
│   └── skills/
│       └── video-generator/
│           ├── SKILL.md                # AI Agent guide (auto-discovered)
│           └── docs/
│               ├── VIDEO_GENERATOR_CAPABILITIES.md  # This file
│               ├── TOOLS.md            # CLI command reference
│               ├── EXAMPLES.md         # Workflow examples
│               └── CAPTIONS.md         # Caption styling guide
│
├── video-generator/
│   └── scripts/
│       ├── vg                          # CLI entry point (Python)
│       │
│       ├── vg_commands/                # CLI command handlers
│       │   ├── __init__.py             # Command exports
│       │   ├── record.py               # Recording commands
│       │   ├── audio.py                # Audio commands
│       │   ├── edit.py                 # Editing commands
│       │   ├── compose.py              # Composition commands
│       │   ├── talking_head.py         # Talking head commands
│       │   ├── quality.py              # Quality commands
│       │   ├── captions.py             # Caption commands
│       │   ├── narration.py            # Narration commands
│       │   ├── request.py              # Request file commands
│       │   └── utils.py                # Utility commands
│       │
│       ├── vg_core_utils/              # Core utility modules
│       │   ├── __init__.py             # Core exports
│       │   ├── timeline.py             # Timeline management
│       │   └── md_parser.py            # Markdown parsing
│       │
│       ├── vg_recording.py             # Recording implementation
│       ├── vg_session_simple.py        # Live session handling (CSS selectors)
│       ├── vg_agent_browser.py         # agent-browser session (ref-based)
│       ├── vg_smart_waiting.py         # Smart wait conditions
│       ├── vg_tts.py                   # TTS implementation
│       ├── elevenlabs_tts.py           # ElevenLabs API wrapper
│       ├── vg_edit.py                  # Video editing
│       ├── video_editor.py             # Editor utilities
│       ├── vg_compose.py               # Video composition
│       ├── vg_captions.py              # Caption generation
│       ├── vg_talking_head.py          # Talking head generation
│       ├── generate_talking_head.py    # Talking head utilities
│       ├── vg_quality.py               # Quality operations
│       ├── vg_narration_templates.py   # Narration templates
│       ├── vg_auth.py                  # Authentication handling
│       ├── vg_cost.py                  # Cost tracking
│       ├── vg_common.py                # Shared utilities
│       ├── vg_utils.py                 # Asset utilities
│       ├── vg_demo.py                  # Demo scenarios
│       ├── base_demo.py                # Base demo class
│       ├── project_paths.py            # Path management
│       └── video_postprocess.py        # Post-processing
│
├── requests/                           # Request file templates
│   ├── _template.md                    # Legacy template (detailed)
│   └── _template_agentic.md            # Agentic template (recommended)
│
├── videos/                             # Output directory
│   └── runs/                           # Run-based output
│       └── <run_id>/
│           ├── raw/                    # Raw recordings
│           ├── audio/                  # Generated audio
│           ├── timeline.md             # Timeline markers
│           ├── demo.mp4                # Converted video
│           ├── final.mp4               # Final output
│           └── run_report.md           # Run report
│
├── CLAUDE.md                           # Project context for AI agents
└── README.md                           # User-facing documentation
```

---

## External Integrations

| Service | Purpose | API Key Env Var | Required For |
|---------|---------|-----------------|--------------|
| **ElevenLabs** | Text-to-Speech | `ELEVENLABS_API_KEY` | `audio tts`, `audio batch`, `request generate` |
| **FAL.ai** | Talking heads, Characters | `FAL_API_KEY` | `talking-head generate` |
| **Playwright** | Browser automation | - (installed) | `record`, `record session`, `record screenshot` |
| **FFmpeg** | Video/audio processing | - (system or npm) | All video operations |

---

## Token Estimation for AI Agents

### Per-Command Token Costs (Approximate)

| Operation | Input Tokens | Output Tokens | Notes |
|-----------|--------------|---------------|-------|
| `vg request generate` | ~500 | ~2000 | Full pipeline orchestration |
| `vg record` | ~300 | ~1500 | Browser recording with markers |
| `vg compose distribute` | ~400 | ~1000 | Audio distribution |
| `vg audio tts` | ~100 | ~200 | Single TTS generation |
| `vg talking-head generate` | ~150 | ~300 | Single talking head |
| `vg quality analyze` | ~100 | ~500 | Quality analysis |
| `vg edit trim/cut/speed` | ~100 | ~200 | Simple editing |

### Typical Full Pipeline Token Usage

| Scenario | Total Input | Total Output | Operations |
|----------|-------------|--------------|------------|
| **Simple Demo** (no talking head) | ~1500 | ~5000 | record → tts → distribute |
| **Full Demo** (with talking head) | ~2500 | ~8000 | record → tts → distribute → talking-head |
| **Skip Record** (use existing video) | ~1000 | ~3000 | parse → tts → distribute |

### Implementation Steps Token Costs

| Step | Tokens | Description |
|------|--------|-------------|
| Parse request file | ~200 | Extract segments and config |
| Generate TTS (per segment) | ~150 | ElevenLabs API call |
| Record browser session | ~800 | Playwright automation |
| Convert WebM→MP4 | ~100 | FFmpeg conversion |
| Distribute audio | ~500 | Timeline-based placement |
| Generate talking heads | ~400 | FAL.ai API calls |
| Composite final | ~200 | FFmpeg overlay |

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total Python modules** | 38+ |
| **CLI command groups** | 16 |
| **Core capabilities** | 18 categories |
| **External integrations** | 5 (ElevenLabs, FAL.ai, Playwright, FFmpeg, agent-browser) |
| **Supported file formats** | MP4, WebM, MP3, M4A, WAV, JSON, Markdown, SRT, VTT, ASS |
| **Cache types** | TTS (24h), Talking Heads (24h), Characters (persistent) |
| **Browser drivers** | 2 (Playwright CSS selectors, agent-browser refs) |

---

*Generated for AI Agent orchestration and human reference.*
