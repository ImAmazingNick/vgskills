# Video Request: Improvado AI Agent Demo (Agentic)

> Agentic format — AI orchestrates recording and calculates placements

---

## Platform

**URL:** https://report.improvado.io/experimental/agent/new-agent/?workspace=121

---

## Authentication

**Method:** Session Cookie
**Cookie Name:** dts_sessionid
**Cookie Value:** Use environment variable `DTS_SESSIONID`
**Cookie Domain:** .improvado.io

---

## Goal

Record a demo showing the Improvado AI Agent creating a marketing analytics dashboard from a text prompt, then enhancing it with additional KPI widgets.

---

## Scenario Flow

1. Navigate to the AI Agent URL and wait for page to load
2. Check model selector — if not "Claude Opus 4.5", click dropdown and select it
3. Click on the main prompt textarea
4. Type: "Create cross-channel marketing analytics dashboard" (slowly, 45ms per char)
5. Press Enter to submit
6. Wait for AI to finish processing (dashboard appears on right side)
7. Click on the follow-up prompt input
8. Type: "Add 3 more KPI widgets at bottom of the dashboard" (35ms per char)
9. Press Enter to submit
10. Wait for AI to finish adding widgets
11. Scroll down to show complete dashboard

---

## Narration

1. **intro** (after page loads): "Connect any marketing or sales data — Google, LinkedIn, Salesforce, anything. Automatically pulled, cleaned, structured, instantly ready."

2. **prompt1** (when typing starts): "Here's where it gets magical. Open the AI agent and type exactly what you need: 'Create cross-channel marketing analytics dashboard.'"

3. **processing1** (during first AI work): "While the agent is processing, it discovers your data and starts building a full editable dashboard—charts, KPIs, and insights—automatically."

4. **reveal1** (when first result appears): "Done. On the left, you have chat. On the right, your generated dashboard—ready to edit."

5. **prompt2** (when typing follow-up): "Just keep talking to the agent. Now add more: 'Add 3 more KPI widgets at bottom of the dashboard.'"

6. **processing2** (during second AI work): "Watch the dashboard update live—no rebuilding, no starting over. Every prompt evolves the same dashboard in real time."

7. **wrap** (at the end): "And you can still drill down, resize, and reorder widgets anytime. This is truly AI-native business intelligence."

---

## Options

- **Voiceover:** yes
- **Talking head:** yes, bottom-right (during processing1, processing2)
- **Speed gaps:** yes, 3x
- **Trim start:** 8 seconds

---

## Notes

- Model selector: Look for dropdown at top showing current model. Click to open, select "Claude Opus 4.5"
- Agent done detection: dashboard container appears, loading spinner gone, or network idle
- Take screenshots at key moments for debugging
