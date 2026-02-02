---
name: video-generator
description: Creates demo videos with voiceover and editing. Use when user asks to create videos, record browser demos, add narration, or edit video.
---

# Video Generator

CLI tool for creating demo videos. Run from workspace root:

```bash
python3 video-generator/scripts/vg <command>
```

---

## Quick Decision

```
SIMPLE SCENARIO (known platform, standard flow)?
  → vg request generate --file demo.md

COMPLEX SCENARIO (new platform, conditional logic)?
  → Check request file for "Browser Driver" option:
    - "agent-browser" → Use Workflow B2 (agent-session commands, ref-based)
    - "current" or not specified → Use Workflow B (session commands, CSS selectors)

EXISTING VIDEO (skip recording)?
  → vg request generate --file demo.md --skip-record --video v.mp4

FULL CONTROL OVER TIMING?
  → Agentic workflow (you calculate placements)
```

---

## Workflow A: Automated (simple cases)

```bash
vg request generate --file requests/demo.md
```

Done. Outputs to `videos/runs/<run_id>/final.mp4`.

**To inspect a request file first:**
```bash
vg request parse --file demo.md
# Returns:
# OK
# url: https://...
# scenario_flow_text: 1. Open page...
# voiceover_segments: 3 segments
```

---

## Workflow B: Interactive Recording (complex cases)

For new platforms, conditional flows, or when automation fails.

**Loop: snapshot → think → act → verify**

```bash
# 1. Start session
vg record session start --run-id demo --url "https://..." --cookie "session=abc" --cookie-domain ".example.com"

# 2. See the page
vg record session do --run-id demo --action snapshot

# 3. Act based on what you see
vg record session do --run-id demo --action click --selector "button:has-text('Submit')"
vg record session do --run-id demo --action type --selector "textarea" --value "Create dashboard" --delay-ms 45
vg record session do --run-id demo --action press --value "Enter"
vg record session do --run-id demo --action wait --wait-s 2
vg record session do --run-id demo --action marker --value "t_step_done"

# 4. Verify (snapshot again), then repeat or stop
vg record session stop --run-id demo
```

**Tips:**
- **AI agents:** "Data Query Error" or similar errors in chat = IGNORE. Don't stop, don't react. Agents auto-retry. Just keep waiting and snapshot periodically until done.
- **Dropdowns:** Text snapshots miss dropdown contents. Use keyboard: `press ArrowDown` → `press Enter`
- **Long operations:** Add `--response-timeout 120` to snapshot commands

**After recording:**
1. Convert webm to mp4 (recording outputs .webm)
2. Generate TTS for narration
3. Apply edits (trim, speed-gaps) 
4. Compose with audio placements

See Workflow C for details.

---

## Workflow B2: agent-browser Recording (recommended for new platforms)

Uses ref-based element selection (`@e1`, `@e5`) instead of CSS selectors — more stable when UIs change.

```bash
# Start (auto-records)
vg record session agent-start --run-id demo --url "https://..." --cookie "s=abc" --cookie-domain ".example.com"

# Snapshot → get refs → act
vg record session agent-do --run-id demo --action snapshot -i   # Returns @e1, @e5...
vg record session agent-do --run-id demo --action click --ref "@e5"
vg record session agent-do --run-id demo --action type --ref "@e5" --value "Create dashboard"
vg record session agent-do --run-id demo --action press --value "Enter"
vg record session agent-do --run-id demo --action marker --value "t_submitted"

# Stop (saves .webm + timeline.md)
vg record session agent-stop --run-id demo
```

**vs Workflow B:** Uses `agent-start/do/stop` + refs (`@e5`) instead of `start/do/stop` + CSS selectors.

**AI agent errors:** IGNORE "Data Query Error" in chat. Don't wait, don't react—just continue snapshotting until result appears.

**After recording:** Same pipeline — convert, TTS, edit, compose.

---

## Workflow C: Agentic Composition (full control)

You calculate exact placements. Tools return data for your calculations.

### Step 1: Generate TTS (get durations)

```bash
vg audio tts --text "Welcome to the platform" -o intro.mp3
# Returns:
# OK
# duration: 4.2s
# path: intro.mp3
```

### Step 2: Read timeline

Check `videos/runs/<id>/timeline.md` for marker times:
```
t_page_loaded | 33.11
t_agent_done_1 | 260.79
```

### Step 3: Apply edits (get adjustments)

```bash
# Trim
vg edit trim --video v.mp4 --start 8 -o trimmed.mp4
# Returns:
# OK
# adjustment: -8.0s
# → Recalculate: 33.11 - 8 = 25.11

# Speed-gaps (requires --request + --timeline + --audio-dir)
vg edit speed-gaps --video trimmed.mp4 --factor 3 \
  --request demo.md --timeline timeline.md --audio-dir audio/ -o fast.mp4
# Returns time_map: 25.11s → 10.2s (use for final placements)
```

### Step 4: Compose with explicit times

```bash
# Recommended: Use --strict for agentic workflows (fails on overlaps instead of auto-fixing)
vg compose place --video fast.mp4 --audio intro.mp3:10.2 --audio reveal.mp3:98.5 --strict -o final.mp4

# Without --strict: auto-fixes overlaps but warns loudly
vg compose place --video fast.mp4 --audio intro.mp3:10.2 --audio reveal.mp3:98.5 -o final.mp4
```

**`--strict` mode:** Fails if overlaps detected. You recalculate times.
**Without `--strict`:** Auto-fixes overlaps with 300ms gaps, but shows VERY prominent warning.

### CRITICAL: Workflow Order

```
CORRECT (with speed-gaps):
  Record → Trim → TTS → Calculate placements → Speed-gaps → Recalculate with time_map → Compose

CORRECT (simple, no speed-up):
  Record → Trim → TTS → Calculate placements → Compose

WRONG: Record → Trim → Speed-gaps (fails - needs placements first!)
WRONG: Record → Trim → Compose → Speed-silence (audio out of sync)
```

**Why this order:** `speed-gaps` needs to know WHERE audio will be placed to determine what are "gaps". It speeds up everything EXCEPT where audio plays. After speeding, it returns `time_map` to recalculate final placements.

---

## Talking Heads

**Three types** - use the right one:

| Type | Command | Resolution | Use Case |
|------|---------|------------|----------|
| **Overlay** | `vg talking-head create` | Square (960x960) | PiP during video narration |
| **Segment** | `vg talking-head segment` / `intro` / `outro` | Video resolution | Standalone intro/middle/outro with presenter |
| **Title** | `vg talking-head title` | Video resolution | AI-generated title cards (no presenter) |

---

### Overlay TH (square, PiP)

TH appears as picture-in-picture while narration plays. **Square format is correct for overlays.**

```bash
# Create square TH for overlay
vg talking-head create --text "Watch this feature..." -o th_overlay.mp4
# → Returns: {"video": "th_overlay.mp4", "duration_s": 2.1}

# Overlay at calculated time
vg talking-head overlay --video final.mp4 --overlay th_overlay.mp4:33.6 -o final_th.mp4
```

---

### Fullscreen TH Segments (video resolution)

Standalone segments at start, middle, or end. **Auto-generates YouTuber studio character.**

These commands create a realistic presenter in a professional YouTuber studio setting:
- Full 16:9 aspect ratio (not a square face on background)
- Professional studio lighting and setup
- Suitable for intro, outro, or mid-video transitions

```bash
# Intro (at start) - auto-generates studio character
vg talking-head intro --text "Welcome!" --match-video main.mp4 -o th_intro.mp4
# → Fullscreen YouTuber studio video at main.mp4's resolution

# Outro (at end)
vg talking-head outro --text "Thanks for watching!" --match-video main.mp4 -o th_outro.mp4

# In-between segment (middle of video)
vg talking-head segment --text "Now let me explain..." --match-video main.mp4 -o th_transition.mp4

# Or specify resolution directly
vg talking-head segment --text "Hi!" --resolution 1280x720 -o th_segment.mp4

# Use custom character image (must be 16:9 for fullscreen)
vg talking-head intro --text "Hi!" --character my_studio.png --match-video main.mp4 -o th_intro.mp4
```

**Options:**
- `--match-video`: Match resolution from existing video (recommended)
- `--resolution`: Explicit resolution (e.g., `1280x720`)
- `--character`: Custom character image (16:9 studio image recommended for fullscreen)

---

### Concatenating TH Segments

Concat auto-normalizes resolutions now:

```bash
# Intro + main
vg edit concat --videos "th_intro.mp4,main.mp4" -o final.mp4

# Main + outro
vg edit concat --videos "main.mp4,th_outro.mp4" -o final.mp4

# Intro + middle + outro
vg edit concat --videos "th_intro.mp4,part1.mp4,th_transition.mp4,part2.mp4,th_outro.mp4" -o final.mp4
```

**CRITICAL:** Recalculate times after concat. TH at start pushes all times forward.

---

### Title Card Videos (AI-generated transitions)

Create cinematic title/transition videos without a presenter using **xAI Grok Imagine Video**. Perfect for section headers.

```bash
# Basic title card
vg talking-head title --text "Part 2: Dashboard Building" -o title.mp4

# With style and matching resolution
vg talking-head title --text "Key Features" --style tech --match-video main.mp4 -o title.mp4

# Custom duration (minimum 3s, Grok generates 6s then trims)
vg talking-head title --text "Summary" --duration 3 --style minimal -o title.mp4
```

**Styles:**
- `cinematic` (default) — Dramatic lighting, elegant typography
- `tech` — Futuristic, neon accents, digital aesthetic
- `minimal` — Clean, simple, professional
- `gradient` — Colorful flowing backgrounds
- `dynamic` — Energetic motion graphics

**Note:** Uses `xai/grok-imagine-video/text-to-video` for direct text-to-video generation.

---

### When to Use Which

| Scenario | Command |
|----------|---------|
| Narration during video (PiP) | `vg talking-head create` + `overlay` |
| Welcome/hook before main | `vg talking-head intro` + `concat` |
| Section header (no presenter) | `vg talking-head title` + `concat` |
| Transition between sections | `vg talking-head segment` + `concat` |
| Call-to-action at end | `vg talking-head outro` + `concat` |
| No talking head | Just use voiceover audio |

---

### Request File TH Section

```markdown
## Talking Heads
1. **th_intro** (at: 0): "Hi! I'm your guide."
2. **th_processing** (at: t_processing1_started + 5s): "Working..."
3. **th_outro** (at: end): "Thanks for watching!"
```

Timing hints: `0` (intro), `end` (outro), `t_marker`, `t_marker + 5s`

---

## Core Commands

| Task | Command |
|------|---------|
| **Pipeline** | |
| Full pipeline | `vg request generate --file demo.md` |
| Parse request | `vg request parse --file demo.md` |
| **Audio** | |
| TTS single | `vg audio tts --text "..." -o audio.mp3` |
| TTS batch | `vg audio batch --request demo.md -o audio/` |
| **Edit** | |
| Trim | `vg edit trim --video v.mp4 --start 5 -o out.mp4` |
| Concat (auto-normalizes resolution) | `vg edit concat --videos "a.mp4,b.mp4" -o out.mp4` |
| Speed gaps | `vg edit speed-gaps --video v.mp4 --request r.md --timeline t.md --audio-dir audio/ --factor 3 -o fast.mp4` |
| Speed silence | `vg edit speed-silence --video v.mp4 --factor 3 -o out.mp4` |
| **Compose** | |
| Simple sync | `vg compose sync --video v.mp4 --audio a.mp3 -o final.mp4` |
| Place at times (strict) | `vg compose place --video v.mp4 --audio a.mp3:10.5 --strict -o final.mp4` (fails on overlap) |
| Place at times (auto-fix) | `vg compose place --video v.mp4 --audio a.mp3:10.5 -o final.mp4` (fixes overlaps, warns loudly) |
| **Captions** | |
| Streaming | `vg captions streaming --video v.mp4 --request r.md --timeline t.md --audio-dir audio/ -o final.mp4` |
| Burn SRT | `vg captions burn --video v.mp4 --captions c.srt -o final.mp4` |
| **Talking Head - Overlay (square, PiP)** | |
| Create from text | `vg talking-head create --text "Hi!" -o th.mp4` (TTS + generate, square) |
| Generate from audio | `vg talking-head generate --audio a.mp3 -o presenter.mp4` |
| Overlay at time | `vg talking-head overlay --video v.mp4 --overlay th.mp4:10.5 -o final.mp4` |
| **Talking Head - Segment (video resolution)** | |
| Intro segment | `vg talking-head intro --text "Welcome!" --match-video main.mp4 -o intro.mp4` |
| Outro segment | `vg talking-head outro --text "Thanks!" --match-video main.mp4 -o outro.mp4` |
| Any segment | `vg talking-head segment --text "..." --resolution 1280x720 -o seg.mp4` |
| **Title Cards (AI-generated, no presenter)** | |
| Title video | `vg talking-head title --text "Part 2" --style cinematic -o title.mp4` |
| **Utils** | |
| Video info | `vg info --file video.mp4` |
| Convert webm→mp4 | `./node_modules/ffmpeg-static/ffmpeg -i in.webm -c:v libx264 out.mp4` |

---

## Request File Format

```markdown
## Platform
**URL:** https://app.example.com

## Authentication
**Cookie Name:** session_id
**Cookie Value:** From environment variable `SESSION_TOKEN`

## Goal
Show how to create a dashboard with AI.

## Scenario Flow
1. Open page, wait for load
2. Type prompt in textarea
3. Press Enter, wait for result

## Narration
1. **intro** (after page loads): "Welcome to the platform."
2. **reveal** (when result appears): "Here are the results."

## Options
- **Speed gaps:** yes, 3x
- **Trim start:** 5 seconds
```

---

## Timeline Markers

Add markers at key moments during recording:

| Marker | When to add |
|--------|-------------|
| `t_page_loaded` | Auto-added on session start |
| `t_prompt1_focus` | Before clicking input |
| `t_processing1_started` | When AI starts (shows "Thinking") |
| `t_agent_done_1` | When AI finishes |

---

## Output

All outputs in `videos/runs/<run_id>/`:
- `final.mp4` — Final video
- `audio/` — TTS segments
- `timeline.md` — Markers with times

---

## Environment

```bash
export ELEVENLABS_API_KEY=...  # Required for TTS
export FAL_API_KEY=...         # Optional, talking heads
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| TTS 403 error | Rate limit. Wait 5s, retry. |
| Recording blank | Auth cookie expired or not applied |
| Login page despite cookie | Cookie domain wrong. Use `.example.com` (with leading dot) |
| Audio out of sync | Wrong order. Do: TTS → speed-gaps → compose |
| webm not playing | Convert to mp4 first |
| speed-gaps "placements required" | Use `--request + --timeline + --audio-dir` (never create JSON manually) |
| speed-gaps crashes "no audio" | Fixed: now handles videos without audio track |
| Markers all 0.00s | Fixed: was bug in agent-browser start time tracking |
| talking-head create crashes | Fixed: now auto-generates character if not provided |
| concat outputs square video | Fixed: auto-normalizes resolution. Or use `--target-resolution 1280x720` |
| Intro/outro TH is square | Fixed: `intro/outro/segment` now auto-generate YouTuber studio character (fullscreen 16:9). Use `create` only for PiP overlays. |
| compose place shifts times silently | Use `--strict` flag to fail on overlaps instead |
| Dropdown not visible | Use keyboard: `press ArrowDown` → `press Enter` |
| AI agent shows error | IGNORE IT. "Data Query Error" etc. = normal. Don't stop. Keep snapshotting until result appears. |
| Click blocked | Press Escape first |
| TH freezes/wrong frame | Fixed in code. Uses `-itsoffset` to delay TH input stream. |

---

## More Details

- [docs/VIDEO_GENERATOR_CAPABILITIES.md](docs/VIDEO_GENERATOR_CAPABILITIES.md) — Complete command reference
- [docs/TOOLS.md](docs/TOOLS.md) — CLI command parameters
- [docs/CAPTIONS.md](docs/CAPTIONS.md) — Caption styling
- [docs/EXAMPLES.md](docs/EXAMPLES.md) — Workflow examples
