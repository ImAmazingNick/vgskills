# Video Generator Tools Reference

Complete reference for all `vg` CLI commands and their parameters.

> **Quick Start**: For most use cases, just run `vg request generate --file <request.md>`  
> **AI Agent Guide**: See `SKILL.md` for decision tree and workflows  
> **Capabilities Overview**: See `VIDEO_GENERATOR_CAPABILITIES.md` for architecture

---

## Command Structure

All commands follow the pattern: `vg <group> <subcommand> [options]`

## 📋 Request Commands

### `vg request parse`

Parse a video request file and extract structured data.

```bash
vg request parse --file <request.md>
```

**Parameters:**
- `--file`, `-f` (required): Path to request file (.md)

**Output:**
```json
{
  "success": true,
  "request": {
    "platform": {"name": "...", "url": "..."},
    "authentication": {"cookie_name": "...", "cookie_value": "..."},
    "voiceover_segments": [
      {"id": "intro", "anchor_marker": "t_page_loaded", "offset": "0.5s", "text": "..."}
    ],
    "options": {"voiceover_enabled": true, "talking_head_enabled": false}
  },
  "segments_count": 7,
  "has_voiceover": true,
  "has_talking_head": true
}
```

### `vg request generate`

Generate a complete video from a request file (one command does everything).

```bash
vg request generate --file <request.md> [options]
```

**Parameters:**
- `--file`, `-f` (required): Path to request file (.md)
- `--run-id` (optional): Run ID for output folder (auto-generated if not provided)
- `--skip-record` (flag): Skip recording, use existing video
- `--video` (optional): Path to existing video (use with --skip-record)

**Example:**
```bash
# Full workflow from request file
vg request generate --file my_demo.md --skip-record --video recording.webm --run-id my_demo
```

**Output:**
```json
{
  "success": true,
  "run_id": "improvado_20260127_215500",
  "run_dir": "/path/to/videos/runs/improvado_20260127_215500",
  "steps": [
    {"step": "tts", "segment": "intro", "success": true, "audio": "/path/to/intro.mp3"},
    {"step": "tts", "segment": "prompt1", "success": true, "audio": "/path/to/prompt1.mp3"},
    {"step": "compose_distribute", "success": true, "segments_distributed": 7}
  ],
  "final_video": "/path/to/final.mp4",
  "manifest": "/path/to/manifest.json"
}
```

## 🎬 Recording Commands

### `vg record`

Record browser sessions with timeline markers.

```bash
vg record --url <url> --scenario <name> [options]
```

**Parameters:**
- `--url` (required): URL to record
- `--scenario` (optional): Recording scenario (`ai-agent`, `simple-dashboard`) default: `ai-agent`
- `--headless` (flag): Run in headless mode
- `--session-cookie` (optional): Session cookie for authentication (format: name=value)
- `--request` (optional): Request file (.md) with platform-specific authentication details
- `--run-id` (optional): Custom run ID for output organization

**Examples:**
```bash
# Record with manual authentication
vg record --url "https://app.example.com" --scenario ai-agent --session-cookie "session_id=abc123"

# Record using authentication from request file (recommended)
vg record --request requests/my_platform.md --run-id my_recording

# Record public website (no authentication needed)
vg record --url "https://public-demo.com" --scenario simple-dashboard --headless
```

**Authentication Methods:**
- **No Authentication**: Public websites and demos
- **Session Cookies**: Standard cookie-based auth (name=value format)
- **Environment Variables**: Reference env vars in request files (e.g., `DTS_SESSIONID`)
- **Request File Auth**: Platform-specific auth defined in .md request files

**How it works:**
1. Reads authentication method from request file or command line
2. Launches browser with appropriate authentication
3. Navigates to the target URL
4. Records user interactions according to the scenario or request actions
5. Takes screenshots at key moments for timeline markers
6. Saves video, timeline JSON, and screenshots

**Output:**
```json
{
  "success": true,
  "video": "/path/to/video.mp4",
  "timeline": "/path/to/timeline.json",
  "duration": 45.2,
  "markers": {...},
  "scenario": "ai-agent",
  "url": "https://app.example.com"
}
```

### `vg record session` (CSS selectors)

AI-driven recording with CSS selectors.

```bash
vg record session start --run-id demo --url "https://..." --cookie "s=abc" --cookie-domain ".example.com"
vg record session do --run-id demo --action snapshot
vg record session do --run-id demo --action click --selector "textarea"
vg record session do --run-id demo --action type --selector "textarea" --value "text" --delay-ms 45
vg record session do --run-id demo --action marker --value "t_step_done"
vg record session stop --run-id demo
```

**Actions:** `snapshot`, `click`, `type`, `fill`, `press`, `wait`, `scroll`, `marker`

### `vg record session agent-*` (ref-based)

AI-driven recording with element refs (`@e1`, `@e5`) — more stable than CSS selectors.

```bash
vg record session agent-start --run-id demo --url "https://..." --cookie "s=abc" --cookie-domain ".example.com"
vg record session agent-do --run-id demo --action snapshot -i   # Returns refs: @e1, @e5...
vg record session agent-do --run-id demo --action click --ref "@e5"
vg record session agent-do --run-id demo --action type --ref "@e5" --value "text"
vg record session agent-do --run-id demo --action marker --value "t_step_done"
vg record session agent-stop --run-id demo
```

**Actions:** Same as above, but use `--ref "@e5"` instead of `--selector "css"`.  
**Output:** `.webm` + `timeline.md` — compatible with rest of pipeline.

## 🧭 Narration Commands

### `vg narration template list`

List available narration templates.

```bash
vg narration template list
```

### `vg narration template render`

Render a template to a narration JSON payload.

```bash
vg narration template render --template ai_agent_default --overrides '{"prompt_text":"Create KPI dashboard"}' --output ./narration.json
```

### `vg narration template save`

Save a custom narration template from JSON.

```bash
vg narration template save --file ./my_template.json --id custom_demo --overwrite
```

### `vg narration batch`

Generate narration JSONs for multiple examples.

```bash
vg narration batch --examples ./narration_examples.json --output-dir ./narrations
```

Example input file:
```json
{
  "examples": [
    {"template": "ai_agent_default", "overrides": {"prompt_text": "Create KPI dashboard"}},
    {"video_type": "file_upload", "overrides": {"file_type": "CSV"}}
  ]
}
```

### `vg record screenshot`

Take a screenshot of a web page.

```bash
vg record screenshot --url <url> --output <path> [options]
```

**Parameters:**
- `--url` (required): URL to screenshot
- `--output`, `-o` (required): Output screenshot path
- `--selector` (optional): CSS selector to wait for before taking screenshot
- `--full-page` (flag): Capture full page instead of viewport only
- `--session-cookie` (optional): Session cookie for authentication

**Examples:**
```bash
vg record screenshot --url "https://app.example.com" --output dashboard.png
vg record screenshot --url "https://app.com" --selector ".dashboard-loaded" --full-page --output full_dashboard.png
vg record screenshot --url "https://app.com" --session-cookie "abc123" --output authenticated.png
```

**Output:**
```json
{
  "success": true,
  "screenshot": "/path/to/screenshot.png",
  "size": 245760,
  "url": "https://app.example.com",
  "full_page": false,
  "selector": null
}
```

## 🔊 Audio Commands

### `vg audio tts`

Generate speech from text using ElevenLabs.

```bash
vg audio tts --text <text> --output <path> [options]
```

**Parameters:**
- `--text` (required): Text to convert to speech (or path to text file)
- `--voice` (optional): Voice ID (alloy, echo, fable, onyx, nova, shimmer) default: `alloy`
- `--output` (required): Output audio file path
- `--no-cache` (flag): Skip cache and force regeneration

**Examples:**
```bash
vg audio tts --text "Welcome to our platform" --voice alloy --output welcome.mp3
vg audio tts --text ./script.txt --output narration.mp3
vg audio tts --text "Hello world" --no-cache --output fresh.mp3
```

### `vg audio batch`

Generate TTS for multiple segments in parallel.

```bash
vg audio batch --segments <json_file> --output-dir <dir> [options]
```

**Parameters:**
- `--segments` (required): JSON file with segments array
- `--output-dir` (required): Output directory for audio files
- `--voice` (optional): Voice ID default: `alloy`

**Segment JSON format:**
```json
[
  {"id": "intro", "text": "Welcome to our demo"},
  {"id": "features", "text": "Here are the key features"}
]
```

## ✂️ Editing Commands

### `vg edit trim`

Trim video start/end times.

```bash
vg edit trim --video <input> --start <seconds> --output <output> [options]
```

**Parameters:**
- `--video` (required): Input video file
- `--start` (required): Start time in seconds
- `--end` (optional): End time in seconds
- `--output` (required): Output video file

### `vg edit cut`

Cut out sections from video.

```bash
vg edit cut --video <input> --cuts <ranges> --output <output>
```

**Parameters:**
- `--video` (required): Input video file
- `--cuts` (required): Cut ranges "start1-end1,start2-end2"
- `--output` (required): Output video file

### `vg edit speed`

Change video speed.

```bash
vg edit speed --video <input> --factor <num> --output <output> [options]
```

**Parameters:**
- `--video` (required): Input video file
- `--factor` (required): Speed factor (e.g., 2.0 for 2x speed)
- `--range` (optional): Time range "start-end" in seconds
- `--output` (required): Output video file

### `vg edit concat`

Concatenate multiple videos.

```bash
vg edit concat --videos <paths> --output <output>
```

**Parameters:**
- `--videos` (required): Comma-separated video paths
- `--output` (required): Output video file

## 🎭 Talking Head Commands

### `vg talking-head generate`

Generate talking head video from audio.

```bash
vg talking-head generate --audio <input> --output <output> [options]
```

**Parameters:**
- `--audio` (required): Input audio file
- `--output` (required): Output video file
- `--character` (optional): Character image path
- `--model` (optional): Model (`omnihuman`, `sadtalker`) default: `omnihuman`

### `vg talking-head composite`

Overlay talking head onto main video.

```bash
vg talking-head composite --video <main> --talking-head <overlay> --output <output> [options]
```

**Parameters:**
- `--video` (required): Main video file
- `--talking-head` (required): Talking head video file
- `--output` (required): Output video file
- `--position` (optional): Position (`top-left`, `top-right`, `bottom-left`, `bottom-right`) default: `bottom-right`
- `--size` (optional): Size in pixels default: `280`
- `--start-time` (optional): Start time in seconds default: `0`

## 🎵 Composition Commands

### `vg compose sync`

Sync audio with video (simple mux - plays audio from start).

```bash
vg compose sync --video <input> --audio <input> --output <output> [options]
```

**Parameters:**
- `--video` (required): Video file
- `--audio` (required): Audio file
- `--output` (required): Output video file
- `--run-id` (optional): Run ID to group assets together
- `--timeline` (optional): Timeline JSON for advanced sync

### `vg compose distribute`

**SIMPLIFIED**: Distribute audio segments across video timeline using STRICT marker requirements. No fallback logic - requires exact timeline markers like the powerful previous solution.

```bash
vg compose distribute --video <input> --request <request.md> --audio-dir <dir> --output <output> [options]
```

**Parameters:**
- `--video` (required): Video file
- `--request`, `-r` (required): Request file (.md) with voiceover segments and timing markers
- `--audio-dir` (required): Directory containing audio segment files (e.g., intro.mp3, prompt1.mp3)
- `--output`, `-o` (required): Output video path
- `--run-id` (optional): Run ID to group assets together
- `--timeline` (optional): Timeline JSON file with marker timestamps (required for precise positioning)

**How it works:**
1. **Parses request file** for voiceover segments with anchor markers and offsets
2. **Requires timeline markers** - fails fast if markers are missing (no fallbacks)
3. **Positions each segment** at exact timeline position + offset
4. **Fixes overlaps automatically** using 300ms cascading delays (like previous solution)
5. **Professional audio mixing** with ffmpeg adelay + amix filters and normalization

**Key Differences from Previous Complex Version:**
- ✅ **Strict requirements**: Requires exact timeline markers (fails fast if missing)
- ✅ **Simple overlap handling**: 300ms cascading delays only
- ✅ **No fallback modes**: No sequential/strict-timeline options
- ✅ **Predictable behavior**: Same logic as powerful previous solution

**Example:**
```bash
vg compose distribute \
  --video demo.mp4 \
  --request requests/my_demo.md \
  --audio-dir videos/runs/my_demo/audio \
  --output final.mp4 \
  --timeline videos/runs/my_demo/timeline.json
```

**Output:**
```json
{
  "success": true,
  "video": "/path/to/final.mp4",
  "segments_distributed": 7,
  "placements": [
    {"id": "intro", "start_time": 52.3, "duration": 3.2},
    {"id": "prompt1", "start_time": 112.8, "duration": 2.1}
  ],
  "video_duration": 235.36,
  "timeline_used": true,
  "placement_mode": "strict_timeline",
  "overlaps_fixed": 2
}
```

### `vg compose place`

**AGENTIC**: Place audio at AI-specified times with automatic overlap fixing.

```bash
vg compose place --video <input> --audio <file:time> [--audio <file:time>...] --output <output>
```

**Parameters:**
- `--video` (required): Video file
- `--audio` (required, repeatable): Audio placement as `file.mp3:start_time`
- `--output`, `-o` (required): Output video path
- `--no-fix-overlaps` (optional): Disable automatic overlap fixing

**Auto-fix Overlaps (default ON):**
- Sorts audio by start time
- Detects overlaps based on duration
- Delays overlapping segments by 300ms after previous ends
- Reports fixes in output

**Example:**
```bash
vg compose place \
  --video demo.mp4 \
  --audio intro.mp3:33.6 \
  --audio prompt1.mp3:107.3 \
  --audio reveal.mp3:261.3 \
  -o final.mp4
```

**Output (with overlap fix):**
```json
{
  "success": true,
  "video": "final.mp4",
  "segments_placed": 3,
  "overlaps_fixed": [{"file": "prompt1.mp3", "original_start": 35.0, "adjusted_start": 43.5}]
}
```

### `vg compose overlay`

Overlay videos (picture-in-picture).

```bash
vg compose overlay --video <main> --overlay <pip> --output <output> [options]
```

**Parameters:**
- `--video` (required): Main video file
- `--overlay` (required): Overlay video file
- `--output` (required): Output video file
- `--position` (optional): Position default: `bottom-right`
- `--size` (optional): Size percentage default: `30`

## 📊 Quality Commands

### `vg quality validate`

Validate video/audio file integrity.

```bash
vg quality validate --file <path>
```

**Parameters:**
- `--file` (required): File to validate

### `vg quality analyze`

Analyze video quality and sync.

```bash
vg quality analyze --video <path> [options]
```

**Parameters:**
- `--video` (required): Video file to analyze
- `--audio` (optional): Audio file to compare

### `vg quality optimize`

Compress and optimize video.

```bash
vg quality optimize --input <path> --output <output> [options]
```

**Parameters:**
- `--input` (required): Input video file
- `--output` (required): Output video file
- `--target-size` (optional): Target size in MB
- `--quality` (optional): Quality preset (`high`, `medium`, `low`) default: `high`

## 🔧 Utility Commands

### `vg list`

List video/audio assets.

```bash
vg list [options]
```

**Parameters:**
- `--type` (optional): Asset type (`video`, `audio`, `timeline`)
- `--recent` (optional): Show N most recent

### `vg info`

Get detailed file information.

```bash
vg info --file <path>
```

**Parameters:**
- `--file` (required): File path

### `vg cleanup`

Clean up temporary files.

```bash
vg cleanup [options]
```

**Parameters:**
- `--older-than` (optional): Remove files older than N days
- `--dry-run` (flag): Show what would be deleted

### `vg status`

Show system status.

```bash
vg status
```

### `vg cache clear`

Clear cache entries.

```bash
vg cache clear [options]
```

**Parameters:**
- `--type` (optional): Cache type (`tts`, `talking_head`)
- `--older-than` (optional): Clear entries older than N hours

### `vg cache status`

Show cache statistics.

```bash
vg cache status
```

## 🔍 Validation Commands

### `vg validate timeline`

Validate that timeline contains all required markers for video generation.

```bash
vg validate timeline --timeline <timeline.json> [--required-markers <marker1> <marker2> ...]
```

**Parameters:**
- `--timeline` (required): Timeline JSON file path
- `--required-markers` (optional): List of marker names that must be present

**Example:**
```bash
vg validate timeline --timeline videos/runs/my_demo/timeline.json --required-markers t_page_loaded t_prompt1_focus t_processing1_started
```

**Output:**
```json
{
  "valid": true,
  "missing_markers": [],
  "available_markers": ["t_page_loaded", "t_prompt1_focus", "t_processing1_started", "t_recording_complete"],
  "marker_count": 4,
  "timeline_path": "videos/runs/my_demo/timeline.json"
}
```

### `vg validate request`

Validate that a request file has all required components for video generation.

```bash
vg validate request --request <request.md>
```

**Parameters:**
- `--request` (required): Request file path

**Example:**
```bash
vg validate request --request requests/my_demo.md
```

**Output:**
```json
{
  "valid": true,
  "issues": [],
  "segment_count": 7,
  "platform": "Improvado",
  "url": "https://report.improvado.io/experimental/agent/new-agent/",
  "has_voiceover": true
}
```

## 💰 Cost Commands

### `vg cost estimate`

Estimate costs for operations.

```bash
vg cost estimate [options]
```

**Parameters:**
- `--tts-text` (optional): Text for TTS cost estimation
- `--tts-voice` (optional): Voice ID for TTS
- `--talking-head-model` (optional): Model for talking head cost

### `vg cost history`

Show cost history.

```bash
vg cost history [options]
```

**Parameters:**
- `--days` (optional): Days to look back default: `7`

### `vg cost summary`

Show total costs by service.

```bash
vg cost summary
```

### `vg cost budget`

Check budget status.

```bash
vg cost budget --limit <amount>
```

**Parameters:**
- `--limit` (required): Budget limit in USD

## 📝 Caption Commands

### `vg captions generate`

Generate caption file (SRT/VTT) from request file and timeline.

```bash
vg captions generate --request <request.md> --timeline <timeline.md> --audio-dir <dir> --output <output>
```

**Parameters:**
- `--request` (required): Path to request MD file
- `--timeline` (required): Path to timeline MD file
- `--audio-dir` (required): Path to audio directory
- `--output`, `-o` (required): Output path for caption file
- `--format` (optional): Caption format (`srt` or `vtt`) default: `srt`
- `--no-validate` (flag): Skip timing validation

**Output:**
```json
{
  "success": true,
  "caption_file": "/path/to/captions.srt",
  "caption_count": 7,
  "format": "srt",
  "total_duration": 125.5,
  "validation": {"valid": true, "issues": []}
}
```

### `vg captions streaming`

Create streaming word-by-word captions (TikTok/YouTube style). Burns captions directly into video.

```bash
vg captions streaming --video <input> --request <request.md> --output <output> [options]
```

**Parameters:**
- `--video` (required): Path to input video
- `--request` (required): Path to request MD file
- `--timeline` (required): Path to timeline MD file
- `--audio-dir` (required): Path to audio directory
- `--output`, `-o` (required): Output path for captioned video
- `--words` (optional): Words per group default: `3`
- `--font-size` (optional): Font size in FFmpeg units default: `10`
- `--trim-offset` (optional): Seconds trimmed from original default: `0`

**Example:**
```bash
vg captions streaming --video demo.mp4 --request demo.md --timeline timeline.md --audio-dir audio/ -o captioned.mp4
```

**Output:**
```json
{
  "success": true,
  "output": "/path/to/captioned.mp4",
  "word_groups": 45,
  "style": "streaming"
}
```

### `vg captions burn`

Burn captions from SRT file into video with style presets.

```bash
vg captions burn --video <input> --captions <captions.srt> --output <output> [options]
```

**Parameters:**
- `--video` (required): Path to input video
- `--captions` (required): Path to SRT caption file
- `--output`, `-o` (required): Path to output video
- `--style` (optional): Caption style preset (`youtube`, `professional`, `tiktok`, `accessibility`) default: `professional`
- `--request` (optional): Request file for inline style overrides
- `--no-animate` (flag): Disable fade animations
- `--fade-duration` (optional): Fade animation duration in seconds default: `0.2`

**Example:**
```bash
vg captions burn --video final.mp4 --captions captions.srt --style youtube -o captioned.mp4
```

**Output:**
```json
{
  "success": true,
  "output": "/path/to/captioned.mp4",
  "style": "youtube",
  "caption_count": 7
}
```

### `vg captions preview`

Preview caption timing and text before burning.

```bash
vg captions preview --captions <captions.srt> [options]
```

**Parameters:**
- `--captions` (optional): Path to existing SRT file to preview
- `--request` (optional): Path to request MD file (for generating captions)
- `--timeline` (optional): Path to timeline MD file (for generating captions)
- `--audio-dir` (optional): Path to audio directory (for generating captions)
- `--start-time` (optional): Start time in seconds
- `--duration` (optional): Duration to preview in seconds

**Example:**
```bash
vg captions preview --request demo.md --timeline timeline.md --audio-dir audio/ --start-time 49 --duration 20
```

---

## Error Codes

All commands return structured errors with actionable suggestions:

- **TRANSIENT**: Network/API issues (may succeed on retry)
- **VALIDATION**: Input parameter errors
- **AUTH_ERROR**: Missing or invalid API keys
- **CONFIG_ERROR**: Configuration/setup issues
- **FILE_NOT_FOUND**: File path issues
- **NOT_IMPLEMENTED**: Feature not yet available

## Environment Variables

- `ELEVENLABS_API_KEY`: ElevenLabs TTS API key
- `FAL_API_KEY`: FAL.ai talking head API key
- `DTS_SESSIONID`: Session cookie for authenticated recording