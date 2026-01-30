# Video Request: [Your Platform Name]

> Copy this template and fill in your details.
> The AI agent reads this file and executes everything autonomously.

---

## Platform

**Name:** [Platform name]  
**Product:** [Feature/product being demoed]  
**URL:** [Starting URL]

---

## Authentication

**Method:** [none | Session Cookie | Login Form]

If Session Cookie:
- **Cookie Name:** [cookie name]
- **Cookie Value:** Use environment variable `[ENV_VAR_NAME]`
- **Cookie Domain:** [.example.com]

If Login Form:
- **Username:** Use environment variable `[ENV_VAR_NAME]`
- **Password:** Use environment variable `[ENV_VAR_NAME]`

If None:
- No authentication required

---

## Browser Settings

**Viewport:** [1920 x 1080 | 1280 x 720 | custom]  
**Headless:** [yes | no]  
**Slow Motion:** [0 | 500ms | custom]  
**Demo Effects:** [yes | no]

---

## Goal

[Describe in plain English what the demo should show. What is the user journey? What is the key value being demonstrated?]

**Key moments to capture:**
1. [First key moment]
2. [Second key moment]
3. [...]

---

## Scenario Flow

### Step 1: [Name]
[Describe what should happen]

### Step 2: [Name]
[Describe what should happen]

### Step 3: [Name]
[Describe what should happen]

[Add more steps as needed]

---

## Actions (Optional)

Use this table to drive custom navigation flows with precise timing and markers.

<!-- ACTIONS_START -->
| Marker | Action | Selector | Value | Wait |
|--------|--------|----------|-------|------|
| t_page_network_idle | wait_network_idle |  |  | 90000 |
| t_page_ready | wait_visible | [role="main"], main |  | 30000 |
| t_prompt1_focus | click | textarea |  |  |
| t_prompt1_typed | type | textarea | Create cross-channel marketing analytics dashboard |  |
| t_prompt1_submitted | press |  | Enter |  |
| t_processing1_started | wait_text |  | Thinking |  |
| t_agent_done_1 | wait_agent_done |  |  |  |
| t_scroll_start | scroll |  | 800 |  |
<!-- ACTIONS_END -->

**Actions supported:**
- Navigation: `click`, `focus`
- Input: `fill`, `type`, `press`
- Smart waiting: `wait_network_idle`, `wait_visible`, `wait_selector`, `wait_text`
- Special: `wait_agent_done`, `wait_followup_input`, `scroll`, `screenshot`, `mark`
- Fallback: `wait` (fixed delay - use sparingly)

**Smart Waiting Best Practices:**
1. Always start with `wait_network_idle` after page loads
2. Use `wait_visible` to ensure elements are rendered before interactions
3. Avoid fixed `wait` times - they don't adapt to actual page state
4. Add `screenshot` actions after key steps for debugging

If you omit Actions, the recorder can run in **auto** mode using prompts
extracted from Scenario Flow (quoted text) for best-effort navigation.

---

## Narrative (Voiceover)

[Describe the voice style: professional, casual, enthusiastic, etc.]

### Narration Template (Optional)

<!-- NARRATION_TEMPLATE_START -->
Template: ai_agent_default
prompt_text: Create cross-channel marketing analytics dashboard
followup_prompt: Add 3 more KPI widgets at bottom of the dashboard
<!-- NARRATION_TEMPLATE_END -->

<!-- VOICEOVER_SEGMENTS_START -->
| Segment | Anchor Marker | Offset | Text |
|---------|---------------|--------|------|
| intro | t_page_loaded | 0.5s | [Your intro narration text] |
| prompt1 | t_prompt1_focus | 0.2s | [Narration when user starts typing first prompt] |
| processing1 | t_processing1_started | 2.0s | [Narration during first AI processing] |
| reveal1 | t_agent_done_1 | 0.5s | [Narration when result appears] |
| prompt2 | t_prompt2_focus | 0.3s | [Narration for follow-up prompt] |
| processing2 | t_processing2_started | 1.5s | [Narration during second processing] |
| wrap | t_scroll_start | 0.3s | [Final wrap-up narration] |
<!-- VOICEOVER_SEGMENTS_END -->

---

## Conditional Narration (Optional)

Use this section to add narration only when processing takes longer than expected.

<!-- CONDITIONAL_SEGMENTS_START -->
| Segment | Start Marker | End Marker | Min Duration | Offset | Text | Repeatable | Max Repeats | Repeat Interval |
|---------|--------------|------------|--------------|--------|------|------------|-------------|-----------------|
| processing1_filler | t_processing1_started | t_agent_done_1 | 8s | 4s | The agent is analyzing your connected data sources and building the perfect dashboard layout. | yes | 2 | 6s |
| processing2_filler | t_processing2_started | t_agent_done_2 | 6s | 3s | Adding those KPIs seamlessly while preserving all your existing work. | no | 1 | 0s |
<!-- CONDITIONAL_SEGMENTS_END -->

### Available Anchor Markers

| Marker | Description |
|--------|-------------|
| t_page_loaded | Page finished loading |
| t_prompt1_focus | User focused on first input |
| t_prompt1_typed | First prompt fully typed |
| t_prompt1_submitted | First prompt submitted |
| t_processing1_started | AI started processing first request |
| t_agent_done_1 | First result ready |
| t_prompt2_focus | User focused on follow-up input |
| t_prompt2_typed | Follow-up prompt fully typed |
| t_prompt2_submitted | Follow-up prompt submitted |
| t_processing2_started | AI started processing follow-up |
| t_agent_done_2 | Follow-up result ready |
| t_scroll_start | Started scrolling to show results |
| t_scroll_end | Finished scrolling |

**Note:** Offset is the delay (in seconds) after the anchor marker before narration starts.

---

## Options

### Browser Driver
- **Driver:** current
  <!-- Use "current" for Playwright CSS selectors, "agent-browser" for ref-based selection -->

### Voiceover
- **Enable:** [yes | no]
- **Voice Provider:** [ElevenLabs | provided audio files]
- **Voice Style:** [Description]

### Talking Head
- **Enable:** [yes | no]
- **Model:** [OmniHuman | SadTalker]
- **Segments:** [Which narrative segments should show talking head]
- **Size:** [300px | custom]
- **Position:** [bottom-right | bottom-left | top-right | top-left]

### Editing
- **Trim Start:** [seconds to remove from beginning]
- **Trim End:** [seconds to remove from end]
- **Speed Up:** [describe sections to speed up, e.g., "processing at 3x"]
- **Cut:** [describe sections to remove entirely]

### Slides
- **Enable:** [yes | no]
- **Title Slide:** [yes | no] - Text: "[Title text]"
- **End Slide:** [yes | no] - Text: "[End text]"

---

## Output

**Filename Pattern:** [your_demo_name]_YYYYMMDD_HHMMSS  
**Format:** MP4  
**Resolution:** [1920x1080 | 1280x720]  
**Target Duration:** [target length]

---

## Success Criteria

The video is successful if:
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

---

## Notes for AI Agent

[Any special instructions, known issues, or tips for the AI agent]

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | [date] | Initial version |
