# Video Generator Examples

Comprehensive examples of video generation workflows using the `vg` CLI.

---

## ⭐ Recommended: One-Command Workflow

### From Request File (Best)
```bash
# Everything in one command - record, TTS, distribute, final output
vg request generate --file my_demo.md
```

### With Existing Video
```bash
# Skip recording, use existing video
vg request generate --file my_demo.md --skip-record --video existing.webm
```

---

## 🔄 Iterative Workflow (No Request File)

When user doesn't have a request file, AI generates one and refines after recording.

### Step 1: Create Initial Request File

```markdown
## Platform
**URL:** https://app.example.com

## Authentication
**Type:** cookie
**Cookie Name:** session_id
**Cookie Value:** From environment variable `SESSION_TOKEN`

<!-- VOICEOVER_SEGMENTS_START -->
| ID | Anchor | Offset | Text |
|----|--------|--------|------|
| intro | t_page_loaded | 0.5 | Welcome to our platform... |
| action1 | t_prompt1_focus | 0.0 | Let's ask a question... |
| result | t_agent_done_1 | 1.0 | Here are the results! |
<!-- VOICEOVER_SEGMENTS_END -->
```

### Step 2: First Pass (Get Timeline)
```bash
vg request generate --file request.md
# Output: videos/runs/<id>/timeline.md with actual markers
```

### Step 3: Review Timeline
```bash
# Check actual timing
cat videos/runs/<id>/timeline.md

# Example output:
# | t_page_loaded | 2.5 |
# | t_prompt1_focus | 8.2 |
# | t_processing1_started | 12.0 |
# | t_agent_done_1 | 45.3 |  ← Processing took 33 seconds!
```

### Step 4: Refine Narration

Update request.md based on actual timing:
```markdown
<!-- VOICEOVER_SEGMENTS_START -->
| ID | Anchor | Offset | Text |
|----|--------|--------|------|
| intro | t_page_loaded | 0.5 | Welcome to our platform... |
| action1 | t_prompt1_focus | 0.0 | Let's ask a question... |
| processing1 | t_processing1_started | 3.0 | The AI is analyzing... |
| processing2 | t_processing1_started | 15.0 | Building your dashboard... |
| result | t_agent_done_1 | 1.0 | Here are the results! |
<!-- VOICEOVER_SEGMENTS_END -->
```

### Step 5: Regenerate Final Video
```bash
vg request generate --file request.md --skip-record --video videos/runs/<id>/demo.mp4
# Output: Perfect narration synced to actual video timing
```

---

## 🚀 Quick Start Examples

### Taking Screenshots
```bash
# Take a screenshot of a dashboard
vg record screenshot --url "https://dashboard.example.com" --output dashboard.png

# Take a full-page screenshot with authentication
vg record screenshot --url "https://app.example.com" --session-cookie "your_session" --full-page --output full_app.png

# Wait for specific element before screenshot
vg record screenshot --url "https://app.com" --selector ".dashboard-loaded" --output loaded_dashboard.png
```

### Basic Demo Recording
```bash
# Record a simple dashboard demo
vg record --url "https://dashboard.example.com" --scenario simple-dashboard --headless

# Record AI agent workflow with authentication
vg record --url "https://app.example.com" --scenario ai-agent --session-cookie "your_session_id"
```

### AI-Driven Recording (agent-browser)
```bash
# Start session with ref-based element selection
vg record session agent-start --run-id demo --url "https://app.example.com" --cookie "s=abc" --cookie-domain ".example.com"

# Snapshot → get element refs
vg record session agent-do --run-id demo --action snapshot -i
# Returns: @e1: button "Submit", @e5: textbox "Prompt"...

# Act using refs (stable even when UI changes)
vg record session agent-do --run-id demo --action click --ref "@e5"
vg record session agent-do --run-id demo --action type --ref "@e5" --value "Create dashboard"
vg record session agent-do --run-id demo --action press --value "Enter"
vg record session agent-do --run-id demo --action marker --value "t_submitted"

# Stop → outputs .webm + timeline.md
vg record session agent-stop --run-id demo
```

### Simple Voiceover
```bash
# Generate voiceover for recorded demo
vg audio tts --text "Welcome to our analytics dashboard. This tool helps you visualize your data." --output welcome.mp3

# Sync voiceover with video
vg compose sync --video demo.mp4 --audio welcome.mp3 --output demo_with_voice.mp4
```

## 🎬 Complete Workflow Examples

### 1. Professional Product Demo

**Goal**: Create a complete product demo with voiceover and talking head presenter.

```bash
# 1. Record the product demo
vg record --url "https://app.example.com" --scenario ai-agent --run-id demo_session
# Output will be in videos/runs/demo_session/

# 2. Generate voiceover script
vg audio tts --text "Welcome to our AI-powered analytics platform. Watch as our agent creates a comprehensive dashboard." --output intro.mp3

# 3. Generate talking head presenter
vg talking-head generate --audio intro.mp3 --output presenter.mp4 --model omnihuman

# 4. Combine everything
vg compose sync --video videos/runs/demo_session/demo.mp4 --audio intro.mp3 --output demo_with_audio.mp4
vg talking-head composite --video demo_with_audio.mp4 --talking-head presenter.mp4 --position bottom-right --output final_demo.mp4

# 5. Optimize for web delivery
vg quality optimize --input final_demo.mp4 --output final_demo_web.mp4 --quality high
```

### 2. Multi-Part Tutorial Series

**Goal**: Create a 3-part tutorial with different voiceovers and seamless transitions.

```bash
# Part 1: Introduction
vg record --url "https://app.com/tutorial" --scenario simple-dashboard --run-id part1
vg audio tts --text "In this tutorial, we'll learn how to create stunning dashboards." --output part1_audio.mp3
vg compose sync --video videos/runs/part1/demo.mp4 --audio part1_audio.mp3 --output tutorial_part1.mp4

# Part 2: Advanced Features
vg record --url "https://app.com/advanced" --scenario ai-agent --run-id part2
vg audio tts --text "Now let's explore the advanced analytics features." --output part2_audio.mp3
vg compose sync --video videos/runs/part2/demo.mp4 --audio part2_audio.mp3 --output tutorial_part2.mp4

# Part 3: Best Practices
vg record --url "https://app.com/best-practices" --scenario simple-dashboard --run-id part3
vg audio tts --text "Finally, here are some best practices for dashboard design." --output part3_audio.mp3
vg compose sync --video videos/runs/part3/demo.mp4 --audio part3_audio.mp3 --output tutorial_part3.mp4

# Combine all parts
vg edit concat --videos "tutorial_part1.mp4,tutorial_part2.mp4,tutorial_part3.mp4" --output complete_tutorial.mp4
```

### 3. Social Media Content Creation

**Goal**: Create short, engaging clips for social media from longer recordings.

```bash
# Start with a long demo recording
vg record --url "https://app.com/features" --scenario ai-agent --run-id long_demo

# Extract the most interesting 15-second segment
vg edit trim --video videos/runs/long_demo/demo.mp4 --start 45 --end 60 --output highlight_clip.mp4

# Add energetic voiceover
vg audio tts --text "Check out this amazing feature!" --voice alloy --output hype_audio.mp3

# Make it faster and more engaging
vg edit speed --video highlight_clip.mp4 --factor 1.2 --output faster_clip.mp4

# Combine audio and video
vg compose sync --video faster_clip.mp4 --audio hype_audio.mp3 --output social_clip.mp4

# Optimize for social media (smaller file size)
vg quality optimize --input social_clip.mp4 --output social_clip_final.mp4 --target-size 8
```

## 🎨 Advanced Editing Examples

### Video Editing Pipeline
```bash
# Original long recording
vg record --url "https://app.com/workflow" --scenario ai-agent --run-id raw_workflow

# Trim out the boring parts
vg edit trim --video videos/runs/raw_workflow/demo.mp4 --start 10 --end 180 --output trimmed.mp4

# Speed up slow sections
vg edit speed --video trimmed.mp4 --factor 1.5 --range 30-60 --output sped_up.mp4

# Cut out any remaining pauses
vg edit cut --video sped_up.mp4 --cuts "90-95,120-125" --output clean.mp4

# Add smooth transitions between sections
vg quality optimize --input clean.mp4 --output final.mp4 --quality high
```

### Batch Audio Generation
```bash
# Create a segments.json file
cat > segments.json << 'EOF'
[
  {"id": "intro", "text": "Welcome to our platform"},
  {"id": "features", "text": "Here are the key features"},
  {"id": "demo", "text": "Watch this live demo"},
  {"id": "conclusion", "text": "Thanks for watching"}
]
EOF

# Generate all voiceovers at once
vg audio batch --segments segments.json --output-dir ./voiceovers --voice alloy

# Check what was created
vg list --type audio --recent 10
```

## 🎭 Talking Head Productions

### Agentic Approach: User Asks, AI Figures Out

User says: *"Add a talking head in the bottom right during the intro"*

AI does:
```bash
# Option A: One-step convenience (recommended)
vg talking-head create --text "Welcome to Improvado..." -o th_intro.mp4
# Returns: {"video": "th_intro.mp4", "audio": "th_intro.mp3", "duration_s": 4.2}

# Option B: Two-step (more control)
vg audio tts --text "Welcome to Improvado..." -o intro.mp3
# Returns: duration: 4.2s
vg talking-head generate --audio intro.mp3 -o th_intro.mp4

# Get marker time from timeline.md (e.g., t_page_loaded: 33.6s)
# Apply any time adjustments from trim/speed-gaps

# Overlay at calculated time
vg talking-head overlay --video final.mp4 --overlay th_intro.mp4:25.1 --position bottom-right -o with_th.mp4
```

---

### Overlay: Picture-in-Picture

Talking head appears in corner while main video plays.

```bash
# Single overlay
vg talking-head overlay --video v.mp4 --overlay th.mp4:33.6 --position bottom-right -o out.mp4

# Multiple overlays at different times
vg talking-head overlay --video v.mp4 \
  --overlay th_intro.mp4:10.2 \
  --overlay th_reveal.mp4:98.5 \
  --position bottom-right -o out.mp4
```

**Positions:** `bottom-right`, `bottom-left`, `top-right`, `top-left`

---

### Full-Screen Segment: Insert Between Scenes

User says: *"Insert a presenter segment between the typing and results"*

AI does:
```bash
# 1. Create talking head from text (TTS + generate in one step)
vg talking-head create --text "Now let's see the results..." -o th_transition.mp4
# Returns: {"video": "th_transition.mp4", "duration_s": 3.5}

# 2. Find the split point from timeline (e.g., t_agent_done: 98.5s)

# 3. Split the video
vg edit trim --video v.mp4 --end 98.5 -o before.mp4
vg edit trim --video v.mp4 --start 98.5 -o after.mp4

# 4. Join with talking head in the middle
vg edit concat --videos "before.mp4,th_transition.mp4,after.mp4" -o final.mp4

# 5. IMPORTANT: Recalculate any subsequent audio placements
#    Everything after 98.5s shifts by +3.5s (the insert duration)
```

---

### Complete Example: Demo with Intro and Reveal Talking Heads

```bash
# === SETUP ===
# Video: demo.mp4 (120s)
# Timeline: t_page_loaded: 8.2s, t_agent_done: 85.3s
# After trim -8s and speed-gaps: t_page_loaded: 0.2s, t_agent_done: 42.1s

# === CREATE TALKING HEADS (TTS + generate in one step) ===
vg talking-head create --text "Welcome to our AI platform. Watch how easy it is." -o th_intro.mp4
# Returns: {"duration_s": 4.8}

vg talking-head create --text "And here's your dashboard, ready to use." -o th_reveal.mp4
# Returns: {"duration_s": 3.2}

# === COMPOSE AUDIO ===
vg compose place --video fast.mp4 \
  --audio th_intro.mp3:0.2 \
  --audio th_reveal.mp3:42.1 \
  -o with_audio.mp4

# === ADD TALKING HEAD OVERLAYS ===
vg talking-head overlay --video with_audio.mp4 \
  --overlay th_intro.mp4:0.2 \
  --overlay th_reveal.mp4:42.1 \
  --position bottom-right \
  -o final.mp4
```

---

### Request File: `## Talking Heads` Section

For requests with custom TH text (separate from voiceover), use the `## Talking Heads` section:

```markdown
## Talking Heads (Optional)

1. **th_intro** (at: 0): "Hi! I'm your AI guide."
2. **th_processing** (at: t_processing1_started + 5s): "The AI is analyzing..."
3. **th_outro** (at: end): "That's all! Try it yourself."
```

AI interprets timing hints:
- `at: 0` → Fullscreen intro (prepend to video)
- `at: t_marker` → Overlay at marker time
- `at: t_marker + 5s` → Overlay 5s after marker
- `at: end` → Fullscreen outro (append to video)

---

### Presenter with Multiple Segments (Legacy)
```bash
# Generate multiple voiceover segments
vg audio tts --text "Hello and welcome!" --output segment1.mp3
vg audio tts --text "Let me show you around." --output segment2.mp3
vg audio tts --text "Here's how it works." --output segment3.mp3

# Create talking head videos for each
vg talking-head generate --audio segment1.mp3 --output presenter1.mp4
vg talking-head generate --audio segment2.mp3 --output presenter2.mp4
vg talking-head generate --audio segment3.mp3 --output presenter3.mp4

# Composite onto main video at different times
vg talking-head composite --video main.mp4 --talking-head presenter1.mp4 --position bottom-right --start-time 0 --output step1.mp4
vg talking-head composite --video step1.mp4 --talking-head presenter2.mp4 --position bottom-right --start-time 15 --output step2.mp4
vg talking-head composite --video step2.mp4 --talking-head presenter3.mp4 --position bottom-right --start-time 45 --output final.mp4
```

### Character Customization
```bash
# Use a custom character image
vg talking-head generate --audio voiceover.mp3 --character ./my_character.png --output custom_presenter.mp4

# Try different models
vg talking-head generate --audio voiceover.mp3 --model sadtalker --output sadtalker_version.mp4
vg talking-head generate --audio voiceover.mp3 --model omnihuman --output omnihuman_version.mp4
```

## 📊 Quality and Optimization

### Comprehensive Quality Pipeline
```bash
# Validate source files
vg quality validate --file raw_demo.mp4
vg quality validate --file voiceover.mp3

# Analyze quality and sync
vg quality analyze --video raw_demo.mp4 --audio voiceover.mp3

# Optimize for different platforms
vg quality optimize --input demo.mp4 --output demo_web.mp4 --quality high
vg quality optimize --input demo.mp4 --output demo_mobile.mp4 --target-size 10 --quality medium
vg quality optimize --input demo.mp4 --output demo_social.mp4 --target-size 8 --quality low
```

### Cost-Aware Production
```bash
# Estimate costs before starting
vg cost estimate --tts-text "This is a long script that will cost money..." --talking-head-model omnihuman

# Check current spending
vg cost summary
vg cost history --days 30

# Set budget limits
vg cost budget --limit 10.00  # Stop if we exceed $10

# Monitor costs during production
vg cost summary  # Check after each expensive operation
```

## 🔧 Maintenance and Troubleshooting

### System Health Checks
```bash
# Check system status
vg status

# View cache usage
vg cache status

# Clean up old files
vg cleanup --older-than 30 --dry-run  # See what would be deleted
vg cleanup --older-than 30             # Actually delete

# Clear cache selectively
vg cache clear --type tts --older-than 48
```

### Troubleshooting Common Issues
```bash
# Check file information
vg info --file problematic_file.mp4

# Validate file integrity
vg quality validate --file suspicious_file.mp4

# List recent assets
vg list --recent 5
vg list --type video
```

## 🎯 Specialized Workflows

### API Documentation Videos
```bash
# Record API interaction
vg record --url "https://api-docs.example.com/interactive" --scenario simple-dashboard

# Generate technical narration
vg audio tts --text "The API accepts JSON payloads with these parameters..." --voice echo --output api_narration.mp3

# Add developer-focused presenter
vg talking-head generate --audio api_narration.mp3 --character ./developer_avatar.png --output dev_presenter.mp4

# Final composition
vg compose sync --video api_demo.mp4 --audio api_narration.mp3 --output api_demo_audio.mp4
vg talking-head composite --video api_demo_audio.mp4 --talking-head dev_presenter.mp4 --position bottom-left --output api_tutorial.mp4
```

### Sales Demo with Multiple Angles
```bash
# Record from different user perspectives
vg record --url "https://app.com" --scenario simple-dashboard --run-id buyer_view
vg record --url "https://app.com/admin" --scenario ai-agent --run-id admin_view

# Create buyer-focused narration
vg audio tts --text "See how easy it is to use..." --output buyer_narration.mp3

# Create admin-focused narration
vg audio tts --text "Powerful admin controls let you..." --output admin_narration.mp3

# Combine perspectives
vg edit concat --videos "videos/runs/buyer_view/demo.mp4,videos/runs/admin_view/demo.mp4" --output combined_demo.mp4
vg compose sync --video combined_demo.mp4 --audio buyer_narration.mp3 --output sales_demo.mp4
```

These examples demonstrate the full range of capabilities available through the `vg` CLI. Claude can compose these tools to fulfill any video generation request, from simple recordings to complex multi-step productions.