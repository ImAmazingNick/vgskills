"""
vg quality commands

Video quality validation, analysis, and optimization.
"""

import argparse
from pathlib import Path

from vg_quality import validate_video, analyze_video, optimize_video

def register(subparsers):
    """Register quality commands."""
    quality_parser = subparsers.add_parser('quality', help='Video quality operations')
    quality_sub = quality_parser.add_subparsers(dest='quality_command')

    # vg quality validate
    validate_parser = quality_sub.add_parser('validate', help='Validate video/audio file')
    validate_parser.add_argument('--file', required=True, help='File to validate')
    validate_parser.set_defaults(func=cmd_validate)

    # vg quality analyze
    analyze_parser = quality_sub.add_parser('analyze', help='Analyze video quality and sync')
    analyze_parser.add_argument('--video', required=True, help='Video file path')
    analyze_parser.add_argument('--audio', help='Audio file path (optional)')
    analyze_parser.set_defaults(func=cmd_analyze)

    # vg quality optimize
    optimize_parser = quality_sub.add_parser('optimize', help='Optimize/compress video')
    optimize_parser.add_argument('--input', required=True, help='Input video path')
    optimize_parser.add_argument('--output', '-o', required=True, help='Output video path')
    optimize_parser.add_argument('--run-id', help='Run ID to group assets together')
    optimize_parser.add_argument('--target-size', type=float, help='Target size in MB')
    optimize_parser.add_argument('--quality', default='high', choices=['high', 'medium', 'low'], help='Quality preset')
    optimize_parser.set_defaults(func=cmd_optimize)

def cmd_validate(args) -> dict:
    """Handle vg quality validate command."""
    return validate_video(args.file)

def cmd_analyze(args) -> dict:
    """Handle vg quality analyze command."""
    return analyze_video(args.video, args.audio)

def cmd_optimize(args) -> dict:
    """Handle vg quality optimize command."""
    from project_paths import run_paths

    # Determine output path
    output_path = Path(args.output)
    
    if output_path.is_absolute():
        # Use absolute path as-is
        output_path.parent.mkdir(parents=True, exist_ok=True)
    elif hasattr(args, 'run_id') and args.run_id:
        # Use provided run_id to keep assets together
        run_paths_obj = run_paths(args.run_id)
        run_paths_obj.run_dir.mkdir(parents=True, exist_ok=True)
        output_path = run_paths_obj.run_dir / args.output
    else:
        # No run_id - use output path directly
        output_path.parent.mkdir(parents=True, exist_ok=True)

    return optimize_video(
        input_path=args.input,
        output_path=str(output_path),
        target_size_mb=args.target_size,
        quality=args.quality
    )