"""
Caption command handlers for vg CLI.

Commands:
- vg captions generate: Generate SRT/VTT from request + timeline
- vg captions burn: Burn captions into video
- vg captions preview: Preview caption timing
- vg captions streaming: Word-by-word streaming captions
"""

import json
from pathlib import Path

# All caption functionality is now in consolidated vg_captions module
from vg_captions import (
    # Basic caption generation
    calculate_caption_times, validate_caption_timing,
    generate_srt_file, generate_vtt_file, burn_captions_into_video,
    parse_caption_style, CaptionEntry,
    # Advanced features
    adjust_caption_times_for_edits,
    burn_captions_with_animation,
    get_protected_audio_segments,
    filter_silence_intervals_with_audio_protection,
    # Word-level streaming captions
    create_streaming_captions,
    generate_word_level_srt,
    burn_small_captions,
    calculate_word_timings,
    WordCaption,
)
from vg_common import error_response, success_response
from vg_core_utils.md_parser import parse_voiceover_segments_from_md, parse_agentic_narration_from_md
from vg_core_utils.timeline import load_timeline_markers


def cmd_generate(args) -> dict:
    """
    Generate caption file (SRT/VTT) from request file and timeline.
    
    Args:
        args.request: Path to request MD file
        args.timeline: Path to timeline MD file
        args.audio_dir: Path to audio directory
        args.output: Output path for caption file
        args.format: Caption format ('srt' or 'vtt')
        args.validate: Whether to validate timing
    
    Returns:
        Dict with success status and file info
    """
    try:
        request_path = Path(args.request)
        timeline_path = Path(args.timeline)
        audio_dir = Path(args.audio_dir)
        output_path = Path(args.output)
        caption_format = getattr(args, 'format', 'srt').lower()
        validate = getattr(args, 'validate', True)
        
        # Validate inputs
        if not request_path.exists():
            return error_response(FileNotFoundError(f"Request file not found: {request_path}"), "")
        if not timeline_path.exists():
            return error_response(FileNotFoundError(f"Timeline file not found: {timeline_path}"), "")
        if not audio_dir.exists():
            return error_response(FileNotFoundError(f"Audio directory not found: {audio_dir}"), "")
        
        # Parse request file for voiceover segments (try legacy format first, then agentic)
        request_content = request_path.read_text(encoding='utf-8')
        voiceover_segments = parse_voiceover_segments_from_md(request_content)
        
        if not voiceover_segments:
            # Try agentic narration format (## Narration section)
            voiceover_segments = parse_agentic_narration_from_md(request_content)
        
        if not voiceover_segments:
            return error_response(ValueError("No voiceover segments found in request file. Expected '## Narration' section or VOICEOVER_SEGMENTS markers."), "")
        
        # Load timeline markers
        timeline_markers = load_timeline_markers(timeline_path)
        
        if not timeline_markers:
            return error_response(ValueError("No timeline markers found in timeline file"), "")
        
        # Calculate caption times
        captions = calculate_caption_times(voiceover_segments, timeline_markers, audio_dir)
        
        if not captions:
            return error_response(ValueError("No captions generated"), "")
        
        # Validate timing if requested
        validation_result = None
        if validate:
            validation_result = validate_caption_timing(captions)
            if not validation_result["valid"]:
                # Return warning but continue
                print(f"⚠️  Caption timing issues detected:")
                for issue in validation_result["issues"]:
                    print(f"   - {issue}")
        
        # Generate caption file
        if caption_format == 'vtt':
            result = generate_vtt_file(captions, output_path)
        else:
            result = generate_srt_file(captions, output_path)
        
        # Add validation info to result
        if validation_result:
            result["validation"] = validation_result
        
        return result
    
    except Exception as e:
        return error_response(e, "Caption generation failed")


def cmd_burn(args) -> dict:
    """
    Burn captions into video.
    
    Args:
        args.video: Path to input video
        args.captions: Path to SRT file
        args.output: Path to output video
        args.style: Style preset name (e.g., 'youtube', 'professional')
        args.request: Optional request file for inline style overrides
        args.animate: Whether to add fade animations (default: True)
        args.fade_duration: Fade duration in seconds (default: 0.2)
    
    Returns:
        Dict with success status and output file info
    """
    try:
        video_path = Path(args.video)
        captions_path = Path(args.captions)
        output_path = Path(args.output)
        style_name = getattr(args, 'style', 'professional')
        request_path = getattr(args, 'request', None)
        animate = getattr(args, 'animate', True)
        fade_duration = getattr(args, 'fade_duration', 0.2)
        
        # Validate inputs
        if not video_path.exists():
            return error_response(FileNotFoundError(f"Video file not found: {video_path}"), "")
        if not captions_path.exists():
            return error_response(FileNotFoundError(f"Captions file not found: {captions_path}"), "")
        
        # Parse style (with optional request file override)
        request_content = None
        if request_path:
            request_path = Path(request_path)
            if request_path.exists():
                request_content = request_path.read_text(encoding='utf-8')
        
        style = parse_caption_style(style_name, request_md_content=request_content)
        
        # Burn captions with or without animation
        if animate:
            result = burn_captions_with_animation(
                video_path=str(video_path),
                srt_path=str(captions_path),
                output_path=str(output_path),
                style=style,
                style_name=style_name,
                fade_duration=fade_duration
            )
        else:
            result = burn_captions_into_video(
                video_path=video_path,
                srt_path=captions_path,
                output_path=output_path,
                style=style,
                style_name=style_name
            )
        
        return result
    
    except Exception as e:
        return error_response(e, "Caption burn failed")


def cmd_preview(args) -> dict:
    """
    Preview caption timing and text.
    
    Args:
        args.captions: Path to SRT file (optional if generating from request)
        args.request: Path to request MD file (for generating captions)
        args.timeline: Path to timeline MD file (for generating captions)
        args.audio_dir: Path to audio directory (for generating captions)
        args.start_time: Optional start time in seconds
        args.duration: Optional duration to preview
    
    Returns:
        Dict with caption preview info
    """
    try:
        captions_path = getattr(args, 'captions', None)
        request_path = getattr(args, 'request', None)
        timeline_path = getattr(args, 'timeline', None)
        audio_dir = getattr(args, 'audio_dir', None)
        start_time = getattr(args, 'start_time', None)
        duration = getattr(args, 'duration', None)
        
        # Either load from SRT or generate from request
        if captions_path:
            # Load existing SRT (future enhancement)
            return error_response(NotImplementedError("SRT parsing not yet implemented"), "")
        
        elif request_path and timeline_path and audio_dir:
            # Generate captions
            request_path = Path(request_path)
            timeline_path = Path(timeline_path)
            audio_dir = Path(audio_dir)
            
            if not request_path.exists():
                return error_response(FileNotFoundError(f"Request file not found: {request_path}"), "")
            if not timeline_path.exists():
                return error_response(FileNotFoundError(f"Timeline file not found: {timeline_path}"), "")
            if not audio_dir.exists():
                return error_response(FileNotFoundError(f"Audio directory not found: {audio_dir}"), "")
            
            # Parse and calculate (try legacy format first, then agentic)
            request_content = request_path.read_text(encoding='utf-8')
            voiceover_segments = parse_voiceover_segments_from_md(request_content)
            if not voiceover_segments:
                voiceover_segments = parse_agentic_narration_from_md(request_content)
            timeline_markers = load_timeline_markers(timeline_path)
            captions = calculate_caption_times(voiceover_segments, timeline_markers, audio_dir)
            
            # Filter by time range if specified
            if start_time is not None:
                end_time = start_time + duration if duration else float('inf')
                captions = [c for c in captions if c.start_s >= start_time and c.start_s < end_time]
            
            # Validate
            validation = validate_caption_timing(captions)
            
            # Format preview
            preview_lines = []
            for i, caption in enumerate(captions, start=1):
                preview_lines.append(f"\n[{i}] {caption.start_s:.2f}s → {caption.end_s:.2f}s ({caption.duration_s:.2f}s)")
                preview_lines.append(f"    {caption.text}")
            
            return success_response(
                captions_count=len(captions),
                validation=validation,
                preview='\n'.join(preview_lines),
                captions=[{
                    "index": i,
                    "start_s": c.start_s,
                    "end_s": c.end_s,
                    "duration_s": c.duration_s,
                    "text": c.text,
                    "segment_id": c.segment_id
                } for i, c in enumerate(captions, start=1)]
            )
        
        else:
            return error_response(ValueError("Must provide either --captions or (--request + --timeline + --audio-dir)"), "")
    
    except Exception as e:
        return error_response(e, "Caption preview failed")


def cmd_streaming(args) -> dict:
    """
    Create streaming word-by-word captions (like TikTok/YouTube).
    
    Args:
        args.video: Path to input video
        args.request: Path to request MD file
        args.timeline: Path to timeline MD file
        args.audio_dir: Path to audio directory
        args.output: Output path for captioned video
        args.words: Words per group (default: 3)
        args.font_size: Font size in FFmpeg units (default: 10)
        args.trim_offset: Seconds trimmed from start (default: 0)
    """
    try:
        video_path = Path(args.video)
        request_path = Path(args.request)
        timeline_path = Path(args.timeline)
        audio_dir = Path(args.audio_dir)
        output_path = Path(args.output)
        words_per_group = getattr(args, 'words', 3)
        font_size = getattr(args, 'font_size', 10)
        trim_offset = getattr(args, 'trim_offset', 0.0)
        
        # Validate inputs
        if not video_path.exists():
            return error_response(FileNotFoundError(f"Video not found: {video_path}"), "")
        if not request_path.exists():
            return error_response(FileNotFoundError(f"Request not found: {request_path}"), "")
        if not timeline_path.exists():
            return error_response(FileNotFoundError(f"Timeline not found: {timeline_path}"), "")
        if not audio_dir.exists():
            return error_response(FileNotFoundError(f"Audio dir not found: {audio_dir}"), "")
        
        # Parse request and timeline (try legacy format first, then agentic)
        request_content = request_path.read_text(encoding='utf-8')
        voiceover_segments = parse_voiceover_segments_from_md(request_content)
        
        if not voiceover_segments:
            # Try agentic narration format (## Narration section)
            voiceover_segments = parse_agentic_narration_from_md(request_content)
        
        timeline_markers = load_timeline_markers(timeline_path)
        
        if not voiceover_segments:
            return error_response(ValueError("No voiceover segments in request. Expected '## Narration' section or VOICEOVER_SEGMENTS markers."), "")
        if not timeline_markers:
            return error_response(ValueError("No timeline markers"), "")
        
        # Calculate caption times
        from vg_captions import calculate_caption_times
        from vg_common import get_duration as gd
        
        captions = calculate_caption_times(voiceover_segments, timeline_markers, audio_dir)
        
        # Convert to segments format and apply trim offset
        segments = []
        for cap in captions:
            start_s = cap.start_s - trim_offset
            end_s = cap.end_s - trim_offset
            
            # Skip if entirely before trim point
            if end_s <= 0:
                continue
            
            start_s = max(0, start_s)
            
            segments.append({
                'start_s': start_s,
                'end_s': end_s,
                'text': cap.text
            })
        
        # Create streaming captions
        result = create_streaming_captions(
            video_path=str(video_path),
            segments=segments,
            output_path=str(output_path),
            words_per_group=words_per_group,
            font_size=font_size
        )
        
        return result
    
    except Exception as e:
        return error_response(e, "Streaming caption creation failed")


def register(subparsers):
    """
    Register caption commands with argparse.
    
    Args:
        subparsers: argparse subparsers object
    """
    # Main captions command group
    captions_parser = subparsers.add_parser('captions', help='Caption generation and management')
    captions_subparsers = captions_parser.add_subparsers(dest='captions_command', help='Caption commands')
    
    # vg captions generate
    generate_parser = captions_subparsers.add_parser('generate', help='Generate caption file from request and timeline')
    generate_parser.add_argument('--request', required=True, help='Path to request MD file')
    generate_parser.add_argument('--timeline', required=True, help='Path to timeline MD file')
    generate_parser.add_argument('--audio-dir', required=True, help='Path to audio directory')
    generate_parser.add_argument('--output', '-o', required=True, help='Output path for caption file')
    generate_parser.add_argument('--format', choices=['srt', 'vtt'], default='srt', help='Caption format (default: srt)')
    generate_parser.add_argument('--no-validate', dest='validate', action='store_false', help='Skip timing validation')
    generate_parser.set_defaults(func=cmd_generate)
    
    # vg captions streaming (NEW - word-by-word captions like TikTok)
    streaming_parser = captions_subparsers.add_parser('streaming', help='Create streaming word-by-word captions (TikTok/YouTube style)')
    streaming_parser.add_argument('--video', required=True, help='Path to input video')
    streaming_parser.add_argument('--request', required=True, help='Path to request MD file')
    streaming_parser.add_argument('--timeline', required=True, help='Path to timeline MD file')
    streaming_parser.add_argument('--audio-dir', required=True, help='Path to audio directory')
    streaming_parser.add_argument('--output', '-o', required=True, help='Output path for captioned video')
    streaming_parser.add_argument('--words', type=int, default=3, help='Words per group (default: 3)')
    streaming_parser.add_argument('--font-size', type=int, default=10, help='Font size in FFmpeg units (default: 10)')
    streaming_parser.add_argument('--trim-offset', type=float, default=0.0, help='Seconds trimmed from original (default: 0)')
    streaming_parser.set_defaults(func=cmd_streaming)
    
    # vg captions burn
    burn_parser = captions_subparsers.add_parser('burn', help='Burn captions into video')
    burn_parser.add_argument('--video', required=True, help='Path to input video')
    burn_parser.add_argument('--captions', required=True, help='Path to SRT caption file')
    burn_parser.add_argument('--output', '-o', required=True, help='Path to output video')
    burn_parser.add_argument('--style', default='professional', help='Caption style preset (default: professional)')
    burn_parser.add_argument('--request', help='Optional request file for inline style overrides')
    burn_parser.add_argument('--no-animate', dest='animate', action='store_false', help='Disable fade animations')
    burn_parser.add_argument('--fade-duration', type=float, default=0.2, help='Fade animation duration in seconds (default: 0.2)')
    burn_parser.set_defaults(func=cmd_burn)
    
    # vg captions preview
    preview_parser = captions_subparsers.add_parser('preview', help='Preview caption timing and text')
    preview_parser.add_argument('--captions', help='Path to SRT file to preview')
    preview_parser.add_argument('--request', help='Path to request MD file (for generating captions)')
    preview_parser.add_argument('--timeline', help='Path to timeline MD file (for generating captions)')
    preview_parser.add_argument('--audio-dir', help='Path to audio directory (for generating captions)')
    preview_parser.add_argument('--start-time', type=float, help='Start time in seconds')
    preview_parser.add_argument('--duration', type=float, help='Duration to preview in seconds')
    preview_parser.set_defaults(func=cmd_preview)
    
    return captions_parser
