# Improvado AI Dashboard Demo Video Plan

## Goal
Create a demo video showing Improvado's AI agent building a cross-channel marketing dashboard from a simple prompt.

## Target
- **URL:** https://report.improvado.io/experimental/agent/new-agent/?workspace=121
- **Cookie Domain:** .improvado.io
- **Run ID:** improvado_ai_dashboard

## Video Flow

### Scene 1: Page Load (0-5s)
- Show the AI agent interface loading
- **Voiceover:** "Meet Improvado's AI Agent — your intelligent assistant for building marketing dashboards."

### Scene 2: Typing the Prompt (5-15s)
- User types "Create a simple cross-channel marketing dashboard" with realistic typing delay
- **Voiceover:** "Simply describe what you need in plain English."

### Scene 3: AI Processing (15-90s estimated)
- AI agent shows thinking/processing state
- AI generates the dashboard components
- **Voiceover:** "The AI analyzes your request and automatically builds the dashboard — selecting the right data sources, metrics, and visualizations."

### Scene 4: Dashboard Reveal (final section)
- Show the completed dashboard
- **Voiceover:** "In seconds, you have a fully functional cross-channel marketing dashboard ready for insights."

---

## Implementation Steps

### Step 1: Start Recording Session
```bash
vg record session agent-start --run-id improvado_ai_dashboard \
  --url "https://report.improvado.io/experimental/agent/new-agent/?workspace=121" \
  --cookie "dts_sessionid=j7gjsg7hsozunox3oamr299l45vo3nsp" \
  --cookie-domain ".improvado.io"
```
**Token estimate:** ~500 tokens
**Status:** [x] Done

### Step 2: Take Initial Snapshot & Explore UI
```bash
vg record session agent-do --run-id improvado_ai_dashboard --action snapshot -i
```
- Identify the input field ref for typing
- Add marker: `t_page_loaded`
**Token estimate:** ~800 tokens per snapshot
**Status:** [x] Done

### Step 3: Type the Prompt
```bash
vg record session agent-do --run-id improvado_ai_dashboard --action click --ref "@eX"  # input field
vg record session agent-do --run-id improvado_ai_dashboard --action marker --value "t_prompt_focus"
vg record session agent-do --run-id improvado_ai_dashboard --action type --ref "@eX" --value "Create a simple cross-channel marketing dashboard" --delay-ms 45
vg record session agent-do --run-id improvado_ai_dashboard --action marker --value "t_prompt_typed"
```
**Token estimate:** ~1,000 tokens
**Status:** [x] Done

### Step 4: Submit & Wait for AI
```bash
vg record session agent-do --run-id improvado_ai_dashboard --action press --value "Enter"
vg record session agent-do --run-id improvado_ai_dashboard --action marker --value "t_processing_started"
# Wait for AI to complete (60-180 seconds typically)
vg record session agent-do --run-id improvado_ai_dashboard --action wait --wait-s 120
vg record session agent-do --run-id improvado_ai_dashboard --action snapshot -i
```
**Token estimate:** ~2,000 tokens (multiple snapshots to monitor)
**Status:** [x] Done

### Step 5: Capture Dashboard Result
```bash
vg record session agent-do --run-id improvado_ai_dashboard --action marker --value "t_dashboard_complete"
vg record session agent-do --run-id improvado_ai_dashboard --action snapshot -i
```
**Token estimate:** ~800 tokens
**Status:** [x] Done

### Step 6: Stop Recording
```bash
vg record session agent-stop --run-id improvado_ai_dashboard
```
**Token estimate:** ~200 tokens
**Status:** [x] Done

### Step 7: Convert WebM to MP4
```bash
./node_modules/ffmpeg-static/ffmpeg -i videos/runs/improvado_ai_dashboard/recording.webm -c:v libx264 videos/runs/improvado_ai_dashboard/recording.mp4
```
**Token estimate:** ~100 tokens
**Status:** [x] Done

### Step 8: Generate TTS Audio
```bash
vg audio tts --text "Meet Improvado's AI Agent — your intelligent assistant for building marketing dashboards." -o videos/runs/improvado_ai_dashboard/audio/intro.mp3

vg audio tts --text "Simply describe what you need in plain English." -o videos/runs/improvado_ai_dashboard/audio/typing.mp3

vg audio tts --text "The AI analyzes your request and automatically builds the dashboard — selecting the right data sources, metrics, and visualizations." -o videos/runs/improvado_ai_dashboard/audio/processing.mp3

vg audio tts --text "In seconds, you have a fully functional cross-channel marketing dashboard ready for insights." -o videos/runs/improvado_ai_dashboard/audio/reveal.mp3
```
**Token estimate:** ~800 tokens
**Status:** [x] Done

### Step 9: Read Timeline & Calculate Placements
- Read `videos/runs/improvado_ai_dashboard/timeline.md`
- Map marker times to audio placements
- Adjust for any trim offset
**Token estimate:** ~500 tokens
**Status:** [x] Done

### Step 10: Trim Video (if needed)
```bash
vg edit trim --video videos/runs/improvado_ai_dashboard/recording.mp4 --start X -o videos/runs/improvado_ai_dashboard/trimmed.mp4
```
**Token estimate:** ~200 tokens
**Status:** [x] Done

### Step 11: Speed Up Gaps
```bash
vg edit speed-gaps --video videos/runs/improvado_ai_dashboard/trimmed.mp4 --factor 3 \
  --request improvado_ai_dashboard_demo.md --timeline timeline.md --audio-dir audio/ \
  -o videos/runs/improvado_ai_dashboard/fast.mp4
```
**Token estimate:** ~300 tokens
**Status:** [x] Done

### Step 12: Compose Final Video
```bash
vg compose place --video videos/runs/improvado_ai_dashboard/fast.mp4 \
  --audio intro.mp3:X --audio typing.mp3:Y --audio processing.mp3:Z --audio reveal.mp3:W \
  -o videos/runs/improvado_ai_dashboard/final.mp4
```
**Token estimate:** ~300 tokens
**Status:** [x] Done

---

## Total Estimated Tokens
- Recording phase: ~5,500 tokens
- Post-processing: ~2,200 tokens
- **Total: ~7,700 tokens**

## Output Location
`videos/runs/improvado_ai_dashboard/final.mp4`

## Narration Script

| Segment | Trigger | Text |
|---------|---------|------|
| intro | t_page_loaded | "Meet Improvado's AI Agent — your intelligent assistant for building marketing dashboards." |
| typing | t_prompt_focus | "Simply describe what you need in plain English." |
| processing | t_processing_started | "The AI analyzes your request and automatically builds the dashboard — selecting the right data sources, metrics, and visualizations." |
| reveal | t_dashboard_complete | "In seconds, you have a fully functional cross-channel marketing dashboard ready for insights." |
