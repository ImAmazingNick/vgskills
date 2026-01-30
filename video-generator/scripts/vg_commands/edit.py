"""
vg edit commands

Video editing operations (trim, cut, speed, concat).
"""

import argparse
from pathlib import Path
from vg_edit import trim_video, cut_video, speed_video, concat_videos, speed_silence, speed_gaps

def register(subparsers):
    """Register edit commands."""
    edit_parser = subparsers.add_parser('edit', help='Video editing operations')
    edit_sub = edit_parser.add_subparsers(dest='edit_command')

    # vg edit trim
    trim_parser = edit_sub.add_parser('trim', help='Trim video (start/end)')
    trim_parser.add_argument('--video', required=True, help='Input video path')
    trim_parser.add_argument('--start', type=float, default=0, help='Start time in seconds')
    trim_parser.add_argument('--end', type=float, help='End time in seconds')
    trim_parser.add_argument('--output', '-o', required=True, help='Output video path')
    trim_parser.set_defaults(func=cmd_trim)

    # vg edit cut
    cut_parser = edit_sub.add_parser('cut', help='Cut sections from video')
    cut_parser.add_argument('--video', required=True, help='Input video path')
    cut_parser.add_argument('--cuts', required=True, help='Cut ranges (e.g., "10-20,30-40")')
    cut_parser.add_argument('--output', '-o', required=True, help='Output video path')
    cut_parser.set_defaults(func=cmd_cut)

    # vg edit speed
    speed_parser = edit_sub.add_parser('speed', help='Change video speed')
    speed_parser.add_argument('--video', required=True, help='Input video path')
    speed_parser.add_argument('--factor', type=float, required=True, help='Speed factor (e.g., 2.0 for 2x speed)')
    speed_parser.add_argument('--range', help='Time range "start-end" in seconds')
    speed_parser.add_argument('--output', '-o', required=True, help='Output video path')
    speed_parser.set_defaults(func=cmd_speed)

    # vg edit speed-silence
    silence_parser = edit_sub.add_parser('speed-silence', help='Speed up silent sections')
    silence_parser.add_argument('--video', required=True, help='Input video path')
    silence_parser.add_argument('--factor', type=float, default=3.0, help='Speed factor for silent parts')
    silence_parser.add_argument('--silence-db', type=float, default=-35.0, help='Silence threshold (dB)')
    silence_parser.add_argument('--min-silence', type=float, default=0.5, help='Minimum silence duration (s)')
    silence_parser.add_argument('--silence-pad', type=float, default=0.2, help='Padding to protect audio edges (s)')
    silence_parser.add_argument('--output', '-o', required=True, help='Output video path')
    silence_parser.set_defaults(func=cmd_speed_silence)

    # vg edit concat
    concat_parser = edit_sub.add_parser('concat', help='Concatenate videos')
    concat_parser.add_argument('--videos', required=True, help='Comma-separated video paths')
    concat_parser.add_argument('--output', '-o', required=True, help='Output video path')
    concat_parser.set_defaults(func=cmd_concat)

    # vg edit speed-gaps (NEW - the right way to speed up videos with voiceover)
    gaps_parser = edit_sub.add_parser('speed-gaps', help='Speed up gaps between voiceover segments (preserves voiceover at normal speed)')
    gaps_parser.add_argument('--video', required=True, help='Input video path')
    gaps_parser.add_argument('--placements', help='INTERNAL: JSON from vg compose distribute output. DO NOT create manually. Use --request + --timeline + --audio-dir instead.')
    gaps_parser.add_argument('--request', help='Request markdown file with voiceover segments (required if no --placements)')
    gaps_parser.add_argument('--timeline', help='Timeline markdown file with markers (required if no --placements)')
    gaps_parser.add_argument('--audio-dir', help='Directory containing audio files (required if no --placements)')
    gaps_parser.add_argument('--factor', type=float, default=3.0, help='Speed factor for gaps (default: 3.0)')
    gaps_parser.add_argument('--trim-offset', type=float, default=0.0, help='Seconds trimmed from video start (adjusts timeline)')
    gaps_parser.add_argument('--min-gap', type=float, default=2.0, help='Minimum gap duration to speed up (default: 2.0s)')
    gaps_parser.add_argument('--output', '-o', required=True, help='Output video path')
    gaps_parser.set_defaults(func=cmd_speed_gaps)

def cmd_trim(args) -> dict:
    """Handle vg edit trim command."""
    return trim_video(
        input_path=args.video,
        output_path=args.output,
        start=args.start,
        end=args.end
    )

def cmd_cut(args) -> dict:
    """Handle vg edit cut command."""
    return cut_video(
        input_path=args.video,
        output_path=args.output,
        cuts=args.cuts
    )

def cmd_speed(args) -> dict:
    """Handle vg edit speed command."""
    range_start = None
    range_end = None
    if args.range:
        try:
            start_str, end_str = args.range.split('-', 1)
            range_start = float(start_str.strip())
            range_end = float(end_str.strip())
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid range format: {args.range}. Use 'start-end'",
                "code": "VALIDATION"
            }

    return speed_video(
        input_path=args.video,
        output_path=args.output,
        factor=args.factor,
        range_start=range_start,
        range_end=range_end
    )

def cmd_concat(args) -> dict:
    """Handle vg edit concat command."""
    # Parse comma-separated video paths
    video_paths = [p.strip() for p in args.videos.split(',') if p.strip()]
    if len(video_paths) < 2:
        return {
            "success": False,
            "error": "Need at least 2 videos to concatenate",
            "code": "VALIDATION"
        }

    return concat_videos(
        input_paths=video_paths,
        output_path=args.output
    )


def cmd_speed_silence(args) -> dict:
    """Handle vg edit speed-silence command."""
    return speed_silence(
        input_path=args.video,
        output_path=args.output,
        factor=args.factor,
        silence_db=args.silence_db,
        min_silence=args.min_silence,
        silence_pad=args.silence_pad
    )


def cmd_speed_gaps(args) -> dict:
    """Handle vg edit speed-gaps command.
    
    This is the CORRECT way to speed up videos with voiceover:
    - Only speeds up gaps between voiceover segments
    - Preserves voiceover audio at normal speed
    - Uses actual audio placements (best) or timeline markers
    """
    import json
    
    # Load placements from JSON file if provided
    audio_placements = None
    if args.placements:
        with open(args.placements, 'r') as f:
            audio_placements = json.load(f)
    
    # Validate: need either placements or request+timeline+audio_dir
    if not audio_placements and not (args.request and args.timeline and args.audio_dir):
        return {
            "success": False,
            "error": "Either --placements OR (--request + --timeline + --audio-dir) required",
            "code": "VALIDATION"
        }
    
    return speed_gaps(
        input_path=args.video,
        output_path=args.output,
        request_path=args.request,
        timeline_path=args.timeline,
        audio_dir=args.audio_dir,
        factor=args.factor,
        trim_offset=args.trim_offset,
        min_gap=args.min_gap,
        audio_placements=audio_placements
    )