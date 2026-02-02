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
vg compose place --video fast.mp4 --audio intro.mp3:10.2 --audio reveal.mp3:98.5 -o final.mp4
```

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

User asks → You figure out timing and placement.

### Workflow A: Overlay TH (during video)

TH appears as picture-in-picture while narration plays.

```bash
# Option 1: From existing audio
vg talking-head generate --audio audio/intro.mp3 -o th_intro.mp4
# → Returns: {"duration": 4.2}

# Option 2: Create from text (TTS + generate in one step)
vg talking-head create --text "Hi! I'm your guide." -o th_intro.mp4
# → Returns: {"video": "th_intro.mp4", "audio": "th_intro.mp3", "duration_s": 2.1}

# Overlay at calculated time (you read timeline, add offset)
vg talking-head overlay --video final.mp4 --overlay th_intro.mp4:33.6 -o final_th.mp4
```

**CRITICAL:** The overlay command uses `-itsoffset` internally to sync TH frame 0 with the overlay start time.

### Workflow B: Fullscreen Intro TH

TH appears fullscreen before main video starts.

```bash
# 1. Create TH
vg talking-head create --text "Welcome! Let me show you something amazing." -o th_intro.mp4
# → duration_s: 3.2

# 2. Concat: TH first, then main video
vg edit concat --videos "th_intro.mp4,main.mp4" -o final.mp4

# 3. Recalculate all subsequent times
# All marker times += 3.2s (TH duration)
# t_page_loaded: 25.11 → 28.31
```

### Workflow C: Fullscreen Outro TH

TH appears at the end.

```bash
# 1. Create TH
vg talking-head create --text "Thanks for watching!" -o th_outro.mp4

# 2. Concat: main video first, then TH
vg edit concat --videos "main.mp4,th_outro.mp4" -o final.mp4

# No time recalculation needed (TH is at end)
```

### Workflow D: Insert TH Between Segments

Insert a TH segment in the middle of the video.

```bash
# 1. Determine insert point (e.g., after intro ends at t=15s)
# 2. Split video
vg edit trim --video main.mp4 --end 15 -o before.mp4
vg edit trim --video main.mp4 --start 15 -o after.mp4

# 3. Create TH
vg talking-head create --text "Now let me show you more." -o th_middle.mp4
# → duration_s: 4.0

# 4. Concat
vg edit concat --videos "before.mp4,th_middle.mp4,after.mp4" -o final.mp4

# 5. Recalculate: times > 15s get += 4.0s
```

**CRITICAL:** You always recalculate times after concat. Tools don't do this automatically.

### Request File TH Section

Users can specify TH-specific text in `## Talking Heads`:

```markdown
## Talking Heads
1. **th_intro** (at: 0): "Hi! I'm your guide."
2. **th_processing** (at: t_processing1_started + 5s): "Working..."
```

Timing hints: `0` (intro), `end` (outro), `t_marker`, `t_marker + 5s`

Positions: `bottom-right`, `bottom-left`, `top-right`, `top-left`

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
| Speed gaps | `vg edit speed-gaps --video v.mp4 --request r.md --timeline t.md --audio-dir audio/ --factor 3 -o fast.mp4` |
| Speed silence | `vg edit speed-silence --video v.mp4 --factor 3 -o out.mp4` |
| **Compose** | |
| Simple sync | `vg compose sync --video v.mp4 --audio a.mp3 -o final.mp4` |
| Place at times | `vg compose place --video v.mp4 --audio a.mp3:10.5 -o final.mp4` (auto-fixes overlaps) |
| **Captions** | |
| Streaming | `vg captions streaming --video v.mp4 --request r.md --timeline t.md --audio-dir audio/ -o final.mp4` |
| Burn SRT | `vg captions burn --video v.mp4 --captions c.srt -o final.mp4` |
| **Talking Head** | |
| Create from text | `vg talking-head create --text "Hi!" -o th.mp4` (TTS + generate) |
| Generate from audio | `vg talking-head generate --audio a.mp3 -o presenter.mp4` |
| Overlay at time | `vg talking-head overlay --video v.mp4 --overlay th.mp4:10.5 -o final.mp4` |
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
