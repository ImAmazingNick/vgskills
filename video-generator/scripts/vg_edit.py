"""
Video editing functionality for vg CLI.

Wraps video_editor.py for CLI integration.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import shutil

from video_editor import edit_video, get_ffmpeg, extract_segment, concatenate_segments, get_video_duration
from vg_common import VGError, classify_error, get_suggestion, get_duration

def trim_video(
    input_path: str,
    output_path: str,
    start: float,
    end: Optional[float] = None
) -> dict:
    """
    Trim video from start to end time.
    """
    try:
        video = Path(input_path)
        output = Path(output_path)

        # Validate inputs
        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")

        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        # Get video duration to validate trim times
        original_duration = get_duration(video)
        if start >= original_duration:
            raise ValueError(f"Start time {start}s is beyond video duration {original_duration}s")

        if end is not None and end <= start:
            raise ValueError(f"End time {end}s must be greater than start time {start}s")

        # Calculate trim_end for the edit_video function
        # edit_video expects trim_end as seconds to trim from end, not absolute time
        trim_end = 0
        if end is not None:
            if end > original_duration:
                raise ValueError(f"End time {end}s is beyond video duration {original_duration}s")
            trim_end = original_duration - end

        # Perform the edit
        result_path = edit_video(
            input_path=input_path,
            output_path=output_path,
            trim_start=start,
            trim_end=trim_end
        )

        # Get final duration
        final_duration = get_duration(Path(result_path))

        return {
            "success": True,
            "video": str(result_path),
            "duration": final_duration,
            "duration_s": final_duration,  # Alias for agentic workflows
            "size": Path(result_path).stat().st_size,
            "operation": "trim",
            "trim_start": start,
            "trim_end": end,
            "original_duration": original_duration,
            "original_duration_s": original_duration,  # Alias for agentic workflows
            # AGENTIC: AI uses this to adjust placements after trim
            "adjustment": {
                "type": "offset",
                "seconds": -start  # Subtract trim_start from all original times
            }
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def cut_video(
    input_path: str,
    output_path: str,
    cuts: str  # Format: "start1-end1,start2-end2"
) -> dict:
    """
    Cut out sections from video.
    """
    try:
        video = Path(input_path)
        output = Path(output_path)

        # Validate inputs
        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")

        # Parse cuts string
        cut_ranges = []
        for cut_range in cuts.split(','):
            if '-' not in cut_range:
                raise ValueError(f"Invalid cut range format: {cut_range}. Use 'start-end'")
            start_str, end_str = cut_range.split('-', 1)
            try:
                start = float(start_str.strip())
                end = float(end_str.strip())
                if start >= end:
                    raise ValueError(f"Start time {start} must be less than end time {end}")
                cut_ranges.append((start, end))
            except ValueError as e:
                raise ValueError(f"Invalid time values in cut range '{cut_range}': {e}")

        # Normalize and sort cut ranges
        cut_ranges = sorted(cut_ranges, key=lambda x: x[0])
        merged_cuts = []
        for start, end in cut_ranges:
            if not merged_cuts or start > merged_cuts[-1][1]:
                merged_cuts.append([start, end])
            else:
                merged_cuts[-1][1] = max(merged_cuts[-1][1], end)

        original_duration = get_duration(video)
        for start_cut, end_cut in merged_cuts:
            if start_cut >= original_duration or end_cut > original_duration:
                raise ValueError("Cut range exceeds video duration")

        # Build keep segments (inverse of cuts)
        keep_segments = []
        current_start = 0.0
        for start_cut, end_cut in merged_cuts:
            if current_start < start_cut:
                keep_segments.append((current_start, start_cut))
            current_start = max(current_start, end_cut)
        if current_start < original_duration:
            keep_segments.append((current_start, original_duration))

        if not keep_segments:
            return {
                "success": False,
                "error": "All content was removed by cuts",
                "code": "VALIDATION",
                "suggestion": "Adjust cut ranges to leave some content"
            }

        # Use video_editor helpers for precise cuts and concatenation
        ffmpeg = get_ffmpeg()
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Single keep segment -> direct extract
        if len(keep_segments) == 1:
            start_s, end_s = keep_segments[0]
            result_path = extract_segment(
                ffmpeg=ffmpeg,
                input_path=input_path,
                output_path=str(output),
                start_s=start_s,
                end_s=end_s,
                speed=1.0
            )
            return {
                "success": True,
                "video": str(result_path),
                "duration": get_duration(Path(result_path)),
                "size": Path(result_path).stat().st_size,
                "operation": "cut",
                "cut_ranges": cuts,
                "kept_segments": keep_segments,
                "original_duration": original_duration
            }

        # Multiple keep segments -> extract then concatenate
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        segment_files = []
        total_keep_duration = 0.0
        try:
            for i, (start_s, end_s) in enumerate(keep_segments):
                seg_file = str(temp_dir / f"keep_{i:03d}.mp4")
                extract_segment(
                    ffmpeg=ffmpeg,
                    input_path=input_path,
                    output_path=seg_file,
                    start_s=start_s,
                    end_s=end_s,
                    speed=1.0
                )
                segment_files.append(seg_file)
                total_keep_duration += (end_s - start_s)

            concatenate_segments(
                ffmpeg=ffmpeg,
                segments=segment_files,
                output_path=str(output),
                expected_duration=total_keep_duration
            )
        finally:
            for f in segment_files:
                Path(f).unlink(missing_ok=True)
            temp_dir.rmdir()

        return {
            "success": True,
            "video": str(output),
            "duration": get_duration(output),
            "size": output.stat().st_size,
            "operation": "cut",
            "cut_ranges": cuts,
            "kept_segments": keep_segments,
            "original_duration": original_duration
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def speed_video(
    input_path: str,
    output_path: str,
    factor: float,
    range_start: Optional[float] = None,
    range_end: Optional[float] = None
) -> dict:
    """
    Change video speed for whole video or a section.
    """
    try:
        video = Path(input_path)
        output = Path(output_path)

        # Validate inputs
        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")

        if factor <= 0:
            raise ValueError("Speed factor must be positive")

        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        # Prepare speed sections
        speed_sections = []
        if range_start is not None and range_end is not None:
            speed_sections = [{
                "start_s": range_start,
                "end_s": range_end,
                "speed": factor
            }]
        # If no range specified, speed_sections remains empty and edit_video applies to whole video

        # Perform the edit
        result_path = edit_video(
            input_path=input_path,
            output_path=output_path,
            speed_sections=speed_sections
        )

        # Get final duration
        final_duration = get_duration(Path(result_path))
        original_duration = get_duration(video)

        return {
            "success": True,
            "video": str(result_path),
            "duration": final_duration,
            "size": Path(result_path).stat().st_size,
            "operation": "speed",
            "speed_factor": factor,
            "range_start": range_start,
            "range_end": range_end,
            "original_duration": original_duration
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }


def speed_silence(
    input_path: str,
    output_path: str,
    factor: float = 3.0,
    silence_db: float = -35.0,
    min_silence: float = 0.5,
    silence_pad: float = 0.2,
    protected_ranges: Optional[List[tuple]] = None
) -> dict:
    """
    Speed up silent sections of a video by a factor.
    
    Args:
        input_path: Input video path
        output_path: Output video path
        factor: Speed factor for silent sections
        silence_db: Silence threshold in dB (default: -35.0)
        min_silence: Minimum silence duration in seconds (default: 0.5)
        silence_pad: Padding around silence in seconds (default: 0.2)
        protected_ranges: List of (start, end) tuples for audio segments to protect
    
    Returns:
        Dict with success status and operation info
    """
    try:
        video = Path(input_path)
        output = Path(output_path)

        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")
        output.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg = get_ffmpeg()
        duration = get_video_duration(ffmpeg, str(video))

        # Detect silence intervals using ffmpeg silencedetect
        import subprocess
        cmd = [
            ffmpeg,
            "-i", str(video),
            "-af", f"silencedetect=noise={silence_db}dB:d={min_silence}",
            "-f", "null",
            "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        stderr = result.stderr or ""

        silence_intervals = []
        silence_start = None
        for line in stderr.splitlines():
            if "silence_start" in line:
                try:
                    silence_start = float(line.split("silence_start:")[1].strip())
                except Exception:
                    silence_start = None
            elif "silence_end" in line:
                try:
                    end_part = line.split("silence_end:")[1]
                    end_value = end_part.split("|")[0].strip()
                    silence_end = float(end_value)
                except Exception:
                    silence_end = None
                if silence_start is not None and silence_end is not None:
                    silence_intervals.append((silence_start, silence_end))
                    silence_start = None

        # If trailing silence without end, close at duration
        if silence_start is not None:
            silence_intervals.append((silence_start, duration))

        if not silence_intervals:
            return {
                "success": True,
                "video": str(video),
                "duration": duration,
                "size": video.stat().st_size,
                "operation": "speed_silence",
                "silent_sections": 0,
                "note": "No silence detected; video unchanged"
            }

        # Merge overlapping/adjacent intervals
        silence_intervals.sort(key=lambda x: x[0])
        merged = []
        for start, end in silence_intervals:
            # Pad silence to avoid clipping adjacent audio.
            padded_start = max(0.0, start + silence_pad)
            padded_end = max(0.0, end - silence_pad)
            if padded_end <= padded_start:
                continue
            start = padded_start
            end = padded_end
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        # Filter out silence intervals that overlap with protected audio segments
        if protected_ranges:
            filtered_merged = []
            for silence_start, silence_end in merged:
                keep_interval = True
                
                # Check if this silence overlaps with any protected range
                for audio_start, audio_end in protected_ranges:
                    # Add extra padding to be safe (1 second before and after audio)
                    protected_start = audio_start - 1.0
                    protected_end = audio_end + 1.0
                    
                    # Check for overlap
                    if not (silence_end <= protected_start or silence_start >= protected_end):
                        # Overlap detected - skip this silence interval
                        keep_interval = False
                        print(f"⚠️  Skipping silence interval {silence_start:.1f}s-{silence_end:.1f}s (overlaps with audio)")
                        break
                
                if keep_interval:
                    filtered_merged.append([silence_start, silence_end])
            
            merged = filtered_merged
            print(f"✅ Protected {len(protected_ranges)} audio segment(s) from speed-up")

        speed_sections = [
            {"start_s": s, "end_s": e, "speed": factor}
            for s, e in merged
            if e > s
        ]

        result_path = edit_video(
            input_path=str(video),
            output_path=str(output),
            speed_sections=speed_sections
        )

        final_duration = get_video_duration(ffmpeg, str(output))

        return {
            "success": True,
            "video": str(result_path),
            "duration": final_duration,
            "size": Path(result_path).stat().st_size,
            "operation": "speed_silence",
            "silent_sections": len(speed_sections),
            "speed_factor": factor,
            "silence_pad_s": silence_pad,
            "min_silence_s": min_silence
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def get_audio_duration(audio_path: Path) -> float:
    """Get duration of an audio file in seconds."""
    ffmpeg = get_ffmpeg()
    import subprocess
    cmd = [ffmpeg, "-i", str(audio_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stderr.split('\n'):
        if 'Duration' in line:
            # Format: Duration: 00:00:08.80, ...
            match = line.split('Duration:')[1].split(',')[0].strip()
            parts = match.split(':')
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    return 0.0


def calculate_voiceover_placements(
    request_path: str,
    timeline_path: str,
    audio_dir: str,
    trim_offset: float = 0.0
) -> List[tuple]:
    """
    Calculate the time ranges where voiceover audio is playing.
    
    Args:
        request_path: Path to request markdown file with voiceover segments
        timeline_path: Path to timeline markdown file with markers
        audio_dir: Directory containing audio files (segment_id.mp3)
        trim_offset: Seconds trimmed from start of video (to adjust times)
    
    Returns:
        List of (start_time, end_time) tuples representing voiceover ranges
    """
    from vg_core_utils.md_parser import parse_voiceover_segments_from_md
    from vg_core_utils.timeline import load_timeline_markers
    
    # Parse voiceover segments from request
    with open(request_path, 'r') as f:
        request_content = f.read()
    segments = parse_voiceover_segments_from_md(request_content)
    
    # Load timeline markers
    markers = load_timeline_markers(Path(timeline_path))
    
    # Calculate placement for each segment
    placements = []
    audio_dir_path = Path(audio_dir)
    
    for seg in segments:
        seg_id = seg.get("id")
        anchor = seg.get("anchor")
        offset = seg.get("offset_s", 0.0)
        
        # Find anchor in markers
        if anchor not in markers:
            print(f"⚠️  Warning: Anchor '{anchor}' not found in timeline, skipping segment '{seg_id}'")
            continue
        
        # Calculate start time (adjusted for trim offset)
        start_time = markers[anchor] + offset - trim_offset
        
        # Get audio duration
        audio_file = audio_dir_path / f"{seg_id}.mp3"
        if not audio_file.exists():
            print(f"⚠️  Warning: Audio file not found: {audio_file}, skipping segment '{seg_id}'")
            continue
        
        duration = get_audio_duration(audio_file)
        end_time = start_time + duration
        
        # Only include if within video bounds (after trim)
        if end_time > 0:
            placements.append((max(0, start_time), end_time))
            print(f"   📢 Voiceover '{seg_id}': {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)")
    
    # Sort by start time
    placements.sort(key=lambda x: x[0])
    return placements


def _calculate_time_mapping(
    gaps: List[Tuple[float, float]],
    voiceover_ranges: List[Tuple[float, float]],
    video_duration: float,
    factor: float
) -> dict:
    """
    Calculate time mapping from original video to sped-up video.
    
    Returns a dict with:
    - breakpoints: list of (original_time, new_time) pairs
    - map_time(t): function to convert original time to new time
    
    This is essential for placing audio on the sped-up video correctly.
    """
    # Build a list of all segment boundaries sorted by time
    # Each segment is either a gap (sped up) or a voiceover (normal speed)
    segments = []
    
    # Add gaps
    for start, end in gaps:
        segments.append({"start": start, "end": end, "type": "gap", "speed": factor})
    
    # Add voiceover ranges
    for start, end in voiceover_ranges:
        segments.append({"start": start, "end": end, "type": "voice", "speed": 1.0})
    
    # Sort by start time
    segments.sort(key=lambda x: x["start"])
    
    # Merge overlapping/adjacent segments and fill gaps
    # Build complete timeline from 0 to video_duration
    all_times = sorted(set([0, video_duration] + [s["start"] for s in segments] + [s["end"] for s in segments]))
    
    # Calculate new time for each original time
    breakpoints = [(0.0, 0.0)]
    current_new_time = 0.0
    
    for i in range(len(all_times) - 1):
        orig_start = all_times[i]
        orig_end = all_times[i + 1]
        orig_duration = orig_end - orig_start
        
        if orig_duration <= 0:
            continue
            
        # Check if this segment is a gap or voice
        is_gap = any(
            g[0] <= orig_start and g[1] >= orig_end 
            for g in gaps
        )
        
        if is_gap:
            new_duration = orig_duration / factor
        else:
            new_duration = orig_duration
        
        current_new_time += new_duration
        breakpoints.append((orig_end, current_new_time))
    
    return {
        "breakpoints": breakpoints,
        "original_duration": video_duration,
        "new_duration": current_new_time,
        "factor": factor
    }


def map_time_with_breakpoints(original_time: float, breakpoints: List[Tuple[float, float]]) -> float:
    """
    Map an original timestamp to the new timestamp using breakpoints.
    
    Args:
        original_time: Time in original video
        breakpoints: List of (original_time, new_time) pairs
        
    Returns:
        Corresponding time in sped-up video
    """
    if not breakpoints:
        return original_time
    
    # Find the two breakpoints that bracket original_time
    prev_orig, prev_new = breakpoints[0]
    
    for orig, new in breakpoints[1:]:
        if original_time <= orig:
            # Interpolate between prev and current
            if orig == prev_orig:
                return new
            ratio = (original_time - prev_orig) / (orig - prev_orig)
            return prev_new + ratio * (new - prev_new)
        prev_orig, prev_new = orig, new
    
    # Beyond last breakpoint - extrapolate (shouldn't happen normally)
    return prev_new


def speed_gaps(
    input_path: str,
    output_path: str,
    request_path: str = None,
    timeline_path: str = None,
    audio_dir: str = None,
    factor: float = 3.0,
    trim_offset: float = 0.0,
    min_gap: float = 2.0,
    audio_placements: List[dict] = None
) -> dict:
    """
    Speed up gaps between voiceover segments while preserving voiceover at normal speed.
    
    This is the proper way to shorten videos - only speed up sections without narration.
    
    Args:
        input_path: Input video path
        output_path: Output video path  
        request_path: Path to request markdown with voiceover segments (optional if audio_placements provided)
        timeline_path: Path to timeline markdown with markers (optional if audio_placements provided)
        audio_dir: Directory containing audio files (optional if audio_placements provided)
        factor: Speed factor for gaps (default: 3.0)
        trim_offset: Seconds trimmed from start (to adjust timeline markers)
        min_gap: Minimum gap duration to speed up (default: 2.0s)
        audio_placements: ACTUAL placements from distribute - use this instead of recalculating!
                         Format: [{"id": "intro", "start_time": 30.5, "duration": 8.2}, ...]
    
    Returns:
        Dict with success status and operation info
    """
    try:
        video = Path(input_path)
        output = Path(output_path)

        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")
        
        # Validate: need either audio_placements OR (request + timeline + audio_dir)
        if audio_placements:
            # Use ACTUAL placements from distribute - most accurate!
            print("📍 Using actual audio placements from distribute")
        else:
            # Fall back to calculating from request/timeline
            if not request_path or not Path(request_path).exists():
                raise FileNotFoundError(f"Request file not found: {request_path}")
            if not timeline_path or not Path(timeline_path).exists():
                raise FileNotFoundError(f"Timeline file not found: {timeline_path}")
            if not audio_dir or not Path(audio_dir).exists():
                raise FileNotFoundError(f"Audio directory not found: {audio_dir}")
            
        output.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg = get_ffmpeg()
        video_duration = get_video_duration(ffmpeg, str(video))
        
        print(f"📹 Input: {input_path}")
        print(f"⏱️  Duration: {video_duration:.1f}s")
        print(f"✂️  Trim offset: {trim_offset}s")

        # Get voiceover ranges - either from actual placements or calculate
        if audio_placements:
            # Convert placements to ranges: (start, end)
            print(f"\n📍 Using {len(audio_placements)} actual audio placements:")
            voiceover_ranges = []
            for p in audio_placements:
                start = p.get("start_time", p.get("start", 0))
                duration = p.get("duration", p.get("duration_s", 0))
                end = start + duration
                voiceover_ranges.append((start, end))
                print(f"   🔊 {p.get('id', '?')}: {start:.1f}s - {end:.1f}s ({duration:.1f}s)")
            voiceover_ranges.sort(key=lambda x: x[0])
        else:
            print(f"\n🔍 Calculating voiceover placements...")
            voiceover_ranges = calculate_voiceover_placements(
                request_path=request_path,
                timeline_path=timeline_path,
                audio_dir=audio_dir,
                trim_offset=trim_offset
            )
        
        if not voiceover_ranges:
            return {
                "success": False,
                "error": "No voiceover segments found. Cannot determine gaps.",
                "code": "VALIDATION",
                "suggestion": "Provide audio_placements or ensure request file has voiceover segments"
            }
        
        # Calculate gaps (sections between voiceover segments)
        print(f"\n📊 Finding gaps between {len(voiceover_ranges)} voiceover segment(s)...")
        gaps = []
        
        # Gap before first voiceover
        first_start = voiceover_ranges[0][0]
        if first_start > min_gap:
            gaps.append((0, first_start))
            print(f"   🔇 Gap at start: 0.0s - {first_start:.1f}s")
        
        # Gaps between voiceover segments
        for i in range(len(voiceover_ranges) - 1):
            current_end = voiceover_ranges[i][1]
            next_start = voiceover_ranges[i + 1][0]
            gap_duration = next_start - current_end
            
            if gap_duration >= min_gap:
                gaps.append((current_end, next_start))
                print(f"   🔇 Gap between segments: {current_end:.1f}s - {next_start:.1f}s ({gap_duration:.1f}s)")
        
        # Gap after last voiceover
        last_end = voiceover_ranges[-1][1]
        if video_duration - last_end > min_gap:
            gaps.append((last_end, video_duration))
            print(f"   🔇 Gap at end: {last_end:.1f}s - {video_duration:.1f}s")
        
        if not gaps:
            # No gaps to speed up - just copy the file
            import shutil
            shutil.copy2(video, output)
            return {
                "success": True,
                "video": str(output),
                "duration": video_duration,
                "size": output.stat().st_size,
                "operation": "speed_gaps",
                "gaps_found": 0,
                "note": "No gaps long enough to speed up; video unchanged"
            }
        
        # Calculate expected savings
        total_gap_duration = sum(end - start for start, end in gaps)
        expected_savings = total_gap_duration * (1 - 1/factor)
        expected_duration = video_duration - expected_savings
        
        print(f"\n📊 Speed-up summary:")
        print(f"   Total gap time: {total_gap_duration:.1f}s")
        print(f"   Voiceover time: {video_duration - total_gap_duration:.1f}s (preserved at normal speed)")
        print(f"   Speed factor: {factor}x for gaps only")
        print(f"   Expected duration: {expected_duration:.1f}s (saving {expected_savings:.1f}s)")
        
        # Create speed sections for gaps only
        speed_sections = [
            {"start_s": start, "end_s": end, "speed": factor}
            for start, end in gaps
        ]
        
        # Apply speed changes
        print(f"\n🎬 Processing {len(gaps)} gap section(s)...")
        result_path = edit_video(
            input_path=str(video),
            output_path=str(output),
            speed_sections=speed_sections
        )

        final_duration = get_video_duration(ffmpeg, str(output))
        actual_savings = video_duration - final_duration

        # Calculate time mapping: original_time -> new_time
        # This is essential for placing audio on the sped-up video
        time_mapping = _calculate_time_mapping(
            gaps=gaps,
            voiceover_ranges=voiceover_ranges,
            video_duration=video_duration,
            factor=factor
        )

        print(f"\n✅ Speed-gaps complete!")
        print(f"   Original: {video_duration:.1f}s")
        print(f"   Final: {final_duration:.1f}s")
        print(f"   Saved: {actual_savings:.1f}s ({actual_savings/video_duration*100:.0f}% shorter)")
        
        # Build simplified time_map for AI: list of [original_time, new_time] pairs
        # AI can look up any original time to find its position in the sped-up video
        time_map = time_mapping.get("breakpoints", [])
        
        # Calculate scale factor for simple approximation (if AI doesn't want to use time_map)
        scale_factor = final_duration / video_duration if video_duration > 0 else 1.0
        
        return {
            "success": True,
            "video": str(result_path),
            "duration": final_duration,
            "duration_s": final_duration,  # Alias for agentic workflows
            "size": Path(result_path).stat().st_size,
            "operation": "speed_gaps",
            "gaps_found": len(gaps),
            "gaps_total_duration": total_gap_duration,
            "voiceover_segments": len(voiceover_ranges),
            "speed_factor": factor,
            "original_duration": video_duration,
            "original_duration_s": video_duration,  # Alias for agentic workflows
            "time_saved": actual_savings,
            # AGENTIC: AI uses these to adjust placements after speed-gaps
            "time_map": time_map,  # [[orig_time, new_time], ...] - precise mapping
            "scale_factor": scale_factor,  # Simple approximation: new_time = orig_time * scale_factor
            "time_mapping": time_mapping  # Full mapping object (legacy, for compatibility)
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }


def concat_videos(
    input_paths: List[str],
    output_path: str
) -> dict:
    """
    Concatenate multiple videos.
    """
    try:
        videos = [Path(p) for p in input_paths]
        output = Path(output_path)

        # Validate inputs
        for video in videos:
            if not video.exists():
                raise FileNotFoundError(f"Video file not found: {video}")

        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        # For now, implement simple concatenation
        # This is a basic implementation - could be enhanced with proper format handling
        if len(videos) < 2:
            raise ValueError("Need at least 2 videos to concatenate")

        # Create a temporary concat file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for video in videos:
                f.write(f"file '{video.absolute()}'\n")
            concat_file = f.name

        # Get ffmpeg using consolidated function
        from vg_common import require_ffmpeg
        
        ffmpeg = require_ffmpeg()

        # Use ffmpeg concat
        cmd = [
            ffmpeg, "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            str(output)
        ]

        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # Clean up temp file
        Path(concat_file).unlink(missing_ok=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")

        # Get final duration and size
        final_duration = get_duration(output)
        total_size = sum(get_duration(v) for v in videos)

        return {
            "success": True,
            "video": str(output),
            "duration": final_duration,
            "size": output.stat().st_size,
            "operation": "concat",
            "videos_concatenated": len(videos),
            "expected_duration": total_size
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }