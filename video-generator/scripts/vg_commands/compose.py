"""
vg compose commands

Composition operations (sync, overlay, distribute, place).

AGENTIC DESIGN:
- `place`: DUMB executor - AI provides exact times, tool just places audio
- `distribute`: Legacy command with marker matching (for backward compatibility)
"""

import argparse
from pathlib import Path

from vg_compose import sync_audio_video, overlay_video

def register(subparsers):
    """Register compose commands."""
    compose_parser = subparsers.add_parser('compose', help='Video composition operations')
    compose_sub = compose_parser.add_subparsers(dest='compose_command')

    # vg compose sync
    sync_parser = compose_sub.add_parser('sync', help='Sync audio with video (simple mux)')
    sync_parser.add_argument('--video', required=True, help='Video file path')
    sync_parser.add_argument('--audio', required=True, help='Audio file path')
    sync_parser.add_argument('--output', '-o', required=True, help='Output video path')
    sync_parser.add_argument('--run-id', help='Run ID to group assets together')
    sync_parser.add_argument('--timeline', help='Timeline JSON file for advanced sync')
    sync_parser.set_defaults(func=cmd_sync)

    # vg compose place - AGENTIC: AI provides exact times, tool auto-fixes overlaps
    place_parser = compose_sub.add_parser('place', help='Place audio at AI-specified times (auto-fixes overlaps)')
    place_parser.add_argument('--video', required=True, help='Video file path')
    place_parser.add_argument('--audio', action='append', required=True, 
                              help='Audio placement: file.mp3:start_time (can specify multiple)')
    place_parser.add_argument('--output', '-o', required=True, help='Output video path')
    place_parser.add_argument('--no-fix-overlaps', action='store_true',
                              help='Disable automatic overlap fixing (default: fix overlaps with 300ms gaps)')
    place_parser.add_argument('--strict', action='store_true',
                              help='Strict mode: fail on overlaps instead of auto-fixing (recommended for agentic workflows)')
    place_parser.set_defaults(func=cmd_place)

    # vg compose distribute - LEGACY: uses marker matching (for backward compatibility)
    dist_parser = compose_sub.add_parser('distribute', help='Distribute audio segments across video timeline with precise positioning')
    dist_parser.add_argument('--video', required=True, help='Video file path')
    dist_parser.add_argument('--request', '-r', required=True, help='Request file (.md) with voiceover segments and timing markers')
    dist_parser.add_argument('--audio-dir', required=True, help='Directory containing audio segment files')
    dist_parser.add_argument('--output', '-o', required=True, help='Output video path')
    dist_parser.add_argument('--run-id', help='Run ID to group assets together')
    dist_parser.add_argument('--timeline', help='Timeline JSON file with marker timestamps (required for precise positioning)')
    dist_parser.set_defaults(func=cmd_distribute)

    # vg compose overlay
    overlay_parser = compose_sub.add_parser('overlay', help='Overlay video on video')
    overlay_parser.add_argument('--video', required=True, help='Main video file path')
    overlay_parser.add_argument('--overlay', required=True, help='Overlay video file path')
    overlay_parser.add_argument('--output', '-o', required=True, help='Output video path')
    overlay_parser.add_argument('--position', default='bottom-right',
                               choices=['top-left', 'top-right', 'bottom-left', 'bottom-right'],
                               help='Overlay position')
    overlay_parser.add_argument('--size', type=int, default=30, help='Overlay size percentage')
    overlay_parser.set_defaults(func=cmd_overlay)

def cmd_sync(args) -> dict:
    """Handle vg compose sync command."""
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

    return sync_audio_video(
        video_path=args.video,
        audio_path=args.audio,
        output_path=str(output_path),
        timeline_path=args.timeline
    )

def cmd_overlay(args) -> dict:
    """Handle vg compose overlay command."""
    return overlay_video(
        main_video=args.video,
        overlay_video=args.overlay,
        output_path=args.output,
        position=args.position,
        size_percent=args.size
    )


def cmd_place(args) -> dict:
    """
    Handle vg compose place command.
    
    AGENTIC DESIGN: AI provides times, tool auto-fixes overlaps.
    - AI agent calculates exact placement times
    - AI passes them as --audio file:time arguments
    - Tool detects overlaps and fixes with 300ms cascading gaps
    - Use --no-fix-overlaps to disable auto-fix
    
    Usage:
        vg compose place \\
            --video demo.mp4 \\
            --audio intro.mp3:33.6 \\
            --audio prompt1.mp3:107.3 \\
            --audio reveal.mp3:261.3 \\
            -o final.mp4
    """
    import subprocess
    from vg_common import get_ffmpeg, get_duration
    
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        return {"success": False, "error": "ffmpeg not found", "code": "CONFIG_ERROR"}
    
    try:
        video_path = Path(args.video)
        output_path = Path(args.output)
        fix_overlaps = not getattr(args, 'no_fix_overlaps', False)
        strict_mode = getattr(args, 'strict', False)
        
        # Strict mode implies no auto-fix
        if strict_mode:
            fix_overlaps = False
        
        # Validate video exists
        if not video_path.exists():
            return {
                "success": False, 
                "error": f"Video not found: {video_path}", 
                "code": "FILE_NOT_FOUND"
            }
        
        # Parse audio placements: "file.mp3:33.6" -> (file, start_time)
        placements = []
        for audio_spec in args.audio:
            if ':' not in audio_spec:
                return {
                    "success": False,
                    "error": f"Invalid audio format: '{audio_spec}'. Use 'file.mp3:start_time'",
                    "code": "VALIDATION_ERROR"
                }
            
            file_part, time_part = audio_spec.rsplit(':', 1)
            audio_file = Path(file_part)
            
            if not audio_file.exists():
                return {
                    "success": False,
                    "error": f"Audio file not found: {audio_file}",
                    "code": "FILE_NOT_FOUND"
                }
            
            try:
                start_time = float(time_part)
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid time value: '{time_part}' in '{audio_spec}'",
                    "code": "VALIDATION_ERROR"
                }
            
            # Get audio duration
            duration = get_duration(audio_file)
            
            placements.append({
                "file": str(audio_file),
                "start_s": start_time,
                "duration_s": duration,
                "original_start_s": start_time  # Track original for reporting
            })
        
        if not placements:
            return {
                "success": False,
                "error": "No audio placements provided",
                "code": "VALIDATION_ERROR"
            }
        
        # Sort by start time for overlap detection
        placements.sort(key=lambda p: p["start_s"])
        
        # Detect overlaps
        overlaps_detected = []
        if len(placements) > 1:
            for i in range(1, len(placements)):
                prev = placements[i - 1]
                curr = placements[i]
                prev_end = prev["start_s"] + prev["duration_s"]
                
                if curr["start_s"] < prev_end:
                    overlaps_detected.append({
                        "file": Path(curr["file"]).name,
                        "prev_file": Path(prev["file"]).name,
                        "overlap_s": prev_end - curr["start_s"],
                        "curr_start_s": curr["start_s"],
                        "prev_end_s": prev_end
                    })
        
        # Handle overlaps based on mode
        overlaps_fixed = []
        if overlaps_detected and strict_mode:
            # FAIL instead of auto-fix - AI should recalculate
            print(f"\n" + "="*60)
            print(f"❌ STRICT MODE: Overlapping segments detected!")
            print(f"="*60)
            for overlap in overlaps_detected:
                print(f"   {overlap['prev_file']} ends at {overlap['prev_end_s']:.1f}s")
                print(f"   {overlap['file']} starts at {overlap['curr_start_s']:.1f}s")
                print(f"   Overlap: {overlap['overlap_s']:.1f}s")
            print(f"\n   💡 AI should recalculate placement times")
            print(f"="*60 + "\n")
            
            return {
                "success": False,
                "error": f"Overlapping segments detected. AI should recalculate times.",
                "code": "OVERLAP_ERROR",
                "overlaps": overlaps_detected,
                "suggestion": "Recalculate placement times with proper gaps, or remove --strict flag"
            }
        
        elif overlaps_detected and fix_overlaps:
            # Auto-fix overlaps with cascading 300ms gaps
            for i in range(1, len(placements)):
                prev = placements[i - 1]
                curr = placements[i]
                prev_end = prev["start_s"] + prev["duration_s"]
                
                if curr["start_s"] < prev_end:
                    old_start = curr["start_s"]
                    new_start = prev_end + 0.3  # 300ms gap
                    curr["start_s"] = new_start
                    overlaps_fixed.append({
                        "file": Path(curr["file"]).name,
                        "original_start": old_start,
                        "adjusted_start": new_start,
                        "delay_added": new_start - old_start
                    })
            
            # VERY prominent warning for non-strict workflows
            print(f"\n" + "="*60)
            print(f"⚠️  OVERLAP AUTO-FIX: {len(overlaps_fixed)} segment(s) shifted!")
            print(f"="*60)
            for fix in overlaps_fixed:
                print(f"   {fix['file']}: {fix['original_start']:.1f}s → {fix['adjusted_start']:.1f}s (+{fix['delay_added']:.1f}s)")
            print(f"\n   💡 Use --strict to fail on overlaps (recommended for agentic workflows)")
            print(f"="*60 + "\n")
        
        elif overlaps_detected:
            # No fix, no strict - just warn
            print(f"⚠️  {len(overlaps_detected)} overlap(s) detected but not fixed (use --strict or remove --no-fix-overlaps)")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get video duration for apad
        video_duration = get_duration(video_path)
        
        # Build FFmpeg command with adelay filters
        inputs = ["-i", str(video_path)]
        filter_parts = []
        
        print(f"🎵 Placing {len(placements)} audio segment(s) at AI-specified times:")
        
        if len(placements) == 1:
            # Single audio stream - just delay and pad
            p = placements[0]
            delay_ms = int(p["start_s"] * 1000)
            inputs.extend(["-i", p["file"]])
            filter_parts.append(f"[1:a]adelay={delay_ms}|{delay_ms},apad=pad_dur={video_duration}[aout]")
            print(f"   {Path(p['file']).name}: {p['start_s']:.2f}s (duration: {p['duration_s']:.1f}s)")
        else:
            # Multiple audio streams - delay each, then mix
            amix_inputs = []
            for i, p in enumerate(placements):
                inputs.extend(["-i", p["file"]])
                delay_ms = int(p["start_s"] * 1000)
                filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms},apad=pad_dur={video_duration}[a{i}]")
                amix_inputs.append(f"[a{i}]")
                print(f"   {Path(p['file']).name}: {p['start_s']:.2f}s (duration: {p['duration_s']:.1f}s)")
            
            # Mix all delayed streams WITHOUT normalization
            filter_parts.append(f"{''.join(amix_inputs)}amix=inputs={len(amix_inputs)}:duration=longest:normalize=0[aout]")
        
        filter_complex = ";".join(filter_parts)
        
        # Re-encode video when source is WebM
        video_codec_args = ["-c:v", "copy"]
        if video_path.suffix.lower() == ".webm":
            video_codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]
        
        cmd = [
            ffmpeg, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            *video_codec_args,
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
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
        
        print(f"✅ Audio placed successfully!")
        
        result = {
            "success": True,
            "video": str(output_path),
            "duration_s": output_duration,
            "placements": [{"file": p["file"], "start_s": p["start_s"], "duration_s": p["duration_s"]} for p in placements],
            "segments_placed": len(placements),
            # For agentic workflows: clearly show if placements were adjusted
            "placements_adjusted": len(overlaps_fixed) > 0,
            "adjusted_placements": [
                {"file": p["file"], "requested_s": p["original_start_s"], "actual_s": p["start_s"]}
                for p in placements
            ]
        }
        
        if overlaps_fixed:
            result["overlaps_fixed"] = overlaps_fixed
            result["overlap_fixes_applied"] = len(overlaps_fixed)
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNEXPECTED_ERROR"
        }


def cmd_distribute(args) -> dict:
    """
    Handle vg compose distribute command.

    SIMPLIFIED: Distributes audio segments across video timeline using STRICT marker requirements.
    No fallback logic - requires exact timeline markers like the powerful previous solution.
    Uses simple cascading overlap fixes (300ms gaps).
    """
    import subprocess
    import shutil
    from project_paths import run_paths
    from vg_core_utils import (
        parse_request_file,
        load_timeline_markers,
        calculate_segment_times_strict,
        calculate_segment_times_lenient,
        fix_overlaps_cascading
    )
    from vg_common import get_ffmpeg
    
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        return {"success": False, "error": "ffmpeg not found", "code": "CONFIG_ERROR"}

    def get_duration(file_path):
        """Get duration using ffmpeg."""
        try:
            result = subprocess.run(
                [ffmpeg, "-i", str(file_path)],
                capture_output=True, text=True, timeout=10
            )
            import re
            duration_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', result.stderr)
            if duration_match:
                hours = int(duration_match.group(1))
                minutes = int(duration_match.group(2))
                seconds = int(duration_match.group(3))
                centiseconds = int(duration_match.group(4))
                return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
        except Exception:
            pass
        return 0.0

    try:
        video_path = Path(args.video)
        request_path = Path(args.request)
        audio_dir = Path(args.audio_dir)

        # Validate inputs
        if not video_path.exists():
            return {"success": False, "error": f"Video not found: {video_path}", "code": "FILE_NOT_FOUND"}
        if not request_path.exists():
            return {"success": False, "error": f"Request file not found: {request_path}", "code": "FILE_NOT_FOUND"}
        if not audio_dir.exists():
            return {"success": False, "error": f"Audio directory not found: {audio_dir}", "code": "FILE_NOT_FOUND"}

        # Parse request file using new utility
        request_data = parse_request_file(request_path)
        voiceover_segments = request_data["segments"]

        if not voiceover_segments:
            return {
                "success": False,
                "error": "No voiceover segments found in request file",
                "code": "PARSE_ERROR",
                "suggestion": "Ensure voiceover segments are properly defined between VOICEOVER_SEGMENTS markers"
            }

        print(f"📄 Parsed {len(voiceover_segments)} voiceover segments from request file")

        # Load timeline markers early (required for conditional fillers)
        if args.timeline:
            timeline_path = Path(args.timeline)
        else:
            timeline_path = video_path.parent / "timeline.md"
            if not timeline_path.exists():
                timeline_path = video_path.parent / "timeline.json"

        if not Path(timeline_path).exists():
            return {
                "success": False,
                "error": f"Timeline file not found: {timeline_path}. Required for precise audio positioning.",
                "code": "FILE_NOT_FOUND",
                "suggestion": "Generate timeline markers first with 'vg record' or provide timeline file with --timeline"
            }

        print(f"📋 Loading timeline from: {timeline_path}")
        markers = load_timeline_markers(Path(timeline_path))
        print(f"   Found {len(markers)} timeline markers")

        def _inject_processing_fillers(segments, markers_dict, conditional_segments=None):
            """Insert conditional narration fillers for long processing windows."""
            existing_ids = {s.get("id") for s in segments}
            added_segments = []

            def add_repeatable(
                base_id,
                start_marker,
                end_marker,
                min_duration_s,
                offset_s,
                text,
                repeatable=False,
                max_repeats=1,
                repeat_interval_s=0.0
            ):
                if start_marker not in markers_dict:
                    return
                duration_s = None
                if end_marker and end_marker in markers_dict:
                    duration_s = markers_dict[end_marker] - markers_dict[start_marker]
                if duration_s is None:
                    duration_s = 999999.0
                if duration_s < min_duration_s:
                    return
                if offset_s >= duration_s - 0.5:
                    return

                repeats = 1
                if repeatable and repeat_interval_s > 0:
                    max_by_time = int((duration_s - offset_s) // repeat_interval_s) + 1
                    repeats = min(max_repeats, max_by_time)

                for i in range(repeats):
                    seg_id = f"{base_id}_{i + 1}" if repeats > 1 else base_id
                    if seg_id in existing_ids:
                        continue
                    seg_offset = offset_s + (i * repeat_interval_s)
                    if seg_offset >= duration_s - 0.5:
                        continue
                    existing_ids.add(seg_id)
                    added_segments.append({
                        "id": seg_id,
                        "anchor": start_marker,
                        "offset_s": seg_offset,
                        "text": text
                    })

            def condition_met(condition):
                ctype = (condition or {}).get("type", "duration_between")
                if ctype == "marker_exists":
                    marker = condition.get("start_marker") or condition.get("marker")
                    return marker in markers_dict
                if ctype in ["duration_between", "duration_range"]:
                    start_marker = condition.get("start_marker")
                    end_marker = condition.get("end_marker")
                    if start_marker not in markers_dict or end_marker not in markers_dict:
                        return False
                    duration_s = markers_dict[end_marker] - markers_dict[start_marker]
                    min_duration = float(condition.get("min_duration_s", 0.0))
                    max_duration = condition.get("max_duration_s")
                    if duration_s < min_duration:
                        return False
                    if max_duration is not None and duration_s > float(max_duration):
                        return False
                    return True
                return False

            if conditional_segments:
                for seg in conditional_segments:
                    condition = seg.get("condition", {})
                    if not condition_met(condition):
                        continue
                    ctype = condition.get("type", "duration_between")
                    add_repeatable(
                        base_id=seg.get("id"),
                        start_marker=condition.get("start_marker") or condition.get("marker"),
                        end_marker=condition.get("end_marker") if ctype != "marker_exists" else None,
                        min_duration_s=float(condition.get("min_duration_s", 0.0)),
                        offset_s=float(seg.get("offset_s", 0.0)),
                        text=seg.get("text", ""),
                        repeatable=bool(seg.get("repeatable", False)),
                        max_repeats=int(seg.get("max_repeats", 1)),
                        repeat_interval_s=float(seg.get("repeat_interval_s", 0.0))
                    )
            else:
                add_repeatable(
                    base_id="processing1_filler",
                    start_marker="t_processing1_started",
                    end_marker="t_agent_done_1",
                    min_duration_s=8.0,
                    offset_s=4.0,
                    text="The agent is analyzing your connected data sources and building the perfect dashboard layout.",
                    repeatable=True,
                    max_repeats=2,
                    repeat_interval_s=6.0
                )

                add_repeatable(
                    base_id="processing2_filler",
                    start_marker="t_processing2_started",
                    end_marker="t_agent_done_2",
                    min_duration_s=6.0,
                    offset_s=3.0,
                    text="Adding those KPIs seamlessly while preserving all your existing work.",
                    repeatable=False
                )

            if added_segments:
                segments = segments + added_segments
            return segments, added_segments

        # Insert conditional fillers from request if provided, otherwise defaults
        request_conditionals = request_data.get("conditional_segments") or None
        voiceover_segments, added_fillers = _inject_processing_fillers(
            voiceover_segments,
            markers,
            conditional_segments=request_conditionals
        )
        if added_fillers:
            print(f"🧩 Added {len(added_fillers)} conditional filler segments")

        # Generate TTS for segments that need it
        print("🎤 Checking audio files and generating TTS as needed...")
        tts_generated = []

        for segment in voiceover_segments:
            audio_file = audio_dir / f"{segment['id']}.mp3"

            if not audio_file.exists() or audio_file.stat().st_size < 1000:
                print(f"  Generating TTS for {segment['id']}: '{segment['text'][:40]}...'")

                try:
                    from vg_tts import tts_with_json_output
                    tts_result = tts_with_json_output(
                        text=segment['text'],
                        output_path=str(audio_file),
                        voice_id="21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice
                    )

                    if tts_result.get("success"):
                        tts_generated.append(segment['id'])
                        print(f"    ✅ Generated {audio_file.name}")
                    else:
                        print(f"    ❌ TTS failed for {segment['id']}: {tts_result.get('error', 'Unknown error')}")
                        continue

                except Exception as e:
                    print(f"    ❌ Error generating TTS for {segment['id']}: {e}")
                    continue
            else:
                print(f"  ✓ Using existing audio for {segment['id']}")

        if tts_generated:
            print(f"🎤 Generated TTS for {len(tts_generated)} segments: {', '.join(tts_generated)}")

        # Build segments with audio file paths
        segments = []
        for segment in voiceover_segments:
            audio_file = audio_dir / f"{segment['id']}.mp3"
            if audio_file.exists():
                segments.append({
                    "id": segment["id"],
                    "anchor": segment["anchor"],  # Use 'anchor' key for timeline utility
                    "offset_s": segment["offset_s"],
                    "audio_file": str(audio_file),
                    "text": segment["text"]
                })

        if not segments:
            available_audio = list(audio_dir.glob("*.mp3"))
            return {
                "success": False,
                "error": f"No matching audio files found. Expected {len(voiceover_segments)} segments, found {len(available_audio)} audio files",
                "code": "FILE_NOT_FOUND",
                "available_audio": [str(f.name) for f in available_audio],
                "expected_segments": [s["id"] for s in voiceover_segments]
            }

        # Get video duration
        video_duration = get_duration(video_path)
        print(f"📹 Video duration: {video_duration:.1f}s")

        # Calculate positions using STRICT requirements (with lenient fallback)
        placement_mode = "strict_timeline"
        missing_markers = []
        try:
            positioned_segments = calculate_segment_times_strict(segments, markers)
        except ValueError as e:
            print(f"⚠️ Strict marker validation failed: {e}")
            positioned_segments, missing_markers = calculate_segment_times_lenient(segments, markers)
            placement_mode = "lenient_timeline"

            if not positioned_segments:
                return {
                    "success": False,
                    "error": str(e),
                    "code": "VALIDATION_ERROR",
                    "suggestion": "Ensure all required timeline markers exist in the recording"
                }

        # Apply time_mapping if video was sped up before audio was added
        # This adjusts placements from original timeline to sped-up timeline
        time_mapping = getattr(args, 'time_mapping', None)
        if time_mapping and time_mapping.get("breakpoints"):
            from vg_edit import map_time_with_breakpoints
            breakpoints = time_mapping["breakpoints"]
            print(f"⏱️ Adjusting placements for sped-up video...")
            for seg in positioned_segments:
                original_time = seg.start_time_s
                new_time = map_time_with_breakpoints(original_time, breakpoints)
                seg.start_time_s = new_time
                print(f"   - {seg.id}: {original_time:.1f}s → {new_time:.1f}s")

        print(f"⏱️ Positioned {len(positioned_segments)} segments:")
        for seg in positioned_segments:
            print(f"   - {seg.id}: {seg.start_time_s:.1f}s")

        # Get audio durations and set on segments
        for seg in positioned_segments:
            seg.duration_s = get_duration(Path(seg.audio_path))
            print(f"     Duration: {seg.duration_s:.1f}s")

        # Fix overlaps using simple cascading approach (like previous solution)
        original_positions = [(s.id, s.start_time_s) for s in positioned_segments]
        positioned_segments = fix_overlaps_cascading(positioned_segments)

        # Report any overlap fixes
        overlaps_fixed = []
        for i, (seg_id, orig_time) in enumerate(original_positions):
            new_time = positioned_segments[i].start_time_s
            if abs(new_time - orig_time) > 0.01:  # More than 10ms difference
                overlaps_fixed.append({
                    "segment": seg_id,
                    "old_start": orig_time,
                    "new_start": new_time,
                    "delay": new_time - orig_time
                })

        if overlaps_fixed:
            print(f"🔧 Fixed {len(overlaps_fixed)} overlapping segments with 300ms gaps:")
            for fix in overlaps_fixed:
                print(f"   {fix['segment']}: delayed {fix['delay']:.1f}s (from {fix['old_start']:.1f}s to {fix['new_start']:.1f}s)")

        # Determine output path
        output_path = Path(args.output)
        if hasattr(args, 'run_id') and args.run_id:
            rp = run_paths(args.run_id)
            rp.run_dir.mkdir(parents=True, exist_ok=True)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command for precise audio placement
        inputs = ["-i", str(video_path)]
        filter_parts = []

        if len(positioned_segments) == 1:
            # Single audio stream - just delay and pad
            seg = positioned_segments[0]
            delay_ms = int(seg.start_time_s * 1000)
            filter_parts.append(f"[1:a]adelay={delay_ms},apad=pad_dur={video_duration}[aout]")
            inputs.extend(["-i", str(seg.audio_path)])
        else:
            # Multiple audio streams - delay each, then mix
            amix_inputs = []
            for i, seg in enumerate(positioned_segments):
                inputs.extend(["-i", str(seg.audio_path)])
                delay_ms = int(seg.start_time_s * 1000)
                filter_parts.append(f"[{i+1}:a]adelay={delay_ms},apad=pad_dur={video_duration}[a{i}]")
                amix_inputs.append(f"[a{i}]")

            # Mix all delayed streams WITHOUT normalization (segments don't overlap, so no clipping risk)
            # normalize=0 keeps original volume levels instead of dividing by number of inputs
            filter_parts.append(f"{''.join(amix_inputs)}amix=inputs={len(amix_inputs)}:duration=longest:normalize=0[aout]")

        filter_complex = ";".join(filter_parts)

        # Re-encode video when source is WebM to avoid MP4 codec issues
        video_codec_args = ["-c:v", "copy"]
        if video_path.suffix.lower() == ".webm":
            video_codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]

        cmd = [
            ffmpeg, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v",  # Video from first input
            "-map", "[aout]",  # Mixed audio
            *video_codec_args,
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path)
        ]

        print(f"🎵 Distributing {len(positioned_segments)} audio segments with precise timing...")
        for seg in positioned_segments:
            print(f"   {seg.id}: {seg.start_time_s:.1f}s (duration: {seg.duration_s:.1f}s)")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"FFmpeg distribute failed: {result.stderr}",
                "code": "FFMPEG_ERROR",
                "ffmpeg_cmd": " ".join(cmd)
            }

        print("✅ Audio distributed successfully with precise timeline synchronization!")

        return {
            "success": True,
            "video": str(output_path),
            "segments_distributed": len(positioned_segments),
            "placements": [{"id": s.id, "start_time": s.start_time_s, "duration": s.duration_s} for s in positioned_segments],
            "video_duration": video_duration,
            "timeline_used": True,
            "placement_mode": placement_mode,
            "overlaps_fixed": overlaps_fixed if overlaps_fixed else None,
            "overlap_fixes_applied": len(overlaps_fixed) if overlaps_fixed else 0,
            "missing_markers": missing_markers if missing_markers else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNEXPECTED_ERROR"
        }