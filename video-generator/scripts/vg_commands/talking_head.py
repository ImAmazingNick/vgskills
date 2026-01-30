"""
vg talking-head commands

Talking head generation and composition.

AGENTIC DESIGN:
- `overlay`: DUMB executor - AI provides exact times, tool just overlays videos
- `composite`: Legacy single-overlay command (backward compatible)
"""

import argparse
from pathlib import Path
from vg_talking_head import generate_character, generate_talking_head, composite_talking_head
from vg_common import validate_env_for_command

def register(subparsers):
    """Register talking-head commands."""
    th_parser = subparsers.add_parser('talking-head', help='Talking head operations')
    th_sub = th_parser.add_subparsers(dest='th_command')

    # vg talking-head generate
    gen_parser = th_sub.add_parser('generate', help='Generate talking head video from audio')
    gen_parser.add_argument('--audio', required=True, help='Audio file path')
    gen_parser.add_argument('--output', '-o', required=True, help='Output video path')
    gen_parser.add_argument('--character', help='Character image path (auto-generated if not provided)')
    gen_parser.add_argument('--model', default='omnihuman', choices=['omnihuman', 'sadtalker'], help='Model to use')
    gen_parser.set_defaults(func=cmd_generate)

    # vg talking-head overlay - AGENTIC: AI provides exact times for multiple overlays
    overlay_parser = th_sub.add_parser('overlay', help='Overlay talking heads at AI-specified times (agentic)')
    overlay_parser.add_argument('--video', required=True, help='Main video file path')
    overlay_parser.add_argument('--overlay', action='append', required=True,
                               help='Overlay placement: file.mp4:start_time (can specify multiple)')
    overlay_parser.add_argument('--output', '-o', required=True, help='Output video path')
    overlay_parser.add_argument('--position', default='bottom-right',
                               choices=['top-left', 'top-right', 'bottom-left', 'bottom-right'],
                               help='Overlay position')
    overlay_parser.add_argument('--size', type=int, default=280, help='Overlay size in pixels')
    overlay_parser.set_defaults(func=cmd_overlay)

    # vg talking-head composite - Legacy single-overlay (backward compatible)
    comp_parser = th_sub.add_parser('composite', help='Composite talking head onto video')
    comp_parser.add_argument('--video', required=True, help='Main video file path')
    comp_parser.add_argument('--talking-head', required=True, help='Talking head video file path')
    comp_parser.add_argument('--output', '-o', required=True, help='Output video path')
    comp_parser.add_argument('--position', default='bottom-right',
                           choices=['top-left', 'top-right', 'bottom-left', 'bottom-right'],
                           help='Overlay position')
    comp_parser.add_argument('--size', type=int, default=280, help='Overlay size in pixels')
    comp_parser.add_argument('--start-time', type=float, default=0, help='Start time in seconds')
    comp_parser.set_defaults(func=cmd_composite)

def cmd_generate(args) -> dict:
    """Handle vg talking-head generate command."""
    # Validate environment
    env_check = validate_env_for_command("talking-head.generate")
    if not env_check["success"]:
        return env_check

    return generate_talking_head(
        audio_path=args.audio,
        output_path=args.output,
        character_image=args.character,
        model=args.model
    )

def cmd_composite(args) -> dict:
    """Handle vg talking-head composite command."""
    return composite_talking_head(
        main_video=args.video,
        talking_head_video=args.talking_head,
        output_path=args.output,
        position=args.position,
        size=args.size,
        start_time=args.start_time
    )


def cmd_overlay(args) -> dict:
    """
    Handle vg talking-head overlay command.
    
    AGENTIC DESIGN: This is a DUMB executor.
    - AI agent calculates exact overlay times
    - AI passes them as --overlay file:time arguments
    - This tool just overlays videos at those times with FFmpeg
    - NO marker matching, NO intelligence, NO heuristics
    
    Usage:
        vg talking-head overlay \\
            --video composed.mp4 \\
            --overlay th_processing.mp4:47.6 \\
            --overlay th_reveal.mp4:99.3 \\
            --position bottom-right \\
            --size 280 \\
            -o final.mp4
    """
    import subprocess
    import tempfile
    from vg_common import get_ffmpeg, get_duration
    
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        return {"success": False, "error": "ffmpeg not found", "code": "CONFIG_ERROR"}
    
    try:
        video_path = Path(args.video)
        output_path = Path(args.output)
        
        # Validate main video exists
        if not video_path.exists():
            return {
                "success": False,
                "error": f"Video not found: {video_path}",
                "code": "FILE_NOT_FOUND"
            }
        
        # Parse overlay placements: "file.mp4:47.6" -> (file, start_time)
        overlays = []
        for overlay_spec in args.overlay:
            if ':' not in overlay_spec:
                return {
                    "success": False,
                    "error": f"Invalid overlay format: '{overlay_spec}'. Use 'file.mp4:start_time'",
                    "code": "VALIDATION_ERROR"
                }
            
            file_part, time_part = overlay_spec.rsplit(':', 1)
            overlay_file = Path(file_part)
            
            if not overlay_file.exists():
                return {
                    "success": False,
                    "error": f"Overlay file not found: {overlay_file}",
                    "code": "FILE_NOT_FOUND"
                }
            
            try:
                start_time = float(time_part)
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid time value: '{time_part}' in '{overlay_spec}'",
                    "code": "VALIDATION_ERROR"
                }
            
            # Get overlay duration
            duration = get_duration(overlay_file)
            
            overlays.append({
                "file": str(overlay_file),
                "start_s": start_time,
                "duration_s": duration,
                "end_s": start_time + duration
            })
        
        if not overlays:
            return {
                "success": False,
                "error": "No overlays provided",
                "code": "VALIDATION_ERROR"
            }
        
        # Sort overlays by start time
        overlays.sort(key=lambda x: x["start_s"])
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate position offset
        position = args.position
        size = args.size
        
        if "right" in position:
            x_offset = f"main_w-overlay_w-20"
        else:
            x_offset = "20"
        
        if "bottom" in position:
            y_offset = f"main_h-overlay_h-20"
        else:
            y_offset = "20"
        
        print(f"🎬 Overlaying {len(overlays)} talking head(s) at AI-specified times:")
        for o in overlays:
            print(f"   {Path(o['file']).name}: {o['start_s']:.2f}s - {o['end_s']:.2f}s ({o['duration_s']:.1f}s)")
        
        # For a single overlay, use simple approach
        if len(overlays) == 1:
            o = overlays[0]
            filter_complex = (
                f"[1:v]scale={size}:{size}:force_original_aspect_ratio=decrease[ovr];"
                f"[0:v][ovr]overlay={x_offset}:{y_offset}:enable='between(t,{o['start_s']},{o['end_s']})'[vout]"
            )
            
            cmd = [
                ffmpeg, "-y",
                "-i", str(video_path),
                "-i", o["file"],
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "0:a?",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(output_path)
            ]
        else:
            # Multiple overlays - chain them
            # Build complex filter that applies overlays sequentially
            inputs = ["-i", str(video_path)]
            for o in overlays:
                inputs.extend(["-i", o["file"]])
            
            # Scale all overlays
            filter_parts = []
            for i in range(len(overlays)):
                filter_parts.append(f"[{i+1}:v]scale={size}:{size}:force_original_aspect_ratio=decrease[ovr{i}]")
            
            # Chain overlays
            prev_output = "[0:v]"
            for i, o in enumerate(overlays):
                if i == len(overlays) - 1:
                    out_label = "[vout]"
                else:
                    out_label = f"[v{i}]"
                filter_parts.append(
                    f"{prev_output}[ovr{i}]overlay={x_offset}:{y_offset}:enable='between(t,{o['start_s']},{o['end_s']})'{out_label}"
                )
                prev_output = out_label
            
            filter_complex = ";".join(filter_parts)
            
            cmd = [
                ffmpeg, "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "0:a?",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(output_path)
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"FFmpeg failed: {result.stderr[:500]}",
                "code": "FFMPEG_ERROR"
            }
        
        # Get output duration
        output_duration = get_duration(output_path)
        
        print(f"✅ Talking heads overlaid successfully!")
        
        return {
            "success": True,
            "video": str(output_path),
            "duration_s": output_duration,
            "overlays": overlays,
            "overlays_applied": len(overlays),
            "position": position,
            "size": size
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNEXPECTED_ERROR"
        }