"""
vg audio commands

Audio generation and processing operations.
"""

import argparse
from pathlib import Path

from vg_tts import tts_with_json_output, batch_tts
from vg_common import validate_env_for_command

def register(subparsers):
    """Register audio commands."""
    audio_parser = subparsers.add_parser('audio', help='Audio operations')
    audio_sub = audio_parser.add_subparsers(dest='audio_command')

    # vg audio tts
    tts_parser = audio_sub.add_parser('tts', help='Generate speech from text')
    tts_parser.add_argument('--text', required=True, help='Text or path to text file')
    tts_parser.add_argument('--voice', default='21m00Tcm4TlvDq8ikWAM', help='Voice ID (ElevenLabs)')
    tts_parser.add_argument('--output', '-o', required=True, help='Output audio path')
    tts_parser.add_argument('--run-id', help='Run ID to group assets together')
    tts_parser.add_argument('--no-cache', action='store_true', help='Skip cache')
    tts_parser.set_defaults(func=cmd_tts)

    # vg audio batch
    batch_parser = audio_sub.add_parser('batch', help='Batch TTS generation')
    batch_parser.add_argument('--segments', required=True, help='JSON file with segments')
    batch_parser.add_argument('--voice', default='21m00Tcm4TlvDq8ikWAM', help='Voice ID')
    batch_parser.add_argument('--output-dir', '-o', required=True, help='Output directory')
    batch_parser.set_defaults(func=cmd_batch)

    # vg audio mix
    mix_parser = audio_sub.add_parser('mix', help='Mix/concatenate multiple audio tracks')
    mix_parser.add_argument('--tracks', required=True, help='Comma-separated audio file paths')
    mix_parser.add_argument('--output', '-o', required=True, help='Output audio path')
    mix_parser.add_argument('--run-id', help='Run ID to group assets together')
    mix_parser.add_argument('--mode', default='concat', choices=['concat', 'overlay'], help='Mix mode')
    mix_parser.set_defaults(func=cmd_mix)

def cmd_tts(args) -> dict:
    """Handle vg audio tts command."""
    from datetime import datetime
    from project_paths import run_paths

    # Handle text input (string or file)
    text = args.text
    if Path(text).exists():
        text = Path(text).read_text()

    # Determine output path
    output_path = Path(args.output)
    
    if output_path.is_absolute():
        # Use absolute path as-is
        output_path.parent.mkdir(parents=True, exist_ok=True)
    elif hasattr(args, 'run_id') and args.run_id:
        # Use provided run_id to keep assets together
        run_paths_obj = run_paths(args.run_id)
        audio_dir = run_paths_obj.audio_dir
        audio_dir.mkdir(parents=True, exist_ok=True)
        output_path = audio_dir / args.output
    else:
        # No run_id provided - use output path directly in current dir or create minimal structure
        output_path.parent.mkdir(parents=True, exist_ok=True)

    return tts_with_json_output(
        text=text,
        output_path=output_path,
        voice_id=args.voice,
        use_cache=not args.no_cache
    )

def cmd_batch(args) -> dict:
    """Handle vg audio batch command."""
    # Validate environment
    env_check = validate_env_for_command("audio.tts")
    if not env_check["success"]:
        return env_check

    # Load segments
    try:
        import json
        with open(args.segments, 'r') as f:
            segments = json.load(f)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to load segments file: {e}",
            "code": "VALIDATION"
        }

    return batch_tts(
        segments=segments,
        output_dir=Path(args.output_dir),
        voice_id=args.voice
    )

def cmd_mix(args) -> dict:
    """Handle vg audio mix command - combine multiple audio tracks."""
    import subprocess
    import shutil
    from project_paths import run_paths

    try:
        # Parse track list
        tracks = [t.strip() for t in args.tracks.split(',')]
        
        # Validate all tracks exist
        for track in tracks:
            if not Path(track).exists():
                return {
                    "success": False,
                    "error": f"Audio track not found: {track}",
                    "code": "FILE_NOT_FOUND"
                }

        # Determine output path
        output_path = Path(args.output)
        
        if output_path.is_absolute():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        elif hasattr(args, 'run_id') and args.run_id:
            # Use provided run_id
            run_paths_obj = run_paths(args.run_id)
            run_paths_obj.audio_dir.mkdir(parents=True, exist_ok=True)
            output_path = run_paths_obj.audio_dir / args.output
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Find ffmpeg
        ffmpeg = Path(__file__).parent.parent.parent.parent / "node_modules" / "ffmpeg-static" / "ffmpeg"
        if not ffmpeg.exists():
            ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return {
                "success": False,
                "error": "ffmpeg not found",
                "code": "CONFIG_ERROR"
            }

        if args.mode == 'concat':
            # Create concat list file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for track in tracks:
                    f.write(f"file '{Path(track).absolute()}'\n")
                concat_file = f.name

            # Concatenate audio files
            cmd = [
                str(ffmpeg), "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:a", "libmp3lame",
                "-b:a", "128k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            Path(concat_file).unlink()  # Cleanup temp file

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"FFmpeg concat failed: {result.stderr[:300]}",
                    "code": "PROCESSING_ERROR"
                }

        # Get output info
        size = output_path.stat().st_size

        return {
            "success": True,
            "audio": str(output_path),
            "tracks_combined": len(tracks),
            "mode": args.mode,
            "size": size,
            "tracks": tracks
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNEXPECTED_ERROR"
        }