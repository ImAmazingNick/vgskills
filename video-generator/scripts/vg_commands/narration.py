"""
vg narration commands

Narration template operations and batch generation.
"""

import argparse
import json
from pathlib import Path
from vg_narration_templates import list_templates, render_template, save_template, load_template


def register(subparsers):
    """Register narration commands."""
    narration_parser = subparsers.add_parser('narration', help='Narration template operations')
    narration_sub = narration_parser.add_subparsers(dest='narration_command')

    # vg narration template
    template_parser = narration_sub.add_parser('template', help='Template management')
    template_sub = template_parser.add_subparsers(dest='template_command')

    # vg narration template list
    list_parser = template_sub.add_parser('list', help='List narration templates')
    list_parser.set_defaults(func=cmd_template_list)

    # vg narration template render
    render_parser = template_sub.add_parser('render', help='Render a narration template')
    render_parser.add_argument('--template', required=True, help='Template ID')
    render_parser.add_argument('--overrides', help='JSON string or file path with overrides')
    render_parser.add_argument('--output', '-o', help='Output JSON file path')
    render_parser.set_defaults(func=cmd_template_render)

    # vg narration template save
    save_parser = template_sub.add_parser('save', help='Save a custom narration template')
    save_parser.add_argument('--file', required=True, help='Template JSON file')
    save_parser.add_argument('--id', help='Override template id')
    save_parser.add_argument('--overwrite', action='store_true', help='Overwrite if template exists')
    save_parser.set_defaults(func=cmd_template_save)

    # vg narration batch
    batch_parser = narration_sub.add_parser('batch', help='Generate multiple narration configs')
    batch_parser.add_argument('--examples', required=True, help='Examples JSON file')
    batch_parser.add_argument('--output-dir', '-o', required=True, help='Output directory')
    batch_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing outputs')
    batch_parser.set_defaults(func=cmd_batch)


def _load_overrides(value: str) -> dict:
    if not value:
        return {}
    candidate = Path(value)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(value)


def cmd_template_list(args) -> dict:
    return {"success": True, "templates": list_templates()}


def cmd_template_render(args) -> dict:
    try:
        overrides = _load_overrides(args.overrides) if args.overrides else {}
        segments, conditional_segments, filler_segments = render_template(args.template, overrides)
        template = load_template(args.template)

        output = {
            "success": True,
            "template_id": template.id,
            "video_type": template.video_type,
            "segments": segments,
            "conditional_segments": conditional_segments,
            "filler_segments": filler_segments,
            "workflow_markers": template.workflow_markers
        }

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
            output["output_path"] = str(output_path)

        return output
    except Exception as e:
        return {"success": False, "error": str(e), "code": "NARRATION_ERROR"}


def cmd_template_save(args) -> dict:
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        path = save_template(data, template_id=args.id, overwrite=args.overwrite)
        return {"success": True, "template_path": str(path)}
    except Exception as e:
        return {"success": False, "error": str(e), "code": "NARRATION_ERROR"}


def cmd_batch(args) -> dict:
    try:
        examples_data = json.loads(Path(args.examples).read_text(encoding="utf-8"))
        examples = examples_data.get("examples", [])
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for idx, example in enumerate(examples, 1):
            template_id = example.get("template") or example.get("template_id")
            if not template_id:
                video_type = example.get("video_type")
                if video_type:
                    template_id = f"{video_type}_default" if video_type != "ai_agent" else "ai_agent_default"

            if not template_id:
                results.append({"index": idx, "success": False, "error": "template not specified"})
                continue

            overrides = example.get("overrides", {}) or example.get("customizations", {})
            segments, conditional_segments, filler_segments = render_template(template_id, overrides)
            template = load_template(template_id)

            payload = {
                "template_id": template_id,
                "video_type": template.video_type,
                "segments": segments,
                "conditional_segments": conditional_segments,
                "filler_segments": filler_segments,
                "workflow_markers": template.workflow_markers
            }

            out_name = example.get("output_name") or f"narration_{template_id}_{idx}.json"
            out_path = output_dir / out_name
            if out_path.exists() and not args.overwrite:
                results.append({
                    "index": idx,
                    "success": False,
                    "error": f"Output exists: {out_path}"
                })
                continue

            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            results.append({
                "index": idx,
                "success": True,
                "output": str(out_path),
                "template_id": template_id
            })

        return {
            "success": True,
            "total": len(examples),
            "generated": len([r for r in results if r.get("success")]),
            "results": results
        }
    except Exception as e:
        return {"success": False, "error": str(e), "code": "NARRATION_ERROR"}
