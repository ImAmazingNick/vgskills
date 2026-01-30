# Video Generator Architecture

> **Version:** 2.0  
> **Last Updated:** January 2026  
> **Purpose:** Complete architecture overview with workflows and data flows

---

## Overview

The Video Generator is an AI-orchestrated system that creates professional product demo videos with voiceover, captions, and talking heads. It's designed to be used by AI agents (Claude) who read request files, make decisions, and execute commands.

**Key Principles:**
1. **Everything goes through a request file** — Even conversational prompts create one first
2. **AI decides, Python executes** — Tools are "dumb executors", AI calculates placements
3. **Iteration is easy** — Request files store timeline markers for re-runs without re-recording

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERACTION                                │
│                                                                             │
│  "Make me a demo of Improvado"    OR    "Use requests/demo.md"              │
│               │                                   │                         │
│               └─────────────┬─────────────────────┘                         │
│                             ▼                                               │
│                  ┌─────────────────────┐                                    │
│                  │    REQUEST FILE     │  ← Everything flows through this   │
│                  │  requests/demo.md   │                                    │
│                  └─────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI AGENT (Claude)                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. Read SKILL.md (auto-discovered)                                   │  │
│  │  2. Ensure request file exists (create from prompt if needed)         │  │
│  │  3. Parse request: URL, auth, scenario, narration, options            │  │
│  │  4. Record browser OR use existing video                              │  │
│  │  5. Apply edits, calculate audio placements                           │  │
│  │  6. Compose final video                                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                   ┌────────────────┼────────────────┐                       │
│                   ▼                ▼                ▼                       │
│           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│           │   Record     │ │    Audio     │ │   Compose    │               │
│           │   Browser    │ │    TTS       │ │   Video      │               │
│           └──────────────┘ └──────────────┘ └──────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VG CLI (Python)                                 │
│                                                                             │
│   vg record     vg audio      vg edit       vg compose     vg captions     │
│   vg talking-head            vg quality     vg request                      │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        Core Modules                                    │ │
│  │  vg_recording.py  vg_tts.py  vg_edit.py  vg_compose.py  vg_captions.py│ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                   ┌────────────────┼────────────────┐
                   ▼                ▼                ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │  Playwright  │ │  ElevenLabs  │ │    FFmpeg    │
           │  (Browser)   │ │  (TTS API)   │ │  (Video)     │
           └──────────────┘ └──────────────┘ └──────────────┘
                   │                │                │
                   ▼                ▼                ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │  recording   │ │   audio/     │ │  final.mp4   │
           │  .webm       │ │   *.mp3      │ │              │
           └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Request File Formats

### Format Comparison

| Feature | Legacy Format | Agentic Format |
|---------|--------------|----------------|
| **File size** | ~200 lines | ~60 lines |
| **Detail level** | Explicit markers, tables | Intent-based descriptions |
| **Marker anchors** | AI parses from tables | AI infers from narration |
| **Timing** | Explicit offsets | AI calculates |
| **Best for** | Repeatable, precise control | Quick iteration |

### Legacy Format (Detailed)

```markdown
# requests/improvado_ai_agent_demo.md

## Platform
**Name:** Improvado
**URL:** https://app.example.com

## Authentication
**Cookie Name:** session_id
**Cookie Value:** Use environment variable `SESSION_TOKEN`

## Scenario Flow
### Step 1: Open and Wait
- Navigate to URL
- Wait for page to load
...

<!-- VOICEOVER_SEGMENTS_START -->
| Segment | Anchor Marker | Offset | Text |
|---------|---------------|--------|------|
| intro | t_page_loaded | 0.5s | Welcome to... |
| prompt1 | t_prompt1_focus | 0.2s | Watch how... |
<!-- VOICEOVER_SEGMENTS_END -->

## Options
### Editing
- **Trim Start:** 8 seconds
- **Speed Gaps:** yes, 3x
```

### Agentic Format (Simplified)

```markdown
# requests/improvado_ai_agent_agentic.md

## Platform
**URL:** https://app.example.com

## Authentication
**Cookie Name:** dts_sessionid
**Cookie Value:** Use environment variable `DTS_SESSIONID`

## Goal
Record a demo showing the AI Agent creating a dashboard.

## Scenario Flow
1. Navigate to URL and wait for load
2. Type: "Create marketing dashboard"
3. Press Enter, wait for AI to finish
4. Scroll to show results

## Narration
1. **intro** (after page loads): "Welcome to..."
2. **typing** (when typing starts): "Watch how..."
3. **reveal** (when result appears): "Here's your..."

## Options
- **Voiceover:** yes
- **Speed gaps:** yes, 3x
- **Trim start:** 8 seconds
```

---

## Unified Workflow

**Everything flows through a request file.** Even conversational prompts create one first.

### Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                     │
│                                                                         │
│  "Make me a demo of Improvado"    OR    "Use requests/demo.md"          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Ensure Request File Exists                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Has request file?                                                      │
│  ├── YES → Parse it                                                     │
│  └── NO  → AI creates one (agentic format)                              │
│            ┌────────────────────────────────────────────────┐           │
│            │  AI gathers from user:                         │           │
│            │  - URL to record                               │           │
│            │  - Authentication method                       │           │
│            │  - What to show (scenario)                     │           │
│            │  - What to say (narration)                     │           │
│            │  - Options (voiceover, speed-gaps, etc.)       │           │
│            │                                                │           │
│            │  Creates: requests/<name>.md                   │           │
│            └────────────────────────────────────────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Recording (or skip if video exists)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Has existing video? (--skip-record --video v.mp4)                      │
│  ├── YES → Skip to Step 3                                               │
│  └── NO  → Record browser                                               │
│            │                                                            │
│            ├── SIMPLE (known platform, actions table)?                  │
│            │   → $ vg request generate --file demo.md                   │
│            │     (automated recording)                                  │
│            │                                                            │
│            └── COMPLEX (new platform, conditional logic)?               │
│                → Session recording (AI drives browser)                  │
│                  snapshot → think → act → verify                        │
│                                                                         │
│  Output: recording.webm + timeline.md (markers with times)              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Edit Video                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Apply edits from request Options:                                      │
│  - Trim start/end                                                       │
│  - Speed up gaps (3x)                                                   │
│  - Cut sections                                                         │
│                                                                         │
│  Each edit returns adjustments → AI recalculates marker times           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Generate Audio & Compose                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  For each narration segment in request:                                 │
│  1. Generate TTS → get duration                                         │
│  2. Calculate placement time from adjusted markers                      │
│  3. Place audio at exact times                                          │
│                                                                         │
│  Optional: Add talking heads, captions                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                           ┌──────────────┐
                           │  final.mp4   │
                           └──────────────┘
```

---

## The Complete Flow (Detailed)

Whether user provides a request file or asks conversationally, the flow is the same:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: REQUEST FILE                                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User says: "Make me a demo of Improvado AI Agent"                       │
│                                                                          │
│  AI asks (if needed):                                                    │
│  - "What URL should I record?"                                           │
│  - "How do I authenticate? (cookie, login, none)"                        │
│  - "What should the video show?"                                         │
│  - "What narration do you want?"                                         │
│                                                                          │
│  AI creates: requests/improvado_demo.md                                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ ## Platform                                                         │ │
│  │ **URL:** https://report.improvado.io/...                            │ │
│  │                                                                     │ │
│  │ ## Authentication                                                   │ │
│  │ **Cookie Name:** dts_sessionid                                      │ │
│  │ **Cookie Value:** Use environment variable `DTS_SESSIONID`          │ │
│  │                                                                     │ │
│  │ ## Scenario Flow                                                    │ │
│  │ 1. Navigate to URL, wait for load                                   │ │
│  │ 2. Type: "Create marketing dashboard"                               │ │
│  │ 3. Wait for AI to finish                                            │ │
│  │                                                                     │ │
│  │ ## Narration                                                        │ │
│  │ 1. **intro** (after page loads): "Welcome to..."                    │ │
│  │ 2. **reveal** (when result appears): "Here's your..."               │ │
│  │                                                                     │ │
│  │ ## Options                                                          │ │
│  │ - **Voiceover:** yes                                                │ │
│  │ - **Speed gaps:** yes, 3x                                           │ │
│  │ - **Trim start:** 8 seconds                                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  OR user provides: requests/improvado_ai_agent_demo.md (already exists)  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: RECORDING                                                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Option A: Automated (request has Actions table)                         │
│  ─────────────────────────────────────────────                           │
│  $ vg request generate --file requests/demo.md                           │
│                                                                          │
│  Pipeline reads Actions table, executes each step, records markers.      │
│                                                                          │
│                                                                          │
│  Option B: Session-based (new platform, no Actions table)                │
│  ─────────────────────────────────────────────────────────               │
│  AI drives the browser interactively:                                    │
│                                                                          │
│  $ vg record session start --run-id demo --url "..." --request demo.md   │
│                                                                          │
│  Loop:                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  $ vg record session do --action snapshot                           │ │
│  │  → Returns: elements, state                                         │ │
│  │                                                                     │ │
│  │  AI thinks: "I see textarea, need to click it"                      │ │
│  │                                                                     │ │
│  │  $ vg record session do --action click --selector "textarea"        │ │
│  │  $ vg record session do --action marker --value "t_prompt1_focus"   │ │
│  │  $ vg record session do --action type --selector "textarea" \       │ │
│  │      --value "Create dashboard" --delay-ms 45                       │ │
│  │  $ vg record session do --action press --value "Enter"              │ │
│  │                                                                     │ │
│  │  ... verify with snapshot, continue until done ...                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  $ vg record session stop --run-id demo                                  │
│  → Returns: video path, duration, markers                                │
│                                                                          │
│                                                                          │
│  Option C: Skip recording (existing video)                               │
│  ─────────────────────────────────────────                               │
│  $ vg request generate --file demo.md --skip-record --video existing.mp4 │
│                                                                          │
│  Uses timeline markers already in the request file (from previous run).  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: TIMELINE (markers from recording)                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  timeline.md (or appended to request file):                              │
│                                                                          │
│  | Marker                | Time (s) |                                    │
│  |-----------------------|----------|                                    │
│  | t_start_recording     | 0.00     |                                    │
│  | t_page_loaded         | 33.11    |                                    │
│  | t_prompt1_focus       | 107.15   |                                    │
│  | t_processing1_started | 123.22   |                                    │
│  | t_agent_done_1        | 260.79   |                                    │
│  | t_scroll_start        | 352.76   |                                    │
│                                                                          │
│  These markers are the synchronization points for audio placement.       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: EDITING                                                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Apply edits from Options, each returns adjustments:                     │
│                                                                          │
│  $ vg edit trim --video v.mp4 --start 8 -o trimmed.mp4                   │
│  → Returns: {"adjustment": {"type": "offset", "seconds": -8}}            │
│                                                                          │
│  AI recalculates: 33.11 - 8 = 25.11                                      │
│                                                                          │
│  $ vg edit speed-gaps --video trimmed.mp4 --factor 3 -o fast.mp4         │
│  → Returns: {"time_map": [[25.11, 10.2], [99.15, 42.3], ...]}            │
│                                                                          │
│  AI uses time_map to find new positions for each marker.                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: AUDIO GENERATION                                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  For each narration segment:                                             │
│                                                                          │
│  $ vg audio tts --text "Welcome to Improvado..." -o intro.mp3            │
│  → Returns: {"duration_s": 4.2, "path": "audio/intro.mp3"}               │
│                                                                          │
│  $ vg audio tts --text "Watch how easy..." -o prompt1.mp3                │
│  → Returns: {"duration_s": 3.8, "path": "audio/prompt1.mp3"}             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 6: COMPOSITION                                                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  AI calculates final placements:                                         │
│                                                                          │
│  | Segment | Anchor         | Offset | Mapped Time | Final    |          │
│  |---------|----------------|--------|-------------|----------|          │
│  | intro   | t_page_loaded  | 0.5s   | 10.2        | 10.7s    |          │
│  | prompt1 | t_prompt1_focus| 0.2s   | 42.3        | 42.5s    |          │
│  | reveal  | t_agent_done_1 | 0.5s   | 98.5        | 99.0s    |          │
│                                                                          │
│  $ vg compose place --video fast.mp4 \                                   │
│      --audio intro.mp3:10.7 \                                            │
│      --audio prompt1.mp3:42.5 \                                          │
│      --audio reveal.mp3:99.0 \                                           │
│      -o final.mp4                                                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 7: OPTIONAL ENHANCEMENTS                                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Talking heads (if enabled):                                             │
│  $ vg talking-head generate --audio intro.mp3 -o th_intro.mp4            │
│  $ vg talking-head overlay --video final.mp4 \                           │
│      --overlay th_intro.mp4:10.7 --position bottom-right -o with_th.mp4  │
│                                                                          │
│  Captions (if enabled):                                                  │
│  $ vg captions streaming --video final.mp4 --request demo.md \           │
│      --timeline timeline.md --audio-dir audio/ -o captioned.mp4          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                           ┌──────────────┐
                           │  final.mp4   │
                           │  Complete!   │
                           └──────────────┘
```

---

## Iteration: Refining the Video

After first run, the request file has real timeline markers. User can iterate:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ITERATION WORKFLOW                                                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  First run: Recording captured, timeline markers saved to request file   │
│                                                                          │
│  <!-- TIMELINE_MARKERS_START -->                                         │
│  | t_page_loaded | 33.11 |                                               │
│  | t_agent_done_1 | 260.79 |  ← Processing took 227 seconds!             │
│  <!-- TIMELINE_MARKERS_END -->                                           │
│                                                                          │
│  User reviews: "Processing is too long, let's add filler narration"      │
│                                                                          │
│  AI updates Narration section:                                           │
│  + **processing1** (during AI work): "The AI is analyzing your data..."  │
│  + **processing2** (15s later): "Building your dashboard layout..."      │
│                                                                          │
│  Re-run with existing video:                                             │
│  $ vg request generate --file demo.md --skip-record --video recording.mp4│
│                                                                          │
│  → New audio, same video, perfect sync                                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Timeline Markers

Timeline markers are the synchronization points between video and audio.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RECORDING PHASE                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
     Browser actions create markers │
                                    ▼
     ┌──────────────────────────────────────────────────────────────┐
     │  timeline.md (generated during recording)                     │
     │                                                               │
     │  | Marker | Time (s) |                                        │
     │  |--------|----------|                                        │
     │  | t_start_recording | 0.00 |                                 │
     │  | t_page_loaded | 33.11 |                                    │
     │  | t_prompt1_focus | 107.15 |                                 │
     │  | t_prompt1_typed | 116.40 |                                 │
     │  | t_processing1_started | 123.22 |                           │
     │  | t_agent_done_1 | 260.79 |                                  │
     │  | t_prompt2_focus | 272.98 |                                 │
     │  | t_agent_done_2 | 347.75 |                                  │
     │  | t_scroll_start | 352.76 |                                  │
     │  | t_recording_complete | 369.99 |                            │
     │                                                               │
     └──────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EDITING PHASE                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
     $ vg edit trim --start 8      │  Adjustment: -8s
                                    ▼
     ┌──────────────────────────────────────────────────────────────┐
     │  After Trim (AI recalculates)                                 │
     │                                                               │
     │  | Marker | Original | After Trim |                           │
     │  |--------|----------|------------|                           │
     │  | t_page_loaded | 33.11 | 25.11 |                            │
     │  | t_prompt1_focus | 107.15 | 99.15 |                         │
     │  | t_agent_done_1 | 260.79 | 252.79 |                         │
     │                                                               │
     └──────────────────────────────────────────────────────────────┘
                                    │
     $ vg edit speed-gaps --factor 3 │  Returns time_map
                                    ▼
     ┌──────────────────────────────────────────────────────────────┐
     │  After Speed-Gaps (time_map from tool)                        │
     │                                                               │
     │  time_map: [                                                  │
     │    [25.11, 10.2],    # t_page_loaded: 25.11 → 10.2            │
     │    [99.15, 42.3],    # t_prompt1_focus: 99.15 → 42.3          │
     │    [252.79, 98.5],   # t_agent_done_1: 252.79 → 98.5          │
     │  ]                                                            │
     │                                                               │
     │  scale_factor: 0.38 (video compressed to 38% of length)       │
     │                                                               │
     └──────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         AUDIO PLACEMENT                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
     AI uses mapped times           │
                                    ▼
     ┌──────────────────────────────────────────────────────────────┐
     │  Final Placements (calculated by AI)                          │
     │                                                               │
     │  | Segment | Anchor | Offset | Final Time |                   │
     │  |---------|--------|--------|------------|                   │
     │  | intro | t_page_loaded | 0.5s | 10.7s |                     │
     │  | prompt1 | t_prompt1_focus | 0.2s | 42.5s |                 │
     │  | reveal1 | t_agent_done_1 | 0.5s | 99.0s |                  │
     │                                                               │
     │  $ vg compose place --video fast.mp4 \                        │
     │      --audio intro.mp3:10.7 \                                 │
     │      --audio prompt1.mp3:42.5 \                               │
     │      --audio reveal1.mp3:99.0 \                               │
     │      -o final.mp4                                             │
     │                                                               │
     └──────────────────────────────────────────────────────────────┘
```

---

## Output Structure

```
videos/runs/<run_id>/
├── raw/
│   ├── recording.webm         # Original browser recording
│   └── screenshots/           # Debug screenshots at key moments
├── audio/
│   ├── intro.mp3              # TTS segments
│   ├── prompt1.mp3
│   ├── processing1.mp3
│   ├── reveal1.mp3
│   └── ...
├── timeline.md                # Extracted markers with timestamps
├── demo.mp4                   # Converted from webm
├── trimmed.mp4                # After trim
├── fast.mp4                   # After speed-gaps
├── final.mp4                  # Final output with audio
└── run_report.md              # Metadata, issues, screenshots
```

---

## Component Reference

### Recording Components

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **Session Recording** | AI-driven browser control (CSS selectors) | `vg_session_simple.py` |
| **agent-browser Recording** | AI-driven browser control (ref-based) | `vg_agent_browser.py` |
| **Automated Recording** | Action-table execution | `vg_recording.py` |
| **Smart Waiting** | Detect AI completion | `vg_smart_waiting.py` |
| **Timeline** | Marker management | `vg_core_utils/timeline.py` |

### Dual Browser Driver Architecture

The Video Generator supports two browser automation drivers for recording:

| Driver | Selector Method | Best For | Commands |
|--------|----------------|----------|----------|
| **current** (Playwright) | CSS selectors | Known platforms, stable UIs | `vg record session start/do/stop` |
| **agent-browser** (Vercel Labs) | Element refs (@e1, @e2) | New platforms, dynamic UIs | `vg record session agent-start/do/stop` |

**Selecting a driver:**
- Set `Browser Driver: agent-browser` in request file Options section
- Or omit for default Playwright driver

**agent-browser advantages:**
- Refs from accessibility tree are more stable than CSS selectors
- AI can read snapshot and pick best ref for action
- Less breakage when UIs change (button moved, class renamed)

**Both drivers produce identical output:**
- `.webm` video file in `raw/` directory
- `timeline.md` with marker timestamps
- Compatible with all editing, TTS, and composition commands

### Audio Components

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **TTS Generation** | Text-to-speech via ElevenLabs | `vg_tts.py`, `elevenlabs_tts.py` |
| **Audio Caching** | MD5-based 24h cache | `vg_common.py` |

### Video Components

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **Editing** | Trim, cut, speed, concat | `vg_edit.py` |
| **Composition** | Audio placement, overlay | `vg_compose.py` |
| **Captions** | SRT generation, burn-in | `vg_captions.py` |
| **Talking Heads** | AI presenter generation | `vg_talking_head.py` |

---

## API Keys Required

| Service | Environment Variable | Purpose |
|---------|---------------------|---------|
| ElevenLabs | `ELEVENLABS_API_KEY` | Text-to-speech |
| FAL.ai | `FAL_API_KEY` | Talking head generation (optional) |
| Platform Auth | `DTS_SESSIONID` (example) | Browser authentication |

---

## Error Handling

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Error Classification                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TRANSIENT        → Network/API issues → Retry with backoff             │
│  VALIDATION       → Bad input → Fix parameters                          │
│  AUTH_ERROR       → Missing API key → Set environment variable          │
│  FILE_NOT_FOUND   → Bad path → Check file exists                        │
│  CONFIG_ERROR     → Setup issue → Check dependencies                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

All CLI commands return JSON with `success: true/false` and actionable error messages.

---

## Quick Reference

### Automated Pipeline
```bash
vg request generate --file demo.md
```

### Skip Recording (Use Existing Video)
```bash
vg request generate --file demo.md --skip-record --video existing.mp4
```

### Session-Based Recording (Playwright - CSS selectors)
```bash
vg record session start --run-id demo --url "..." --request demo.md
vg record session do --run-id demo --action snapshot
vg record session do --run-id demo --action click --selector "textarea"
vg record session do --run-id demo --action marker --value "t_prompt1_focus"
vg record session stop --run-id demo
```

### agent-browser Recording (ref-based - recommended for new platforms)
```bash
vg record session agent-start --run-id demo --url "..." --cookie "session=abc" --cookie-domain ".example.com"
vg record session agent-do --run-id demo --action snapshot -i    # Get refs
vg record session agent-do --run-id demo --action click --ref "@e5"
vg record session agent-do --run-id demo --action type --ref "@e12" --value "Create dashboard"
vg record session agent-do --run-id demo --action marker --value "t_prompt1_focus"
vg record session agent-stop --run-id demo
```

### Agentic Composition
```bash
vg audio tts --text "Welcome..." -o intro.mp3        # Returns duration
vg edit trim --video v.mp4 --start 8 -o trimmed.mp4  # Returns adjustment
vg edit speed-gaps --video v.mp4 --factor 3 -o fast.mp4  # Returns time_map
vg compose place --video fast.mp4 --audio intro.mp3:10.2 -o final.mp4
```

---

## See Also

- **[SKILL.md](.claude/skills/video-generator/SKILL.md)** — AI workflow guide
- **[TOOLS.md](.claude/skills/video-generator/docs/TOOLS.md)** — CLI parameters
- **[EXAMPLES.md](.claude/skills/video-generator/docs/EXAMPLES.md)** — Workflow examples
- **[requests/_template_agentic.md](requests/_template_agentic.md)** — Request file template
