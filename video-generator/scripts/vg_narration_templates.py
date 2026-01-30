"""
Narration templates for dynamic voiceover generation.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json


@dataclass
class NarrationTemplate:
    id: str
    name: str
    description: str
    video_type: str
    workflow_markers: List[str]
    segments: List[Dict[str, Any]]
    conditional_segments: List[Dict[str, Any]]
    filler_segments: List[Dict[str, Any]]
    customization_options: Dict[str, Any]


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "narration_templates"


def _ensure_templates_dir() -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _apply_overrides(text: str, overrides: Dict[str, Any]) -> str:
    if not overrides:
        return text
    for key, value in overrides.items():
        placeholder = "{" + str(key) + "}"
        text = text.replace(placeholder, str(value))
    return text


def _render_segments(
    segments: List[Dict[str, Any]],
    overrides: Dict[str, Any]
) -> List[Dict[str, Any]]:
    rendered = []
    for seg in segments:
        rendered.append({
            **seg,
            "text": _apply_overrides(seg.get("text", ""), overrides)
        })
    return rendered


def _builtin_templates() -> Dict[str, NarrationTemplate]:
    templates: Dict[str, NarrationTemplate] = {}

    templates["ai_agent_default"] = NarrationTemplate(
        id="ai_agent_default",
        name="AI Agent Dashboard Demo",
        description="Interactive AI agent creating marketing dashboards",
        video_type="ai_agent",
        workflow_markers=[
            "t_page_loaded", "t_prompt1_focus", "t_prompt1_submitted",
            "t_processing1_started", "t_agent_done_1", "t_prompt2_focus",
            "t_processing2_started", "t_agent_done_2", "t_scroll_start"
        ],
        segments=[
            {
                "id": "intro",
                "anchor": "t_page_loaded",
                "offset_s": 0.5,
                "text": "Connect any marketing or sales data — Google, LinkedIn, Salesforce, anything. Automatically pulled, cleaned, structured, instantly ready."
            },
            {
                "id": "prompt1",
                "anchor": "t_prompt1_focus",
                "offset_s": 0.2,
                "text": "Here's where it gets magical. Open the AI agent and type exactly what you need: '{prompt_text}'"
            },
            {
                "id": "processing1",
                "anchor": "t_processing1_started",
                "offset_s": 2.0,
                "text": "While the agent is processing, it discovers your data and starts building a full editable dashboard—charts, KPIs, and insights—automatically."
            },
            {
                "id": "reveal1",
                "anchor": "t_agent_done_1",
                "offset_s": 0.5,
                "text": "Done. On the left, you have chat. On the right, your generated dashboard—ready to edit."
            },
            {
                "id": "prompt2",
                "anchor": "t_prompt2_focus",
                "offset_s": 0.3,
                "text": "Just keep talking to the agent. Now add more: '{followup_prompt}'"
            },
            {
                "id": "processing2",
                "anchor": "t_processing2_started",
                "offset_s": 1.5,
                "text": "Watch the dashboard update live—no rebuilding, no starting over. Every prompt evolves the same dashboard in real time."
            },
            {
                "id": "wrap",
                "anchor": "t_scroll_start",
                "offset_s": 0.3,
                "text": "And you can still drill down, resize, and reorder widgets anytime. This is truly AI-native business intelligence."
            }
        ],
        conditional_segments=[
            {
                "id": "long_wait_filler",
                "condition": {
                    "type": "duration_between",
                    "start_marker": "t_processing1_started",
                    "end_marker": "t_agent_done_1",
                    "min_duration_s": 8.0
                },
                "anchor": "t_processing1_started",
                "offset_s": 4.0,
                "text": "The agent is analyzing your connected data sources and building the perfect dashboard layout.",
                "repeatable": True,
                "max_repeats": 2,
                "repeat_interval_s": 6.0
            }
        ],
        filler_segments=[
            {
                "id": "thinking_filler_1",
                "text": "The AI is working through your data connections and building insights.",
                "duration_s": 4.0
            },
            {
                "id": "thinking_filler_2",
                "text": "Processing your request and generating the dashboard components.",
                "duration_s": 3.5
            }
        ],
        customization_options={
            "prompt_text": "Create cross-channel marketing analytics dashboard",
            "followup_prompt": "Add 3 more KPI widgets at bottom of the dashboard"
        }
    )

    templates["file_upload_basic"] = NarrationTemplate(
        id="file_upload_basic",
        name="Basic File Upload Demo",
        description="Simple file upload with progress indication",
        video_type="file_upload",
        workflow_markers=[
            "t_page_loaded", "t_file_select", "t_upload_start", "t_upload_complete"
        ],
        segments=[
            {
                "id": "intro",
                "anchor": "t_page_loaded",
                "offset_s": 0.5,
                "text": "Let's upload your {file_type} file and see how quickly it gets processed."
            },
            {
                "id": "select",
                "anchor": "t_file_select",
                "offset_s": 0.2,
                "text": "Click to select your file, or drag and drop it into the upload area."
            },
            {
                "id": "uploading",
                "anchor": "t_upload_start",
                "offset_s": 0.3,
                "text": "Starting the upload now. You'll see the progress in real-time."
            },
            {
                "id": "complete",
                "anchor": "t_upload_complete",
                "offset_s": 0.5,
                "text": "Upload complete! Your file has been successfully processed and is ready to use."
            }
        ],
        conditional_segments=[],
        filler_segments=[
            {
                "id": "upload_progress_filler",
                "text": "Transferring your file securely to our servers.",
                "duration_s": 3.0
            }
        ],
        customization_options={
            "file_type": "document"
        }
    )

    return templates


def _load_custom_templates() -> Dict[str, NarrationTemplate]:
    _ensure_templates_dir()
    templates: Dict[str, NarrationTemplate] = {}

    for template_file in TEMPLATES_DIR.glob("*.json"):
        try:
            data = json.loads(template_file.read_text(encoding="utf-8"))
            template_id = data.get("id") or template_file.stem
            templates[template_id] = NarrationTemplate(
                id=template_id,
                name=data.get("name", template_id),
                description=data.get("description", ""),
                video_type=data.get("video_type", "custom"),
                workflow_markers=data.get("workflow_markers", []),
                segments=data.get("segments", []),
                conditional_segments=data.get("conditional_segments", []),
                filler_segments=data.get("filler_segments", []),
                customization_options=data.get("customization_options", {})
            )
        except Exception:
            continue

    return templates


def list_templates() -> List[Dict[str, Any]]:
    builtin = _builtin_templates()
    custom = _load_custom_templates()
    templates = {**builtin, **custom}

    items = []
    for t in templates.values():
        items.append({
            "id": t.id,
            "name": t.name,
            "video_type": t.video_type,
            "source": "custom" if t.id in custom else "builtin"
        })
    return items


def load_template(template_id: str) -> NarrationTemplate:
    templates = _builtin_templates()
    if template_id in templates:
        return templates[template_id]
    custom = _load_custom_templates()
    if template_id in custom:
        return custom[template_id]
    raise ValueError(f"Narration template not found: {template_id}")


def save_template(template: Dict[str, Any], template_id: Optional[str] = None, overwrite: bool = False) -> Path:
    _ensure_templates_dir()
    tid = template_id or template.get("id")
    if not tid:
        raise ValueError("Template id is required")

    template_path = TEMPLATES_DIR / f"{tid}.json"
    if template_path.exists() and not overwrite:
        raise ValueError(f"Template already exists: {template_path}")

    data = {
        "id": tid,
        "name": template.get("name", tid),
        "description": template.get("description", ""),
        "video_type": template.get("video_type", "custom"),
        "workflow_markers": template.get("workflow_markers", []),
        "segments": template.get("segments", []),
        "conditional_segments": template.get("conditional_segments", []),
        "filler_segments": template.get("filler_segments", []),
        "customization_options": template.get("customization_options", {})
    }

    template_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return template_path


def render_template(
    template_id: str,
    overrides: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    template = load_template(template_id)
    merged_overrides = {**template.customization_options, **(overrides or {})}

    segments = _render_segments(template.segments, merged_overrides)
    conditional_segments = _render_segments(template.conditional_segments, merged_overrides)

    return segments, conditional_segments, template.filler_segments
