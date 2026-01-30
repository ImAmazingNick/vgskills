# Video Request: Improvado AI Agent Navigation Walkthrough

> Demo focused on guided navigation with narrated page descriptions.
> The AI agent reads this file and executes everything autonomously.

---

## Platform

**Name:** Improvado  
**Product:** AI Agent Workspace Navigation  
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

Create a narrated walkthrough where the user navigates the Dashboards, Chats, and Connections pages from the AI Agent start page. Each page should be clearly shown while voiceover explains what it is for.

**Key moments to capture:**
1. Start page loads
2. Dashboards page is opened and showcased
3. Chats page is opened and showcased
4. Connections page is opened and showcased
5. Final hold on Connections

---

## Scenario Flow

### Step 1: Open and Wait
- Navigate to the AI Agent URL
- Wait for the page to fully load

### Step 2: Dashboards
- Click **"Dashboards"** in the left navigation
- Pause to show the dashboards page content

### Step 3: Chats
- Click **"Chats"** in the left navigation
- Pause to show chat threads or assistant interface

### Step 4: Connections
- Click **"Connections"** in the left navigation
- Pause to show data source connections

---

## Actions (Optional)

Use this table to drive custom navigation flows with precise timing and markers.

<!-- ACTIONS_START -->
| Marker | Action | Selector | Value | Wait |
|--------|--------|----------|-------|------|
| t_page_wait | wait |  | 10s |  |
| t_page_loaded | wait_visible | button, a[href] |  | 120000 |
| t_verify_nav | wait_visible | text=Dashboards, text=Chats, text=Connections |  | 90000 |
| t_page_ready | screenshot |  |  |  |
| t_nav_dashboards_click | click | text=Dashboards |  |  |
| t_dashboards_content_wait | wait_visible | h1:has-text("Dashboards"), text="All your dashboards" |  | 15000 |
| t_dashboards_screenshot | screenshot |  |  |  |
| t_dashboards_view | mark |  |  |  |
| t_nav_chats_click | click | text=Chats |  |  |
| t_chats_content_wait | wait_visible | h1:has-text("Chats"), text="conversations" |  | 15000 |
| t_chats_screenshot | screenshot |  |  |  |
| t_chats_view | mark |  |  |  |
| t_nav_connections_click | click | text=Connections |  |  |
| t_connections_content_wait | wait_visible | h1:has-text("Connections"), text="data sources" |  | 15000 |
| t_connections_screenshot | screenshot |  |  |  |
| t_connections_view | mark |  |  |  |
<!-- ACTIONS_END -->

Actions supported: click, focus, fill, type, press, wait_selector, wait_visible, wait_text, wait_network_idle, wait_agent_done, wait_followup_input, scroll, screenshot, wait, mark.

**Smart waiting actions:**
- `wait_network_idle`: Wait for network activity to settle (recommended for page loads)
- `wait_visible`: Wait for element to be visible (better than fixed `wait`)
- `wait_selector`: Wait for element to exist in DOM
- `wait`: Fixed time delay (use sparingly)

---

## Narrative (Voiceover)

The voiceover should be clear, professional, and descriptive. Keep it concise and aligned to each page.

<!-- VOICEOVER_SEGMENTS_START -->
| Segment | Anchor Marker | Offset | Text |
|---------|---------------|--------|------|
| intro | t_page_loaded | 0.5s | Welcome to Improvado’s AI Agent workspace, where you can build insights, collaborate, and connect data—all in one place. |
| dashboards | t_dashboards_view | 0.3s | The Dashboards page is where your analytics live. Here you can explore performance views, edit widgets, and monitor KPIs at a glance. |
| chats | t_chats_view | 0.3s | Chats keep your AI conversations organized. Ask questions, refine requests, and track how each insight was generated. |
| connections | t_connections_view | 0.3s | Connections is where data sources come together—linking platforms like Google, LinkedIn, and Salesforce to power every dashboard. |
| wrap | t_connections_view | 3.0s | With dashboards, chats, and connections unified, the AI Agent becomes your command center for data-driven decisions. |
<!-- VOICEOVER_SEGMENTS_END -->

---

## Options

### Voiceover
- **Enable:** yes
- **Voice Provider:** ElevenLabs
- **Voice Style:** Professional, clear, neutral
- **Generate via:** TTS from narrative text above

### Talking Head
- **Enable:** no

### Editing
- **Trim Start:** 15
- **Speed Up:** none
- **Cut:** none

### Slides
- **Enable:** no

---

## Output

**Filename Pattern:** ai_agent_navigation_walkthrough_YYYYMMDD_HHMMSS  
**Format:** MP4 (H.264)  
**Resolution:** 1920x1080  
**Target Duration:** ~45 to 75 seconds

---

## Success Criteria

The video is successful if:
- [ ] Dashboards, Chats, and Connections pages are each shown clearly
- [ ] Voiceover describes each page accurately
- [ ] Navigation between pages is smooth
- [ ] Audio is synced to the visuals

---

## Notes for AI Agent

- Set `DTS_SESSIONID` to the provided session value before running.
- If left-nav labels are not visible, open the main menu and retry.
- If "Chats" or "Connections" labels differ, prefer closest visible match.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-28 | Initial navigation walkthrough request |


<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 17.31 |
| t_screenshot_initial_page | 16.29 |
| t_page_wait | 17.30 |
| t_verify_nav | 17.33 |
| t_page_ready | 17.94 |
| t_nav_dashboards_click | 19.04 |
| t_dashboards_content_wait | 19.33 |
| t_dashboards_screenshot | 20.23 |
| t_dashboards_view | 20.23 |
| t_nav_chats_click | 22.00 |
| t_chats_content_wait | 22.37 |
| t_chats_screenshot | 24.29 |
| t_chats_view | 24.29 |
| t_nav_connections_click | 26.57 |
| t_connections_content_wait | 56.37 |
| t_connections_screenshot | 57.91 |
| t_connections_view | 57.91 |
| t_recording_complete | 57.91 |
<!-- TIMELINE_MARKERS_END -->


<!-- RUN_RESULTS_START -->

# Run Report: improvado_20260128_212913

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_20260128_212913
- Final video: None
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_20260128_212913/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 10.14 |
| t_screenshot_initial_page | 9.14 |
| t_nav_dashboards_click | 11.20 |
| t_dashboards_wait | 12.21 |
| t_dashboards_view | 12.21 |
| t_nav_chats_click | 14.10 |
| t_chats_wait | 15.11 |
| t_chats_view | 15.11 |
| t_nav_connections_click | 17.90 |
| t_connections_wait | 18.90 |
| t_connections_view | 18.90 |
| t_recording_complete | 18.90 |


<!-- RUN_RESULTS_START -->

# Run Report: improvado_20260128_213640

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_20260128_213640
- Final video: /Users/nick/virthrillove/videos/runs/improvado_20260128_213640/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_20260128_213640/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 72.39 |
| t_screenshot_initial_page | 71.39 |
| t_nav_dashboards_click | 80.18 |
| t_dashboards_wait | 81.18 |
| t_dashboards_view | 81.18 |
| t_nav_chats_click | 82.23 |
| t_chats_wait | 83.23 |
| t_chats_view | 83.23 |
| t_nav_connections_click | 86.56 |
| t_connections_wait | 87.56 |
| t_connections_view | 87.56 |
| t_recording_complete | 87.56 |


<!-- RUN_RESULTS_START -->

# Run Report: improvado_20260128_215137

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_20260128_215137
- Final video: /Users/nick/virthrillove/videos/runs/improvado_20260128_215137/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_20260128_215137/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 83.74 |
| t_screenshot_initial_page | 68.71 |
| t_page_ready | 84.74 |
| t_nav_dashboards_click | 85.86 |
| t_dashboards_wait | 86.87 |
| t_dashboards_view | 86.87 |
| t_nav_chats_click | 87.91 |
| t_chats_wait | 88.91 |
| t_chats_view | 88.91 |
| t_nav_connections_click | 92.58 |
| t_connections_wait | 93.59 |
| t_connections_view | 93.59 |
| t_recording_complete | 93.59 |


<!-- RUN_RESULTS_START -->

# Run Report: improvado_20260128_220008

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_20260128_220008
- Final video: /Users/nick/virthrillove/videos/runs/improvado_20260128_220008/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_20260128_220008/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 37.46 |
| t_screenshot_initial_page | 39.42 |
| t_recording_complete | 39.42 |


<!-- RUN_RESULTS_START -->

# Run Report: improvado_20260128_220725

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_20260128_220725
- Final video: /Users/nick/virthrillove/videos/runs/improvado_20260128_220725/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_20260128_220725/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 23.83 |
| t_screenshot_initial_page | 24.72 |
| t_recording_complete | 24.72 |


<!-- RUN_RESULTS_START -->

# Run Report: improvado_20260128_221958

- Run directory: /Users/nick/virthrillove/videos/runs/improvado_20260128_221958
- Final video: /Users/nick/virthrillove/videos/runs/improvado_20260128_221958/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/improvado_20260128_221958/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 36.57 |
| t_screenshot_initial_page | 37.55 |
| t_recording_complete | 37.55 |


<!-- RUN_RESULTS_START -->

# Run Report: unknown_20260128_231433

- Run directory: /Users/nick/virthrillove/videos/runs/unknown_20260128_231433
- Final video: /Users/nick/virthrillove/videos/runs/unknown_20260128_231433/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/unknown_20260128_231433/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 4.15 |
| t_screenshot_initial_page | 4.41 |
| t_recording_complete | 4.41 |


<!-- RUN_RESULTS_START -->

# Run Report: unknown_20260128_232024

- Run directory: /Users/nick/virthrillove/videos/runs/unknown_20260128_232024
- Final video: /Users/nick/virthrillove/videos/runs/unknown_20260128_232024/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/unknown_20260128_232024/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 4.03 |
| t_screenshot_initial_page | 4.26 |
| t_recording_complete | 4.26 |


<!-- RUN_RESULTS_START -->

# Run Report: unknown_20260128_232657

- Run directory: /Users/nick/virthrillove/videos/runs/unknown_20260128_232657
- Final video: /Users/nick/virthrillove/videos/runs/unknown_20260128_232657/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/unknown_20260128_232657/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 24.98 |
| t_screenshot_initial_page | 25.62 |
| t_recording_complete | 25.63 |


<!-- RUN_RESULTS_START -->

# Run Report: unknown_20260128_234854

- Run directory: /Users/nick/virthrillove/videos/runs/unknown_20260128_234854
- Final video: /Users/nick/virthrillove/videos/runs/unknown_20260128_234854/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/unknown_20260128_234854/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 86.15 |
| t_screenshot_initial_page | 83.32 |
| t_page_wait | 84.32 |
| t_verify_nav | 92.52 |
| t_page_ready | 107.11 |
| t_nav_dashboards_click | 108.21 |
| t_dashboards_wait | 109.22 |
| t_dashboards_screenshot | 109.83 |
| t_dashboards_view | 109.83 |
| t_nav_chats_click | 111.37 |
| t_chats_wait | 112.37 |
| t_chats_screenshot | 112.97 |
| t_chats_view | 112.97 |
| t_nav_connections_click | 118.10 |
| t_connections_wait | 119.10 |
| t_connections_screenshot | 149.11 |
| t_connections_view | 149.11 |
| t_recording_complete | 149.11 |


<!-- RUN_RESULTS_START -->

# Run Report: unknown_20260129_002634

- Run directory: /Users/nick/virthrillove/videos/runs/unknown_20260129_002634
- Final video: /Users/nick/virthrillove/videos/runs/unknown_20260129_002634/final.mp4
- Video (converted): /Users/nick/virthrillove/videos/runs/unknown_20260129_002634/demo.mp4
- Timeline source: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md
- Request file: product-demo-videos/requests/improvado_ai_agent_navigation_voiceover.md

## Timeline Markers

<!-- TIMELINE_MARKERS_START -->
| Marker | Time (s) |
|--------|----------|
| t_start_recording | 0.00 |
| t_page_loaded | 17.31 |
| t_screenshot_initial_page | 16.29 |
| t_page_wait | 17.30 |
| t_verify_nav | 17.33 |
| t_page_ready | 17.94 |
| t_nav_dashboards_click | 19.04 |
| t_dashboards_content_wait | 19.33 |
| t_dashboards_screenshot | 20.23 |
| t_dashboards_view | 20.23 |
| t_nav_chats_click | 22.00 |
| t_chats_content_wait | 22.37 |
| t_chats_screenshot | 24.29 |
| t_chats_view | 24.29 |
| t_nav_connections_click | 26.57 |
| t_connections_content_wait | 56.37 |
| t_connections_screenshot | 57.91 |
| t_connections_view | 57.91 |
| t_recording_complete | 57.91 |
<!-- TIMELINE_MARKERS_END -->
## Screenshots

- /Users/nick/virthrillove/videos/runs/unknown_20260129_002634/raw/screenshots/initial_page_1769635613.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_002634/raw/screenshots/t_chats_screenshot_1769635620.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_002634/raw/screenshots/t_connections_screenshot_1769635654.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_002634/raw/screenshots/t_dashboards_screenshot_1769635617.png
- /Users/nick/virthrillove/videos/runs/unknown_20260129_002634/raw/screenshots/t_page_ready_1769635615.png

## Issues

- None detected.


<!-- RUN_RESULTS_END -->
