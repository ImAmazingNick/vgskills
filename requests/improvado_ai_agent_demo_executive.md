# Video Request: Improvado AI Agent Executive Dashboard Demo

> Executive-focused demo showing how the AI agent creates a comprehensive marketing dashboard for leadership teams.
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

Record a demo showing how the Improvado AI Agent creates an executive marketing dashboard with campaign and creative analytics from a simple text prompt, then enhances it with key performance indicators at the top — perfect for leadership teams needing comprehensive marketing insights.

**Key moments to capture:**
1. Page loads with the AI agent interface
2. User types the first prompt to create an executive dashboard
3. AI processes and generates the dashboard (this takes 30-90 seconds)
4. Dashboard appears on the right side of the screen
5. User types a follow-up prompt to add KPI widgets at the top
6. AI updates the dashboard with new KPIs positioned at the top
7. Final scroll to show the complete executive dashboard

---

## Scenario Flow

### Step 1: Open and Wait
- Navigate to the AI Agent URL
- Wait for the page to fully load
- The interface shows a chat/prompt area on the left

### Step 2: First Prompt
- Find the main prompt input field (textarea for building dashboards)
- Type: **"Create executive marketing dashbord with campaign and creative analytics"**
- Type slowly (45ms per character) so viewers can read
- Submit the prompt (press Enter)

### Step 3: Wait for Dashboard Generation
- The AI agent will process the request
- A loading/thinking indicator will appear
- Wait until the dashboard appears on the right side of the screen
- This can take 30-90 seconds depending on data complexity

### Step 4: Follow-up Prompt  
- Find the follow-up prompt input (may have different placeholder like "Ask anything")
- Type: **"Add 4 simple KPI widgets at top of dashboard"**
- Type at 35ms per character
- Submit the prompt

### Step 5: Wait for Update
- Wait for the AI to finish adding the widgets
- Dashboard updates in real-time with KPIs positioned at the top

### Step 6: Show Final Result
- Scroll down the dashboard to reveal all widgets
- Pause briefly to let viewers see the complete executive result

---

## Narrative (Voiceover)

The voiceover should be professional, authoritative, and executive-focused. Voice: confident, clear, business-savvy.

<!-- VOICEOVER_SEGMENTS_START -->
| Segment | Anchor Marker | Offset | Text |
|---------|---------------|--------|------|
| intro | t_page_loaded | 0.5s | For executive teams needing comprehensive marketing insights, the AI agent connects to all your marketing platforms and builds executive dashboards instantly. |
| prompt1 | t_prompt1_focus | 0.2s | Watch how simple it is. Just describe what you need: 'Create executive marketing dashboard with campaign and creative analytics.' |
| processing1 | t_processing1_started | 2.0s | The agent analyzes your campaign data, creative performance, and marketing channels to build a comprehensive executive dashboard with all the key metrics. |
| reveal1 | t_agent_done_1 | 0.5s | Complete executive dashboard generated—campaign performance, creative analytics, and cross-channel insights all automatically visualized. |
| prompt2 | t_prompt2_focus | 0.3s | Now let's add key performance indicators for quick executive visibility. Simply request: 'Add 4 simple KPI widgets at top of dashboard.' |
| processing2 | t_processing2_started | 1.5s | The dashboard evolves in real-time, adding those critical KPIs right at the top where executives need them most. |
| wrap | t_scroll_start | 0.3s | Your executive team now has instant access to campaign ROI, creative performance metrics, and key business indicators—all from natural language requests. |
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
- **Voice Style:** Professional, authoritative, executive
- **Generate via:** TTS from narrative text above

### Talking Head
- **Enable:** yes
- **Model:** OmniHuman (high quality, realistic expressions)
- **Character:** Professional male presenter (reuse existing if available)
- **Segments:** processing1, processing2 (show during AI "thinking" time)
- **Size:** 300px
- **Position:** bottom-right
- **Reuse Policy:** Match by audio hash (if same audio exists, reuse the video)

### Editing
- **Trim Start:** 8 seconds (remove initial loading/blank screen)
- **Speed Up:** The long processing sections can be sped up 3x
- **Cut:** Remove any excessively long wait times (keep video under 2 minutes if possible)

### Slides
- **Enable:** no (not needed for this demo)

---

## Output

**Filename Pattern:** ai_agent_executive_demo_YYYYMMDD_HHMMSS  
**Format:** MP4 (H.264)  
**Resolution:** 1920x1080  
**Target Duration:** ~1.5 to 2 minutes after editing

---

## Success Criteria

The video is successful if:
- [ ] Executive dashboard is fully generated and visible
- [ ] Both prompts are shown being typed
- [ ] AI processing is captured (with talking head overlay)
- [ ] Final dashboard with top KPI widgets is shown
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

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-26 | Initial executive dashboard demo request |

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 49.14 |
| t_screenshot_initial_page | 50.68 |
| t_prompt1_focus | 51.82 |
| t_screenshot_prompt1_focus | 54.16 |
| t_prompt1_typed | 58.23 |
| t_prompt1_submitted | 60.45 |
| t_processing1_started | 60.46 |
| t_screenshot_processing1_started | 61.01 |
| t_agent_done_1 | 197.90 |
| t_screenshot_agent_done_1 | 201.05 |
| t_hold_done_1 | 206.05 |
| t_prompt2_focus | 207.08 |
| t_screenshot_prompt2_focus | 208.51 |
| t_prompt2_typed | 211.56 |
| t_prompt2_submitted | 213.59 |
| t_processing2_started | 213.59 |
| t_agent_done_2 | 278.69 |
| t_screenshot_followup_done | 280.77 |
| t_scroll_start | 280.77 |
| t_scroll_end | 288.29 |
| t_screenshot_scroll_start | 289.41 |
| t_recording_complete | 289.41 |
<!-- TIMELINE_MARKERS_END -->


<!-- RUN_RESULTS_START -->

# Run Report: unknown_20260129_005741

- Run directory: /Users/nick/virthrillove/videos/runs/unknown_20260129_005741
- Final video: /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_demo_executive.md
- Request file: product-demo-videos/requests/improvado_ai_agent_demo_executive.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 49.14 |
| t_screenshot_initial_page | 50.68 |
| t_prompt1_focus | 51.82 |
| t_screenshot_prompt1_focus | 54.16 |
| t_prompt1_typed | 58.23 |
| t_prompt1_submitted | 60.45 |
| t_processing1_started | 60.46 |
| t_screenshot_processing1_started | 61.01 |
| t_agent_done_1 | 197.90 |
| t_screenshot_agent_done_1 | 201.05 |
| t_hold_done_1 | 206.05 |
| t_prompt2_focus | 207.08 |
| t_screenshot_prompt2_focus | 208.51 |
| t_prompt2_typed | 211.56 |
| t_prompt2_submitted | 213.59 |
| t_processing2_started | 213.59 |
| t_agent_done_2 | 278.69 |
| t_screenshot_followup_done | 280.77 |
| t_scroll_start | 280.77 |
| t_scroll_end | 288.29 |
| t_screenshot_scroll_start | 289.41 |
| t_recording_complete | 289.41 |
<!-- TIMELINE_MARKERS_END -->
## Screenshots

- /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/raw/screenshots/agent_done_1_1769637697.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/raw/screenshots/followup_done_1769637778.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/raw/screenshots/initial_page_1769637548.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/raw/screenshots/processing1_started_1769637560.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/raw/screenshots/prompt1_focus_1769637551.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/raw/screenshots/prompt2_focus_1769637706.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_005741/raw/screenshots/scroll_complete_1769637788.png

## Issues

- Talking heads were not composited (missing placements).


<!-- RUN_RESULTS_END -->
