"""
vg talking-head commands

Talking head generation and composition.

AGENTIC DESIGN:
- `overlay`: DUMB executor - AI provides exact times, tool just overlays videos
- `composite`: Legacy single-overlay command (backward compatible)
- `create`: Square TH for overlays (PiP)
- `segment`/`intro`/`outro`: Fullscreen TH at video resolution

TH TYPES:
- Overlay (square): For PiP during video narration
- Segment (video resolution): For standalone intro/middle/outro segments
"""

import re
import subprocess
import tempfile
from pathlib import Path
from vg_talking_head import generate_character, generate_talking_head, composite_talking_head
from vg_common import validate_env_for_command, get_ffmpeg, get_duration

# Constants
DEFAULT_VOICE_ID = '21m00Tcm4TlvDq8ikWAM'  # ElevenLabs Rachel voice

# Default resolution for fullscreen TH segments (intro/outro/segment) when:
# - User doesn't provide --resolution or --match-video
# - Video resolution detection fails
# Common recording sizes: 1920x1080, 1280x720
DEFAULT_RESOLUTION = (1920, 1080)

# Fullscreen TH composition settings (YouTuber-style framing)
CHAR_HEIGHT_RATIO = 0.6   # Character takes 60% of frame height
CHAR_BOTTOM_MARGIN = 0.1  # 10% margin from bottom

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

    # vg talking-head create - CONVENIENCE: TTS + generate in one step
    create_parser = th_sub.add_parser('create', help='Create talking head from text (TTS + generate)')
    create_parser.add_argument('--text', required=True, help='Text to speak')
    create_parser.add_argument('--output', '-o', required=True, help='Output video path')
    create_parser.add_argument('--character', help='Character image path (auto-generated if not provided)')
    create_parser.add_argument('--model', default='omnihuman', choices=['omnihuman', 'sadtalker'], help='Model to use')
    create_parser.add_argument('--voice-id', default=DEFAULT_VOICE_ID, help='ElevenLabs voice ID')
    create_parser.set_defaults(func=cmd_create)

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

    # Helper to add segment args (reused for segment/intro/outro)
    def _add_segment_args(parser):
        parser.add_argument('--text', required=True, help='Text to speak')
        parser.add_argument('--output', '-o', required=True, help='Output video path')
        parser.add_argument('--resolution', help='Target resolution (e.g., 1280x720)')
        parser.add_argument('--match-video', help='Match resolution from this video')
        parser.add_argument('--character', help='Character image path (auto-generated if not provided)')
        parser.add_argument('--background', default='gradient', 
                          choices=['black', 'gradient', 'blur'], help='Background style')
        parser.add_argument('--voice-id', default=DEFAULT_VOICE_ID, help='ElevenLabs voice ID')
        parser.add_argument('--model', default='omnihuman', choices=['omnihuman', 'sadtalker'], 
                          help='Model to use')

    # vg talking-head segment - Fullscreen TH at video resolution (for any position)
    segment_parser = th_sub.add_parser('segment', 
        help='Create fullscreen TH segment (matches video resolution, for start/middle/end)')
    _add_segment_args(segment_parser)
    segment_parser.set_defaults(func=cmd_segment)

    # vg talking-head intro - Alias for segment (clearer intent)
    intro_parser = th_sub.add_parser('intro', 
        help='Create fullscreen intro TH (alias for segment)')
    _add_segment_args(intro_parser)
    intro_parser.set_defaults(func=cmd_segment)

    # vg talking-head outro - Alias for segment (clearer intent)
    outro_parser = th_sub.add_parser('outro', 
        help='Create fullscreen outro TH (alias for segment)')
    _add_segment_args(outro_parser)
    outro_parser.set_defaults(func=cmd_segment)

    # vg talking-head title - AI-generated title card video (no presenter)
    title_parser = th_sub.add_parser('title', 
        help='Create AI-generated title card video for transitions')
    title_parser.add_argument('--text', required=True, help='Title text to display')
    title_parser.add_argument('--output', '-o', required=True, help='Output video path')
    title_parser.add_argument('--duration', type=float, default=3.0, help='Video duration in seconds (default: 3)')
    title_parser.add_argument('--resolution', help='Target resolution (e.g., 1280x720)')
    title_parser.add_argument('--match-video', help='Match resolution from this video')
    title_parser.add_argument('--style', default='cinematic', 
                            choices=['cinematic', 'tech', 'minimal', 'gradient', 'dynamic'],
                            help='Visual style for the title card')
    title_parser.set_defaults(func=cmd_title)

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


def cmd_create(args) -> dict:
    """
    Create talking head from text in one step (TTS + generate).
    
    DUMB WRAPPER: Just combines TTS + generate. No intelligence.
    AI decides when to use this and where to place the result.
    
    Usage:
        vg talking-head create --text "Hi! Welcome." -o th_intro.mp4
    
    Returns:
        {"video": "th_intro.mp4", "audio": "th_intro.mp3", "duration_s": 2.1}
    """
    from vg_tts import tts_with_json_output
    
    # Validate environment (need both ElevenLabs and FAL)
    env_check = validate_env_for_command("talking-head.create")
    if not env_check["success"]:
        return env_check
    
    output_path = Path(args.output)
    audio_path = output_path.with_suffix('.mp3')
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate TTS
    text_preview = args.text[:50] + "..." if len(args.text) > 50 else args.text
    print(f"🎤 Generating TTS: \"{text_preview}\"")
    
    tts_result = tts_with_json_output(
        text=args.text,
        output_path=str(audio_path),
        voice_id=args.voice_id
    )
    
    if not tts_result.get("success"):
        return {
            "success": False,
            "error": f"TTS failed: {tts_result.get('error')}",
            "code": tts_result.get("code", "TTS_ERROR")
        }
    
    duration_s = tts_result.get("duration_s") or tts_result.get("duration") or 0
    print(f"   ✅ Audio: {audio_path.name} ({duration_s:.1f}s)")
    
    # Step 2: Generate talking head
    print(f"🎬 Generating talking head with {args.model}...")
    
    # Generate character if not provided (as documented)
    character = args.character
    if not character:
        print("   🎭 Auto-generating character image...")
        char_result = generate_character()
        if not char_result.get("success"):
            return {
                "success": False,
                "error": f"Character generation failed: {char_result.get('error')}",
                "code": char_result.get("code", "CHARACTER_ERROR")
            }
        character = char_result.get("image")
    
    th_result = generate_talking_head(
        audio_path=str(audio_path),
        output_path=str(output_path),
        character_image=character,
        model=args.model
    )
    
    if not th_result.get("success"):
        return {
            "success": False,
            "error": f"TH generation failed: {th_result.get('error')}",
            "code": th_result.get("code", "TH_ERROR")
        }
    
    print(f"   ✅ Video: {output_path.name}")
    
    return {
        "success": True,
        "video": str(output_path),
        "audio": str(audio_path),
        "duration_s": duration_s,
        "model": args.model,
        "cached": th_result.get("cached", False)
    }


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
        
        # Validate overlay times against video duration
        video_duration = get_duration(video_path)
        warnings = []
        
        for o in overlays:
            if o["start_s"] > video_duration:
                return {
                    "success": False,
                    "error": f"Overlay start time ({o['start_s']:.1f}s) exceeds video duration ({video_duration:.1f}s)",
                    "code": "VALIDATION_ERROR",
                    "suggestion": f"Use a start time less than {video_duration:.1f}s"
                }
            
            if o["start_s"] < 0:
                return {
                    "success": False,
                    "error": f"Overlay start time cannot be negative ({o['start_s']:.1f}s)",
                    "code": "VALIDATION_ERROR"
                }
            
            if o["end_s"] > video_duration:
                warnings.append(
                    f"TH '{Path(o['file']).name}' extends past video end "
                    f"({o['end_s']:.1f}s > {video_duration:.1f}s) - will be clipped"
                )
        
        if warnings:
            for w in warnings:
                print(f"⚠️  {w}")
        
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
                "-itsoffset", str(o['start_s']),  # CRITICAL: Delay TH input to sync with overlay time
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
            # CRITICAL: Each TH input needs -itsoffset to sync frame 0 with overlay start time
            inputs = ["-i", str(video_path)]
            for o in overlays:
                inputs.extend(["-itsoffset", str(o['start_s']), "-i", o["file"]])
            
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


def _get_video_resolution(video_path: str) -> tuple:
    """Get video resolution (width, height) using ffmpeg."""
    ffmpeg = get_ffmpeg()
    result = subprocess.run(
        [ffmpeg, "-i", video_path],
        capture_output=True, text=True
    )
    
    # Look for video stream resolution - match "WIDTHxHEIGHT" after "Video:" line
    # Handles common resolutions: 640x480, 1280x720, 1920x1080, 3840x2160, etc.
    video_match = re.search(r'Video:.*?(\d{3,5})x(\d{3,5})', result.stderr)
    if video_match:
        return int(video_match.group(1)), int(video_match.group(2))
    
    # Warn and fall back to default
    print(f"   ⚠️  Could not detect resolution for {Path(video_path).name}, using default {DEFAULT_RESOLUTION[0]}x{DEFAULT_RESOLUTION[1]}")
    return DEFAULT_RESOLUTION


def _compose_fullscreen_th(
    th_video: str,
    output_path: str,
    resolution: tuple,
    background: str = "gradient"
) -> str:
    """
    Compose square TH into fullscreen video at target resolution.
    
    Places the TH character naturally (like a YouTuber video) on a background.
    Character is NOT enlarged to fill the frame - uses natural sizing.
    
    Args:
        th_video: Path to square TH video
        output_path: Path for output video
        resolution: Target (width, height) tuple
        background: Background style ('black', 'gradient', 'blur')
    
    Returns:
        Path to output video
    """
    ffmpeg = get_ffmpeg()
    target_w, target_h = resolution
    
    # Get TH video dimensions (should be square, e.g., 960x960)
    th_w, th_h = _get_video_resolution(th_video)
    
    # Calculate character size - natural framing, not filling the screen
    char_height = int(target_h * CHAR_HEIGHT_RATIO)
    char_width = int(char_height * (th_w / th_h))  # Maintain aspect ratio
    
    # Center horizontally, position in lower portion of frame (like YouTuber)
    x_pos = (target_w - char_width) // 2
    y_pos = target_h - char_height - int(target_h * CHAR_BOTTOM_MARGIN)
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    # Build filter based on background style
    if background == "black":
        # Simple black background
        filter_complex = (
            f"color=black:s={target_w}x{target_h}:d=9999[bg];"
            f"[1:v]scale={char_width}:{char_height}[th];"
            f"[bg][th]overlay={x_pos}:{y_pos}:shortest=1[vout]"
        )
    elif background == "gradient":
        # Gradient background (dark blue to dark)
        filter_complex = (
            f"gradients=s={target_w}x{target_h}:c0=0x1a1a2e:c1=0x16213e:x0=0:y0=0:x1=0:y1={target_h}:d=9999[bg];"
            f"[1:v]scale={char_width}:{char_height}[th];"
            f"[bg][th]overlay={x_pos}:{y_pos}:shortest=1[vout]"
        )
    else:  # blur
        # Blurred version of the TH as background
        filter_complex = (
            f"[1:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},boxblur=20:20[bg];"
            f"[1:v]scale={char_width}:{char_height}[th];"
            f"[bg][th]overlay={x_pos}:{y_pos}:shortest=1[vout]"
        )
    
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"color=black:s={target_w}x{target_h}:d=1",  # Dummy for gradients
        "-i", th_video,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "1:a?",  # Keep TH audio if present
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0:
        # Fallback to simpler approach if gradient filter not available
        # Check for specific filter errors (e.g., "No such filter", "Unknown filter")
        if background == "gradient" and ("No such filter" in result.stderr or 
                                          "Unknown filter" in result.stderr or
                                          "gradients" in result.stderr.lower()):
            print("   ⚠️  Gradient filter not available, using black background")
            return _compose_fullscreen_th(th_video, output_path, resolution, "black")
        raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")
    
    return str(output)


def cmd_segment(args) -> dict:
    """
    Create fullscreen talking head segment at video resolution.
    
    DUMB EXECUTOR: Combines TTS + TH generation + fullscreen composition.
    AI decides when to use this and where to place the result (concat).
    
    For intro/outro or in-between segments - NOT for PiP overlays.
    Use `vg talking-head create` for square overlay THs.
    
    Usage:
        vg talking-head segment --text "Welcome!" --match-video main.mp4 -o intro.mp4
        vg talking-head intro --text "Hi!" --resolution 1280x720 -o intro.mp4
        vg talking-head outro --text "Thanks!" --match-video main.mp4 -o outro.mp4
    
    Returns:
        {"video": "intro.mp4", "audio": "intro.mp3", "duration_s": 3.2, "resolution": "1280x720"}
    """
    from vg_tts import tts_with_json_output
    
    # Validate environment (need ElevenLabs + FAL)
    env_check = validate_env_for_command("talking-head.segment")
    if not env_check["success"]:
        return env_check
    
    try:
        output_path = Path(args.output)
        audio_path = output_path.with_suffix('.mp3')
        
        # Determine target resolution
        if args.match_video:
            match_path = Path(args.match_video)
            if not match_path.exists():
                return {
                    "success": False,
                    "error": f"Match video not found: {match_path}",
                    "code": "FILE_NOT_FOUND"
                }
            target_w, target_h = _get_video_resolution(str(match_path))
            print(f"📐 Matched resolution from {match_path.name}: {target_w}x{target_h}")
        elif args.resolution:
            try:
                target_w, target_h = map(int, args.resolution.lower().split('x'))
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid resolution format: {args.resolution}. Use WIDTHxHEIGHT (e.g., 1280x720)",
                    "code": "VALIDATION_ERROR"
                }
            print(f"📐 Using specified resolution: {target_w}x{target_h}")
        else:
            target_w, target_h = DEFAULT_RESOLUTION
            print(f"📐 Using default Full HD resolution: {target_w}x{target_h}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Generate TTS
        text_preview = args.text[:50] + "..." if len(args.text) > 50 else args.text
        print(f"🎤 Generating TTS: \"{text_preview}\"")
        
        tts_result = tts_with_json_output(
            text=args.text,
            output_path=str(audio_path),
            voice_id=args.voice_id
        )
        
        if not tts_result.get("success"):
            return {
                "success": False,
                "error": f"TTS failed: {tts_result.get('error')}",
                "code": tts_result.get("code", "TTS_ERROR")
            }
        
        duration_s = tts_result.get("duration_s") or tts_result.get("duration") or 0
        print(f"   ✅ Audio: {audio_path.name} ({duration_s:.1f}s)")
        
        # Step 2: Generate character if not provided
        # For fullscreen segments (intro/outro/segment), use studio style (YouTuber in studio)
        character = args.character
        if not character:
            print("   🎭 Auto-generating YouTuber studio character...")
            char_result = generate_character(style="studio")  # Studio style for fullscreen segments
            if not char_result.get("success"):
                return {
                    "success": False,
                    "error": f"Character generation failed: {char_result.get('error')}",
                    "code": char_result.get("code", "CHARACTER_ERROR")
                }
            character = char_result.get("image")
            print(f"   ✅ Using studio character: {character}")
        
        # Step 3: Generate fullscreen TH (OmniHuman preserves aspect ratio of input image)
        # With studio image (16:9), output will be fullscreen, not square
        print(f"🎬 Generating fullscreen talking head with {args.model}...")
        
        # Use temp file for intermediate TH if scaling needed
        th_raw_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                th_raw_path = tmp.name
            
            th_result = generate_talking_head(
                audio_path=str(audio_path),
                output_path=th_raw_path,
                character_image=character,
                model=args.model
            )
            
            if not th_result.get("success"):
                return {
                    "success": False,
                    "error": f"TH generation failed: {th_result.get('error')}",
                    "code": th_result.get("code", "TH_ERROR")
                }
            
            print(f"   ✅ Fullscreen TH generated")
            
            # Step 4: Scale to exact target resolution (OmniHuman output may be slightly different)
            print(f"🖼️  Scaling to target resolution ({target_w}x{target_h})...")
            
            ffmpeg = get_ffmpeg()
            scale_cmd = [
                ffmpeg, "-y",
                "-i", th_raw_path,
                "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            result = subprocess.run(scale_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Scaling failed: {result.stderr}",
                    "code": "SCALING_ERROR"
                }
            
            # Get final duration
            final_duration = get_duration(Path(output_path))
            
            print(f"   ✅ Video: {output_path.name}")
            print(f"✅ Fullscreen TH segment complete!")
            
            return {
                "success": True,
                "video": str(output_path),
                "audio": str(audio_path),
                "duration_s": final_duration,
                "resolution": f"{target_w}x{target_h}",
                "model": args.model,
                "type": "segment",  # Fullscreen segment (not overlay)
                "style": "studio",  # YouTuber studio style
                "cached": th_result.get("cached", False)
            }
        finally:
            # Always clean up temp file
            if th_raw_path:
                Path(th_raw_path).unlink(missing_ok=True)
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNEXPECTED_ERROR"
        }


def cmd_title(args) -> dict:
    """
    Generate AI title card video for transitions using xAI Grok Imagine Video.
    
    Creates a cinematic title/transition video without a presenter.
    Uses text-to-video generation directly (no intermediate image step).
    Useful for introducing sections or topics in a video.
    
    Usage:
        vg talking-head title --text "Part 2: Building the Dashboard" -o title.mp4
        vg talking-head title --text "Key Features" --style tech --match-video main.mp4 -o title.mp4
    
    Returns:
        {"video": "title.mp4", "duration_s": 3.0, "resolution": "1280x720", "style": "cinematic"}
    """
    import os
    
    # Validate environment
    env_check = validate_env_for_command("talking-head.title")
    if not env_check["success"]:
        return env_check
    
    try:
        output_path = Path(args.output)
        
        # Determine target resolution
        if args.match_video:
            match_path = Path(args.match_video)
            if not match_path.exists():
                return {
                    "success": False,
                    "error": f"Match video not found: {match_path}",
                    "code": "FILE_NOT_FOUND"
                }
            target_w, target_h = _get_video_resolution(str(match_path))
            print(f"📐 Matched resolution from {match_path.name}: {target_w}x{target_h}")
        elif args.resolution:
            try:
                target_w, target_h = map(int, args.resolution.lower().split('x'))
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid resolution format: {args.resolution}. Use WIDTHxHEIGHT (e.g., 1280x720)",
                    "code": "VALIDATION_ERROR"
                }
            print(f"📐 Using specified resolution: {target_w}x{target_h}")
        else:
            target_w, target_h = DEFAULT_RESOLUTION
            print(f"📐 Using default resolution: {target_w}x{target_h}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build prompt based on style
        style_prompts = {
            "cinematic": f"Cinematic title card with elegant typography showing \"{args.text}\", professional film quality, dramatic lighting, subtle motion, dark background with light rays, 4K quality",
            "tech": f"Modern tech-style title card showing \"{args.text}\", sleek digital aesthetic, glowing neon accents, futuristic grid background, smooth animation, high-tech corporate feel",
            "minimal": f"Minimalist clean title card displaying \"{args.text}\", simple elegant design, white text on dark gradient, subtle fade animation, professional and modern",
            "gradient": f"Stylish gradient background title card with \"{args.text}\", colorful flowing gradients, modern typography, smooth color transitions, trendy design aesthetic",
            "dynamic": f"Dynamic motion graphics title card showing \"{args.text}\", energetic particle effects, bold typography with impact, dramatic reveal animation, high energy"
        }
        
        prompt = style_prompts.get(args.style, style_prompts["cinematic"])
        requested_duration = args.duration
        
        print(f"🎬 Generating title card video with Grok Imagine Video...")
        print(f"   📝 Text: \"{args.text}\"")
        print(f"   🎨 Style: {args.style}")
        print(f"   ⏱️  Requested duration: {requested_duration}s")
        
        # Use Grok Imagine Video (xAI's text-to-video model)
        try:
            import fal_client
            os.environ["FAL_KEY"] = os.environ.get("FAL_API_KEY", "")
            
            print("   🚀 Calling xAI Grok Imagine Video...")
            
            # Grok Imagine Video supports 6s duration (minimum), so we generate and trim
            # It produces videos with audio, which we'll strip for title cards
            grok_duration = max(6, int(requested_duration))  # Grok minimum is 6s
            
            video_result = fal_client.subscribe(
                "xai/grok-imagine-video/text-to-video",
                arguments={
                    "prompt": prompt,
                    "duration": grok_duration,
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                },
            )
            
            video_url = video_result["video"]["url"]
            generated_duration = video_result["video"].get("duration", grok_duration)
            
            print(f"   ✅ Grok generated {generated_duration:.1f}s video")
            
            # Download video
            import urllib.request
            temp_video = output_path.with_suffix('.temp.mp4')
            urllib.request.urlretrieve(video_url, str(temp_video))
            
            # Scale to target resolution and trim to requested duration
            print(f"   🖼️  Scaling to {target_w}x{target_h} and trimming to {requested_duration}s...")
            
            ffmpeg = get_ffmpeg()
            scale_cmd = [
                ffmpeg, "-y",
                "-i", str(temp_video),
                "-t", str(requested_duration),  # Trim to requested duration
                "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-an",  # No audio for title cards
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            result = subprocess.run(scale_cmd, capture_output=True, text=True, timeout=120)
            
            # Clean up temp file
            temp_video.unlink(missing_ok=True)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Video processing failed: {result.stderr}",
                    "code": "PROCESSING_ERROR"
                }
            
            # Get final duration
            final_duration = get_duration(output_path)
            
            print(f"   ✅ Video: {output_path.name}")
            print(f"✅ Title card video complete!")
            
            return {
                "success": True,
                "video": str(output_path),
                "duration_s": final_duration,
                "resolution": f"{target_w}x{target_h}",
                "style": args.style,
                "text": args.text,
                "type": "title",
                "model": "grok-imagine-video"
            }
            
        except Exception as e:
            error_msg = str(e)
            if "fal_client" in error_msg or "FAL" in error_msg.upper() or "xai" in error_msg.lower():
                return {
                    "success": False,
                    "error": f"Grok Imagine Video generation failed: {error_msg}",
                    "code": "FAL_ERROR",
                    "suggestion": "Check FAL_API_KEY is set and has access to xai/grok-imagine-video"
                }
            raise
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNEXPECTED_ERROR"
        }