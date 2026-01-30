# Video Request: Improvado AI Agent Demo

> This is the reference example showing how to request a demo video.
> The AI agent reads this file and executes everything autonomously.

---

## Platform

**Name:** Improvado  
**Product:** AI Agent for Dashboard Creation  
**URL:** https://report.improvado.io/experimental/agent/new-agent/?workspace=121

---

## Authentication

**Method:** Session Cookie  
**Cookie Name:** dts_sessionid  
**Cookie Value:** Use environment variable `DTS_SESSIONID`  
**Cookie Domain:** .improvado.io  
**Cookie Path:** /  
**Secure:** yes

---

## Browser Settings

**Viewport:** 1920 x 1080 (Full HD)  
**Headless:** no (show browser window)  
**Slow Motion:** 500ms between actions  
**Demo Effects:** yes (cursor highlight, click ripples)

---

## Goal

Record a demo showing how the Improvado AI Agent creates a complete marketing analytics dashboard from a simple text prompt, then enhances it with additional KPI widgets — all without any manual configuration.

**Key moments to capture:**
1. Page loads with the AI agent interface
2. User selects Claude Opus 4.5 model from dropdown (if not already selected)
3. User types the first prompt to create a dashboard
4. AI processes and generates the dashboard (this takes 30-90 seconds)
5. Dashboard appears on the right side of the screen
6. User types a follow-up prompt to add more widgets
7. AI updates the dashboard with new KPIs
8. Final scroll to show the complete dashboard

---

## Scenario Flow

### Step 1: Open and Wait
- Navigate to the AI Agent URL
- Wait for the page to fully load
- The interface shows a chat/prompt area on the left

### Step 2: Select Claude Opus Model
- Look at the model selector dropdown at the top of the page (shows current model like "Claude Sonnet 4.5")
- If the current model is NOT Claude Opus 4.5:
  - Click on the model dropdown to open it
  - Wait for dropdown menu to appear with model options
  - Click on "Claude Opus 4.5" option (marked as "Most capable, higher cost")
  - Wait for dropdown to close and model to be selected
- This ensures we're using the most capable model for the demo

### Step 3: First Prompt
- Find the main prompt input field (textarea for building dashboards)
- Type: **"Create cross-channel marketing analytics dashboard"**
- Type slowly (45ms per character) so viewers can read
- Submit the prompt (press Enter)

### Step 4: Wait for Dashboard Generation
- The AI agent will process the request
- A loading/thinking indicator will appear
- Wait until the dashboard appears on the right side of the screen
- This can take 30-90 seconds depending on data complexity

### Step 5: Follow-up Prompt  
- Find the follow-up prompt input (may have different placeholder like "Ask anything")
- Type: **"Add 3 more KPI widgets at bottom of the dashboard"**
- Type at 35ms per character
- Submit the prompt

### Step 6: Wait for Update
- Wait for the AI to finish adding the widgets
- Dashboard updates in real-time

### Step 7: Show Final Result
- Scroll down the dashboard to reveal all widgets
- Pause briefly to let viewers see the complete result

---

## Narrative (Voiceover)

The voiceover should be professional, enthusiastic but not over-the-top. Voice: warm, clear, modern.

<!-- VOICEOVER_SEGMENTS_START -->
| Segment | Anchor Marker | Offset | Text |
|---------|---------------|--------|------|
| intro | t_page_loaded | 0.5s | Connect any marketing or sales data — Google, LinkedIn, Salesforce, anything. Automatically pulled, cleaned, structured, instantly ready. |
| prompt1 | t_prompt1_focus | 0.2s | Here's where it gets magical. Open the AI agent and type exactly what you need: 'Create cross-channel marketing analytics dashboard.' |
| processing1 | t_processing1_started | 2.0s | While the agent is processing, it discovers your data and starts building a full editable dashboard—charts, KPIs, and insights—automatically. |
| reveal1 | t_agent_done_1 | 0.5s | Done. On the left, you have chat. On the right, your generated dashboard—ready to edit. |
| prompt2 | t_prompt2_focus | 0.3s | Just keep talking to the agent. Now add more: 'Add 3 more KPI widgets at bottom of the dashboard.' |
| processing2 | t_processing2_started | 1.5s | Watch the dashboard update live—no rebuilding, no starting over. Every prompt evolves the same dashboard in real time. |
| wrap | t_scroll_start | 0.3s | And you can still drill down, resize, and reorder widgets anytime. This is truly AI-native business intelligence. |
<!-- VOICEOVER_SEGMENTS_END -->

### Segment Details

**intro** — Right after page loads  
**prompt1** — When focusing on the first prompt input  
**processing1** — While AI is processing first request  
**reveal1** — When the dashboard appears  
**prompt2** — When focusing on the follow-up prompt  
**processing2** — While AI is adding KPI widgets  
**wrap** — When starting to scroll the final dashboard

---

## Options

### Voiceover
- **Enable:** yes
- **Voice Provider:** ElevenLabs
- **Voice Style:** Professional, warm, clear
- **Generate via:** TTS from narrative text above

### Talking Head
- **Enable:** yes
- **Model:** OmniHuman (high quality, realistic expressions)
- **Character:** Friendly female presenter (reuse existing if available)
- **Segments:** processing1, processing2 (show during AI "thinking" time)
- **Size:** 300px
- **Position:** bottom-right
- **Reuse Policy:** Match by audio hash (if same audio exists, reuse the video)

### Editing
- **Trim Start:** 8 seconds (remove initial loading/blank screen)
- **Speed Gaps:** yes (speeds up gaps BEFORE adding audio - preserves voiceover)
- **Speed Factor:** 3.0
- **Cut:** Remove any excessively long wait times (keep video under 2 minutes if possible)

### Slides
- **Enable:** no (not needed for this demo)

---

## Output

**Filename Pattern:** ai_agent_demo_YYYYMMDD_HHMMSS  
**Format:** MP4 (H.264)  
**Resolution:** 1920x1080  
**Target Duration:** ~1.5 to 2 minutes after editing

---

## Success Criteria

The video is successful if:
- [ ] Dashboard is fully generated and visible
- [ ] Both prompts are shown being typed
- [ ] AI processing is captured (with talking head overlay)
- [ ] Final dashboard with KPI widgets is shown
- [ ] Voiceover is synced with visual actions
- [ ] No audio overlaps
- [ ] Video is under 2 minutes after editing

---

## Notes for AI Agent

- If the page requires login, stop and report — the session cookie should handle auth
- If selectors are not found, try alternatives: look for textareas, buttons with "Submit" or arrow icons
- The "agent done" state can be detected by: dashboard container appearing, loading spinner disappearing, or network going idle
- Take screenshots at key moments for debugging
- Generate timeline markers for each segment anchor point
- **Model selector:** Look for a dropdown at the top of the page showing "Claude Sonnet 4.5" or similar text. Click it to open the dropdown, then select "Claude Opus 4.5" (the most capable option). The dropdown shows model descriptions like "Most capable, higher cost" next to Opus.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-26 | Initial reference example |
| 1.1 | 2026-01-29 | Added Step 2: Select Claude Opus model before first prompt |


<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 5.61 |
| t_prompt1_focus | 55.77 |
| t_agent_done_1 | 365.89 |
| t_agent_done_2 | 631.70 |
| t_recording_complete | 637.52 |
<!-- TIMELINE_MARKERS_END -->


<!-- RUN_RESULTS_START -->

# Run Report: improvado_agentic_final

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_agentic_final
- Final video: /Users/nick/virthrillove/videos/runs/improvado_agentic_final/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_agentic_final/raw/improvado_agentic_20260130_002910_20260130_002911.webm
- Timeline source: requests/improvado_ai_agent_demo.md
- Request file: requests/improvado_ai_agent_demo.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 33.11 |
| t_model_dropdown_click | 75.54 |
| t_model_selected | 97.78 |
| t_prompt1_focus | 107.15 |
| t_prompt1_typed | 116.40 |
| t_prompt1_submitted | 123.22 |
| t_processing1_started | 123.22 |
| t_agent_done_1 | 260.79 |
| t_prompt2_focus | 272.98 |
| t_prompt2_typed | 275.91 |
| t_prompt2_submitted | 283.01 |
| t_processing2_started | 283.01 |
| t_agent_done_2 | 347.75 |
| t_scroll_start | 352.76 |
| t_recording_complete | 369.99 |


<!-- RUN_RESULTS_START -->

# Run Report: test_speed_workflow

- Run directory: /Users/nick/virthrillove/videos/runs/test_speed_workflow
- Final video: /Users/nick/virthrillove/videos/runs/test_speed_workflow/final_fast.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/test_speed_workflow/raw/improvado_agentic_20260130_002910_20260130_002911.webm
- Timeline source: requests/improvado_ai_agent_demo.md
- Request file: requests/improvado_ai_agent_demo.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 33.11 |
| t_model_dropdown_click | 75.54 |
| t_model_selected | 97.78 |
| t_prompt1_focus | 107.15 |
| t_prompt1_typed | 116.40 |
| t_prompt1_submitted | 123.22 |
| t_processing1_started | 123.22 |
| t_agent_done_1 | 260.79 |
| t_prompt2_focus | 272.98 |
| t_prompt2_typed | 275.91 |
| t_prompt2_submitted | 283.01 |
| t_processing2_started | 283.01 |
| t_agent_done_2 | 347.75 |
| t_scroll_start | 352.76 |
| t_recording_complete | 369.99 |


<!-- RUN_RESULTS_START -->

# Run Report: improvado_final_test

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_final_test
- Final video: /Users/nick/virthrillove/videos/runs/improvado_final_test/final_fast.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_final_test/raw/improvado_test_130000_20260130_130001.webm
- Timeline source: requests/improvado_ai_agent_demo.md
- Request file: requests/improvado_ai_agent_demo.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 59.53 |
| t_prompt1_typed | 111.03 |
| t_agent_done_1 | 383.79 |
| t_agent_done_2 | 506.90 |
| t_recording_complete | 511.73 |


<!-- RUN_RESULTS_START -->

# Run Report: improvado_final_output

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_final_output
- Final video: /Users/nick/virthrillove/videos/runs/improvado_final_output/final_fast.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_final_output/raw/improvado_demo_final.webm
- Timeline source: requests/improvado_ai_agent_demo.md
- Request file: requests/improvado_ai_agent_demo.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 5.61 |
| t_prompt1_focus | 55.77 |
| t_agent_done_1 | 365.89 |
| t_agent_done_2 | 631.70 |
| t_recording_complete | 637.52 |
<!-- TIMELINE_MARKERS_END -->
## Screenshots

- None

## Issues

- Missing timeline markers: t_processing1_started, t_prompt2_focus, t_processing2_started, t_scroll_start
- Not all narration segments were placed.
- Talking heads were not composited (missing placements).


<!-- RUN_RESULTS_END -->
