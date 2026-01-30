#!/usr/bin/env python3
"""
Video Editor - Trim, Cut, and Speed Up Video Sections

Supports:
- Trimming start/end of video
- Cutting out sections
- Speeding up/slowing down sections
- Preserving audio sync (adjusts pitch for speed changes)

Usage:
    python video_editor.py input.mp4 output.mp4 --operations operations.json
    python video_editor.py input.mp4 output.mp4 --trim-start 5 --speed-section 37,135,3.0
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional

from vg_common import require_ffmpeg


def get_ffmpeg() -> str:
    """Get path to ffmpeg binary (uses consolidated resolution)."""
    return require_ffmpeg()


def get_video_duration(ffmpeg: str, video_path: str) -> float:
    """Get video duration in seconds."""
    result = subprocess.run(
        [ffmpeg, "-i", video_path],
        capture_output=True, text=True
    )
    
    import re
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if match:
        hours, minutes, seconds = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    
    raise RuntimeError(f"Could not determine duration of {video_path}")


def timestamp_to_seconds(ts: str) -> float:
    """Convert timestamp (MM:SS or HH:MM:SS) to seconds."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    else:
        return float(ts)


def seconds_to_timestamp(secs: float) -> str:
    """Convert seconds to MM:SS.ms format."""
    mins = int(secs // 60)
    secs_remain = secs % 60
    return f"{mins:02d}:{secs_remain:05.2f}"


def extract_segment(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    start_s: float,
    end_s: float,
    speed: float = 1.0
) -> str:
    """Extract a segment from video, optionally with speed change.
    
    IMPORTANT FIX: Use -to instead of -t to avoid timing issues with filters.
    Also use trim filter for precise cuts when speed is involved.
    """
    
    duration = end_s - start_s
    
    if speed == 1.0:
        # Simple extraction without speed change - use -to for precise end time
        cmd = [
            ffmpeg, "-y",
            "-ss", str(start_s),
            "-i", input_path,
            "-to", str(duration),  # -to is relative to -ss position
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-avoid_negative_ts", "make_zero",  # Prevent timestamp issues
            output_path
        ]
    else:
        # Speed change with audio pitch correction
        # Use trim filter for precise cutting, then apply speed
        # This prevents duplicate frames at segment boundaries
        
        video_filter = f"setpts=PTS/{speed}"
        
        # Build atempo chain for speeds > 2.0 or < 0.5
        atempo_filters = []
        remaining_speed = speed
        while remaining_speed > 2.0:
            atempo_filters.append("atempo=2.0")
            remaining_speed /= 2.0
        while remaining_speed < 0.5:
            atempo_filters.append("atempo=0.5")
            remaining_speed /= 0.5
        atempo_filters.append(f"atempo={remaining_speed}")
        audio_filter = ",".join(atempo_filters)
        
        # Use trim filter for video and atrim for audio to get precise cuts
        # Then apply speed changes, then reset timestamps
        video_full_filter = f"trim=start={start_s}:end={end_s},setpts=PTS-STARTPTS,{video_filter},setpts=PTS-STARTPTS"
        audio_full_filter = f"atrim=start={start_s}:end={end_s},asetpts=PTS-STARTPTS,{audio_filter},asetpts=PTS-STARTPTS"
        
        cmd = [
            ffmpeg, "-y",
            "-i", input_path,  # No -ss here, use trim filter instead
            "-filter_complex", f"[0:v]{video_full_filter}[v];[0:a]{audio_full_filter}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr[:500]}")
        raise RuntimeError(f"Failed to extract segment")
    
    return output_path


def concatenate_segments(ffmpeg: str, segments: List[str], output_path: str, expected_duration: float = None) -> str:
    """Concatenate multiple video segments.
    
    Args:
        ffmpeg: Path to ffmpeg binary
        segments: List of segment file paths
        output_path: Output file path
        expected_duration: Expected output duration for verification (optional)
    """
    
    # Verify segment durations before concatenation
    total_segment_duration = 0.0
    print(f"\n📊 Verifying {len(segments)} segments before concatenation:")
    for i, seg in enumerate(segments):
        dur = get_video_duration(ffmpeg, seg)
        total_segment_duration += dur
        print(f"   Segment {i+1}: {seconds_to_timestamp(dur)} ({dur:.2f}s)")
    print(f"   Total: {seconds_to_timestamp(total_segment_duration)} ({total_segment_duration:.2f}s)")
    
    # Create concat file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
        concat_file = f.name
    
    try:
        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg concat error: {result.stderr[:500]}")
            raise RuntimeError("Failed to concatenate segments")
    finally:
        Path(concat_file).unlink(missing_ok=True)
    
    # Verify output duration
    actual_duration = get_video_duration(ffmpeg, output_path)
    print(f"\n📊 Output verification:")
    print(f"   Segments total: {seconds_to_timestamp(total_segment_duration)}")
    print(f"   Output duration: {seconds_to_timestamp(actual_duration)}")
    
    if expected_duration:
        diff = abs(actual_duration - expected_duration)
        if diff > 1.0:  # More than 1 second difference
            print(f"   ⚠️  WARNING: Expected {seconds_to_timestamp(expected_duration)}, got {seconds_to_timestamp(actual_duration)}")
            print(f"   ⚠️  Difference: {diff:.2f}s - possible duplicate content!")
        else:
            print(f"   ✅ Duration matches expected ({seconds_to_timestamp(expected_duration)})")
    
    return output_path


def edit_video(
    input_path: str,
    output_path: str,
    trim_start: float = 0,
    trim_end: float = 0,
    speed_sections: List[Dict] = None
) -> str:
    """
    Edit video with trimming and speed changes.
    
    Args:
        input_path: Input video file
        output_path: Output video file
        trim_start: Seconds to trim from start
        trim_end: Seconds to trim from end
        speed_sections: List of dicts with {start_s, end_s, speed}
    """
    
    ffmpeg = get_ffmpeg()
    duration = get_video_duration(ffmpeg, input_path)
    
    print(f"📹 Input: {input_path}")
    print(f"⏱️  Duration: {seconds_to_timestamp(duration)} ({duration:.2f}s)")
    print(f"✂️  Trim start: {trim_start}s, Trim end: {trim_end}s")
    
    effective_start = trim_start
    effective_end = duration - trim_end
    
    if effective_end <= effective_start:
        raise ValueError("Trim values result in zero or negative duration")
    
    # Default: no speed sections
    if not speed_sections:
        speed_sections = []
    
    # Sort speed sections by start time
    speed_sections = sorted(speed_sections, key=lambda x: x["start_s"])
    
    # Build segment list
    segments = []
    min_segment_s = 0.1
    current_pos = effective_start
    
    for i, section in enumerate(speed_sections):
        start_s = max(section["start_s"], effective_start)
        end_s = min(section["end_s"], effective_end)
        speed = section.get("speed", 1.0)
        
        if start_s >= effective_end or end_s <= effective_start:
            continue  # Section outside our range
        
        # Add normal-speed segment before this speed section
        if current_pos < start_s:
            if (start_s - current_pos) >= min_segment_s:
                segments.append({
                    "start_s": current_pos,
                    "end_s": start_s,
                    "speed": 1.0
                })
        
        # Add speed section
        if (end_s - start_s) >= min_segment_s:
            segments.append({
                "start_s": start_s,
                "end_s": end_s,
                "speed": speed
            })
        
        current_pos = end_s
    
    # Add final normal-speed segment
    if current_pos < effective_end:
        if (effective_end - current_pos) >= min_segment_s:
            segments.append({
                "start_s": current_pos,
                "end_s": effective_end,
                "speed": 1.0
            })
    
    if not segments:
        raise ValueError("No segments to process")
    
    print(f"\n📋 Segments to process:")
    total_output_duration = 0
    for i, seg in enumerate(segments):
        seg_duration = seg["end_s"] - seg["start_s"]
        output_duration = seg_duration / seg["speed"]
        total_output_duration += output_duration
        speed_str = f"{seg['speed']}x" if seg['speed'] != 1.0 else "normal"
        print(f"   {i+1}. {seconds_to_timestamp(seg['start_s'])} - {seconds_to_timestamp(seg['end_s'])} "
              f"({seg_duration:.1f}s → {output_duration:.1f}s @ {speed_str})")
    
    print(f"\n📊 Output duration estimate: {seconds_to_timestamp(total_output_duration)} ({total_output_duration:.1f}s)")
    
    # Process segments
    temp_dir = Path(tempfile.mkdtemp())
    segment_files = []
    
    try:
        for i, seg in enumerate(segments):
            print(f"\n🎬 Processing segment {i+1}/{len(segments)}...")
            
            seg_file = str(temp_dir / f"segment_{i:03d}.mp4")
            extract_segment(
                ffmpeg, input_path, seg_file,
                seg["start_s"], seg["end_s"], seg["speed"]
            )
            segment_files.append(seg_file)
            print(f"   ✅ Done")
        
        print(f"\n🔗 Concatenating {len(segment_files)} segments...")
        concatenate_segments(ffmpeg, segment_files, output_path, expected_duration=total_output_duration)
        
        # Verify output
        output_duration = get_video_duration(ffmpeg, output_path)
        output_size = Path(output_path).stat().st_size / 1024 / 1024
        
        # Check for significant duration mismatch (indicates duplicate content bug)
        duration_diff = abs(output_duration - total_output_duration)
        if duration_diff > 2.0:
            print(f"\n⚠️  DURATION MISMATCH DETECTED!")
            print(f"   Expected: {seconds_to_timestamp(total_output_duration)} ({total_output_duration:.1f}s)")
            print(f"   Actual: {seconds_to_timestamp(output_duration)} ({output_duration:.1f}s)")
            print(f"   Difference: {duration_diff:.1f}s")
            print(f"   This may indicate duplicate content. Please verify the output.")
        
        print(f"\n{'='*60}")
        print(f"✅ VIDEO EDITING COMPLETE!")
        print(f"   Output: {output_path}")
        print(f"   Duration: {seconds_to_timestamp(output_duration)} ({output_duration:.1f}s)")
        print(f"   Expected: {seconds_to_timestamp(total_output_duration)} ({total_output_duration:.1f}s)")
        print(f"   Size: {output_size:.1f} MB")
        print(f"   Saved: {duration - output_duration:.1f}s ({(1 - output_duration/duration)*100:.0f}% shorter)")
        print(f"{'='*60}")
        
    finally:
        # Cleanup temp files
        for f in segment_files:
            Path(f).unlink(missing_ok=True)
        temp_dir.rmdir()
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Video Editor - Trim, Cut, Speed Up")
    parser.add_argument("input", help="Input video file")
    parser.add_argument("output", help="Output video file")
    parser.add_argument("--trim-start", type=float, default=0,
                       help="Seconds to trim from start")
    parser.add_argument("--trim-end", type=float, default=0,
                       help="Seconds to trim from end")
    parser.add_argument("--speed-section", action="append", dest="speed_sections",
                       help="Speed section: start,end,speed (e.g., 37,135,3.0)")
    parser.add_argument("--operations", help="JSON file with operations")
    
    args = parser.parse_args()
    
    # Parse speed sections
    speed_sections = []
    
    if args.operations:
        with open(args.operations) as f:
            ops = json.load(f)
            speed_sections = ops.get("speed_sections", [])
            if "trim_start" in ops:
                args.trim_start = ops["trim_start"]
            if "trim_end" in ops:
                args.trim_end = ops["trim_end"]
    
    if args.speed_sections:
        for ss in args.speed_sections:
            parts = ss.split(",")
            if len(parts) == 3:
                speed_sections.append({
                    "start_s": timestamp_to_seconds(parts[0]),
                    "end_s": timestamp_to_seconds(parts[1]),
                    "speed": float(parts[2])
                })
    
    edit_video(
        args.input,
        args.output,
        trim_start=args.trim_start,
        trim_end=args.trim_end,
        speed_sections=speed_sections
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
