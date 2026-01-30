"""
vg request commands

Parse and process video request files (.md) to drive video generation.

NOTE: All parsing logic lives in vg_core_utils/md_parser.py.
This module provides CLI commands that use the unified parser.
"""

import argparse
from pathlib import Path
from typing import Optional

# Import from core utils (path set by vg entry point)
from vg_core_utils import parse_request_file as parse_request_file_core, markers_to_md_block


def register(subparsers):
    """Register request commands."""
    request_parser = subparsers.add_parser('request', help='Process video request files')
    request_sub = request_parser.add_subparsers(dest='request_command')

    # vg request parse
    parse_parser = request_sub.add_parser('parse', help='Parse request file and extract segments')
    parse_parser.add_argument('--file', '-f', required=True, help='Request file path (.md)')
    parse_parser.set_defaults(func=cmd_parse)

    # vg request generate
    gen_parser = request_sub.add_parser('generate', help='Generate video from request file')
    gen_parser.add_argument('--file', '-f', required=True, help='Request file path (.md)')
    gen_parser.add_argument('--run-id', help='Run ID for output folder')
    gen_parser.add_argument('--skip-record', action='store_true', help='Skip recording (use existing video)')
    gen_parser.add_argument('--video', help='Existing video to use (with --skip-record)')
    gen_parser.add_argument('--timeline', help='Timeline JSON to use (with --skip-record)')
    gen_parser.set_defaults(func=cmd_generate)


def parse_request_file(file_path: str) -> dict:
    """
    Parse a video request markdown file and extract all structured data.
    
    DELEGATES TO: vg_core_utils.parse_request_file (single source of truth)
    
    This wrapper exists for backward compatibility - it returns the unified
    parser result directly. All parsing logic is in vg_core_utils/md_parser.py.
    """
    return parse_request_file_core(Path(file_path))


def cmd_parse(args) -> dict:
    """Handle vg request parse command.
    
    Returns structured data from request file for AI agents to use:
    - url: Target URL for recording
    - auth: Authentication configuration
    - scenario_flow_text: Natural language description of recording steps (for AI to read)
    - voiceover_segments: Audio segments with timing anchors
    - guided_actions: Parsed actions from scenario flow (best-effort)
    - goal: What the demo should accomplish
    """
    from vg_common import error_response, success_response
    
    try:
        file_path = Path(args.file)
        if not file_path.exists():
            return {
                "success": False,
                "error": f"Request file not found: {args.file}",
                "code": "FILE_NOT_FOUND",
                "suggestion": "Check the file path and ensure the request file exists"
            }
        
        parsed = parse_request_file(args.file)
        
        # Use unified parser output
        segments = parsed.get("segments", [])
        options = parsed.get("options", {})
        platform = parsed.get("platform", {})
        auth = parsed.get("authentication", {})
        
        # Extract required markers from voiceover segments
        # These are the markers AI must add during recording for voiceover to sync correctly
        required_markers = []
        for seg in segments:
            anchor = seg.get("anchor")
            if anchor and anchor not in ["t_page_loaded", "t_start_recording", "t_recording_complete"]:
                # t_page_loaded is auto-added by session start
                required_markers.append(anchor)
        required_markers = list(dict.fromkeys(required_markers))  # Remove duplicates, preserve order
        
        # Build AI-friendly output
        return success_response(
            # Essential info for recording
            url=platform.get("url"),
            auth=auth,
            goal=parsed.get("goal", ""),
            
            # Scenario Flow - natural language for AI to read and understand
            scenario_flow_text=parsed.get("scenario_flow_text", ""),
            
            # Parsed actions (best-effort from scenario flow)
            guided_actions=parsed.get("guided_actions", []),
            guided_actions_count=len(parsed.get("guided_actions", [])),
            
            # Voiceover segments
            voiceover_segments=segments,
            segments_count=len(segments),
            
            # Required markers - AI MUST add these during recording for voiceover sync
            required_markers=required_markers,
            required_markers_note="Add these markers during recording using: vg record session do --action marker --value <marker_name>",
            
            # Flags
            has_voiceover=parsed.get("has_voiceover", False) or options.get("voiceover_enabled", False),
            has_talking_head=options.get("talking_head_enabled", False),
            
            # Full parsed data (for advanced use)
            request=parsed
        )
    
    except Exception as e:
        return error_response(e, "Failed to parse request file")


def cmd_generate(args) -> dict:
    """Handle vg request generate command - full workflow from request file."""
    from datetime import datetime
    from project_paths import run_paths
    from vg_tts import tts_with_json_output
    from vg_quality import optimize_video
    from vg_compose import sync_audio_video
    from vg_recording import RecordingConfig, record_demo
    from vg_common import error_response
    
    try:
        # Parse request file using unified parser
        file_path = Path(args.file)
        if not file_path.exists():
            return {
                "success": False,
                "error": f"Request file not found: {args.file}",
                "code": "FILE_NOT_FOUND",
                "suggestion": "Check the file path and ensure the request file exists"
            }
        
        parsed = parse_request_file(args.file)
        
        # Setup run ID and paths
        if args.run_id:
            run_id = args.run_id
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            platform_name = parsed["platform"].get("name", "demo").lower().replace(" ", "_")
            run_id = f"{platform_name}_{timestamp}"
        
        rp = run_paths(run_id)
        rp.run_dir.mkdir(parents=True, exist_ok=True)
        rp.audio_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "success": True,
            "run_id": run_id,
            "run_dir": str(rp.run_dir),
            "steps": []
        }
        audio_files = []
        timeline_path = None
        timeline_markers = None
        video_path = None
        
        # Step 1: Generate voiceover segments (including conditional)
        voiceover_segments = parsed.get("voiceover_segments", [])
        conditional_segments = parsed.get("conditional_segments", [])
        segments_for_tts = voiceover_segments + conditional_segments
        voiceover_ids = {s.get("id") for s in voiceover_segments}

        if segments_for_tts:
            for segment in segments_for_tts:
                output_path = rp.audio_dir / f"{segment['id']}.mp3"
                print(f"🎤 Generating audio: {segment['id']}...")
                
                tts_result = tts_with_json_output(
                    text=segment["text"],
                    output_path=output_path,
                    voice_id="21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice
                )
                
                if tts_result.get("success"):
                    audio_files.append(str(output_path))
                    results["steps"].append({
                        "step": "tts",
                        "segment": segment["id"],
                        "success": True,
                        "audio": str(output_path)
                    })
                else:
                    results["steps"].append({
                        "step": "tts",
                        "segment": segment["id"],
                        "success": False,
                        "error": tts_result.get("error")
                    })
            
            # Step 2: Combine core narration segments (exclude conditional fillers)
            concat_audio_files = [f for f in audio_files if Path(f).stem in voiceover_ids]
            if concat_audio_files:
                print("🎵 Combining audio segments...")
                import subprocess
                import shutil
                
                ffmpeg = Path(__file__).parent.parent.parent.parent / "node_modules" / "ffmpeg-static" / "ffmpeg"
                if not ffmpeg.exists():
                    ffmpeg = shutil.which("ffmpeg")
                
                if ffmpeg:
                    concat_file = rp.audio_dir / "concat_list.txt"
                    with open(concat_file, 'w') as f:
                        for af in concat_audio_files:
                            f.write(f"file '{af}'\n")
                    
                    full_narration = rp.audio_dir / "full_narration.mp3"
                    cmd = [
                        str(ffmpeg), "-y",
                        "-f", "concat", "-safe", "0",
                        "-i", str(concat_file),
                        "-c:a", "libmp3lame", "-b:a", "128k",
                        str(full_narration)
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=120)
                    concat_file.unlink()
                    
                    results["steps"].append({
                        "step": "audio_mix",
                        "success": True,
                        "audio": str(full_narration),
                        "segments_combined": len(concat_audio_files)
                    })
                    results["full_narration"] = str(full_narration)

        # Step 2: Record video unless skipping
        if not args.skip_record:
            url = parsed.get("platform", {}).get("url")
            if not url:
                return {
                    "success": False,
                    "error": "Request file missing platform URL. Add ## Platform with **URL:** field.",
                    "code": "VALIDATION"
                }

            print("🎬 Recording video from request...")
            explicit_actions = parsed.get("actions") or None
            guided_actions = parsed.get("guided_actions") or []
            scenario_prompts = parsed.get("scenario_prompts") or []
            voiceover_prompts = parsed.get("voiceover_prompts") or []
            success_criteria = parsed.get("success_criteria") or []
            voiceover_anchors = {s.get("anchor") for s in parsed.get("voiceover_segments", [])}
            ai_markers = {
                "t_prompt1_focus",
                "t_prompt2_focus",
                "t_processing1_started",
                "t_processing2_started",
                "t_agent_done_1",
                "t_agent_done_2"
            }
            needs_ai_flow = bool(voiceover_anchors & ai_markers)
            prompts = scenario_prompts or voiceover_prompts
            
            # Determine actions to use: explicit > guided > none
            # guided_actions come from parsing Scenario Flow section
            actions_to_use = explicit_actions or (guided_actions if guided_actions else None)

            # Determine scenario based on what we have
            if explicit_actions:
                scenario = "custom"
            elif guided_actions:
                # Use guided actions from Scenario Flow - executes parsed steps
                scenario = "guided"
                print(f"   📋 Using {len(guided_actions)} guided actions from Scenario Flow")
            elif needs_ai_flow:
                scenario = "ai-agent"
            elif prompts:
                scenario = "auto"
            else:
                scenario = "simple-dashboard"

            # Load auth from request file
            from vg_auth import _auth_from_request_data
            auth_cookies, auth_headers, auth_err = _auth_from_request_data(parsed)
            if auth_err:
                return {
                    "success": False,
                    "error": auth_err,
                    "code": "AUTH_ERROR"
                }
            
            record_result = record_demo(RecordingConfig(
                url=url,
                scenario=scenario,
                actions=actions_to_use,
                auto_prompts=prompts,
                run_id=run_id,
                validation_checks=success_criteria,
                prompts=prompts if scenario == "ai-agent" else None,
                auth_cookies=auth_cookies or None,
                auth_headers=auth_headers or None
            ))

            # CRITICAL: Recording success is INDEPENDENT of audio markers
            # Missing voiceover markers is an AUDIO PLACEMENT issue, not a RECORDING failure
            # The recording captured the video correctly - audio placement happens later
            
            if not record_result.get("success"):
                return record_result

            video_path = record_result.get("video") or record_result.get("raw_video")
            timeline_path = record_result.get("timeline")
            timeline_markers = record_result.get("markers")

            # Copy recording assets into the run_id folder for consistency
            import shutil
            rp.raw_dir.mkdir(parents=True, exist_ok=True)
            if video_path and Path(video_path).exists():
                copied_video = rp.raw_dir / Path(video_path).name
                shutil.copy(video_path, copied_video)
                video_path = str(copied_video)

            if timeline_path and Path(timeline_path).exists():
                shutil.copy(timeline_path, rp.timeline_md)
                timeline_path = str(rp.timeline_md)

            screenshots_dir = record_result.get("screenshots_dir")
            if screenshots_dir and Path(screenshots_dir).exists():
                target_dir = rp.raw_dir / "screenshots"
                target_dir.mkdir(parents=True, exist_ok=True)
                for img in Path(screenshots_dir).glob("*.png"):
                    shutil.copy(img, target_dir / img.name)

            results["steps"].append({
                "step": "record",
                "success": True,
                "video": video_path,
                "timeline": timeline_path
            })

            # SIMPLE TRIM: Use value from request file if specified
            trim_start_time = parsed.get("trim_start", 0) or 0
            if trim_start_time > 0:
                print(f"✂️  Trimming first {trim_start_time}s as requested in file")
            
            # Convert recorded WebM to MP4 for downstream ffmpeg operations
            if video_path and Path(video_path).suffix.lower() == ".webm":
                print("🎬 Converting recorded WebM to MP4...")
                output_mp4 = rp.run_dir / "demo.mp4"
                
                # If trimming, use ffmpeg directly for trim+convert in one step
                if trim_start_time > 0:
                    print(f"🎬 Trimming and converting (start: {trim_start_time:.1f}s)...")
                    import subprocess
                    from vg_common import get_ffmpeg
                    ffmpeg = get_ffmpeg()
                    
                    result = subprocess.run([
                        ffmpeg, "-ss", str(trim_start_time), "-i", str(video_path),
                        "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                        "-c:a", "aac", "-b:a", "192k",
                        str(output_mp4), "-y"
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        print(f"✅ Trimmed {trim_start_time:.1f}s and converted to MP4!")
                        # Adjust timeline markers to account for trim
                        timeline_markers = {k: max(0, v - trim_start_time) for k, v in timeline_markers.items()}
                        results["steps"].append({
                            "step": "video_convert",
                            "success": True,
                            "video": str(output_mp4),
                            "auto_trimmed": trim_start_time
                        })
                        video_path = str(output_mp4)
                        results["video"] = str(output_mp4)
                    else:
                        print(f"⚠️  Trim/convert failed, falling back to optimize_video")
                        trim_start_time = 0  # Reset - will use standard conversion
                
                # Standard conversion if no trim or trim failed
                if trim_start_time == 0:
                    optimize_result = optimize_video(
                        input_path=str(video_path),
                        output_path=str(output_mp4),
                        quality="high"
                    )
                    if optimize_result.get("success"):
                        results["steps"].append({
                            "step": "video_convert",
                            "success": True,
                            "video": str(output_mp4)
                        })
                        video_path = str(output_mp4)
                        results["video"] = str(output_mp4)
        
        # Step 3: Process video (if provided or skip-record)
        if args.skip_record and args.video:
            video_path = Path(args.video)
            if video_path.exists():
                # Copy provided video into run raw/ for consistent asset layout
                rp.raw_dir.mkdir(parents=True, exist_ok=True)
                copied_video = rp.raw_dir / video_path.name
                if video_path.resolve() != copied_video.resolve():
                    import shutil
                    shutil.copy(video_path, copied_video)
                video_path = copied_video

                # Convert to MP4 if needed
                if video_path.suffix.lower() == '.webm':
                    print("🎬 Converting video to MP4...")
                    output_mp4 = rp.run_dir / "demo.mp4"
                    optimize_result = optimize_video(
                        input_path=str(video_path),
                        output_path=str(output_mp4),
                        quality="high"
                    )
                    if optimize_result.get("success"):
                        results["steps"].append({
                            "step": "video_convert",
                            "success": True,
                            "video": str(output_mp4)
                        })
                        results["video"] = str(output_mp4)
                        video_path = Path(results["video"])
                else:
                    results["video"] = str(video_path)

                # Determine timeline path when skipping recording
                if args.timeline and Path(args.timeline).exists():
                    timeline_src = Path(args.timeline)
                    import shutil
                    rp.run_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy(timeline_src, rp.timeline_md)
                    timeline_path = str(rp.timeline_md)
                else:
                    candidate_paths = [
                        video_path.parent / "timeline.md",
                        video_path.parent.parent / "timeline.md",
                        video_path.parent / "timeline.json",
                        video_path.parent.parent / "timeline.json"
                    ]
                    for candidate in candidate_paths:
                        if candidate.exists():
                            import shutil
                            rp.run_dir.mkdir(parents=True, exist_ok=True)
                            shutil.copy(candidate, rp.timeline_md)
                            timeline_path = str(rp.timeline_md)
                            break

        # Update request file with timeline markers (single source of truth)
        if not timeline_markers and timeline_path and Path(timeline_path).exists():
            try:
                from vg_core_utils import load_timeline_markers
                timeline_markers = load_timeline_markers(Path(timeline_path))
            except Exception:
                timeline_markers = None

        if timeline_markers:
            try:
                request_text = file_path.read_text(encoding="utf-8")
                start_tag = "<!-- TIMELINE_MARKERS_START -->"
                end_tag = "<!-- TIMELINE_MARKERS_END -->"
                marker_block = markers_to_md_block(timeline_markers)
                if start_tag in request_text and end_tag in request_text:
                    before = request_text.split(start_tag)[0]
                    after = request_text.split(end_tag)[1]
                    file_path.write_text(before + marker_block + after, encoding="utf-8")
                else:
                    file_path.write_text(request_text + "\n\n" + marker_block + "\n", encoding="utf-8")
                # Use request file as timeline source from here on
                timeline_path = str(file_path)
            except Exception:
                pass
        
        # Step 4: Distribute audio segments across video timeline
        # This places each segment at its proper position based on request markers
        dist_result = None
        opts = parsed.get("options", {})
        speed_gaps_enabled = opts.get("speed_gaps_enabled", False)
        speed_factor = opts.get("speed_factor", 3.0)
        if (results.get("video") or video_path) and audio_files:
            print("🎬 Distributing audio segments across video timeline...")
            final_output = rp.run_dir / "final.mp4"
            
            if timeline_path:
                # Use distribute_audio function
                from vg_commands.compose import cmd_distribute
                import argparse

                # Create args namespace for distribute
                dist_args = argparse.Namespace(
                    video=str(results.get("video") or video_path),
                    request=str(file_path),
                    audio_dir=str(rp.audio_dir),
                    output=str(final_output),
                    run_id=run_id,
                    timeline=timeline_path,
                    time_mapping=None  # Not used in simplified approach
                )

                dist_result = cmd_distribute(dist_args)

                if dist_result.get("success"):
                    results["steps"].append({
                        "step": "compose_distribute",
                        "success": True,
                        "video": str(final_output),
                        "segments_distributed": dist_result.get("segments_distributed"),
                        "placements": dist_result.get("placements")
                    })
                    results["final_video"] = str(final_output)
                else:
                    # Fallback to simple sync if distribute fails
                    print(f"⚠️ Distribute failed: {dist_result.get('error')}, falling back to simple sync...")
                    if results.get("full_narration"):
                        sync_result = sync_audio_video(
                            video_path=str(results.get("video") or video_path),
                            audio_path=results["full_narration"],
                            output_path=str(final_output)
                        )
                        if sync_result.get("success"):
                            results["steps"].append({
                                "step": "compose_sync_fallback",
                                "success": True,
                                "video": str(final_output)
                            })
                            results["final_video"] = str(final_output)
            else:
                # No timeline available, fall back to simple sync if possible
                if results.get("full_narration"):
                    sync_result = sync_audio_video(
                        video_path=str(results.get("video") or video_path),
                        audio_path=results["full_narration"],
                        output_path=str(final_output)
                    )
                    if sync_result.get("success"):
                        results["steps"].append({
                            "step": "compose_sync_fallback",
                            "success": True,
                            "video": str(final_output)
                        })
                        results["final_video"] = str(final_output)

        # Step 4.5: Speed up gaps AFTER distribute (using ACTUAL placements)
        # This is the simple and correct approach:
        # - Distribute placed audio at exact positions
        # - We know exactly where audio is (from placements)
        # - Speed up only the gaps (silent sections) - audio is preserved
        if speed_gaps_enabled and results.get("final_video") and dist_result and dist_result.get("placements"):
            print(f"\n🚀 Speed-gaps: speeding up silent gaps {speed_factor}x (using actual audio placements)...")
            from vg_edit import speed_gaps
            
            # Convert placements to format expected by speed_gaps
            audio_placements = []
            for p in dist_result["placements"]:
                audio_placements.append({
                    "id": p.get("id"),
                    "start_time": p.get("start_time_s", p.get("start_time", 0)),
                    "duration": p.get("duration_s", p.get("duration", 0))
                })
            
            current_video = results["final_video"]
            sped_video = rp.run_dir / "final_fast.mp4"
            
            speed_result = speed_gaps(
                input_path=current_video,
                output_path=str(sped_video),
                factor=speed_factor,
                min_gap=2.0,
                audio_placements=audio_placements  # Use ACTUAL placements!
            )
            
            if speed_result.get("success"):
                results["steps"].append({
                    "step": "speed_gaps",
                    "success": True,
                    "video": str(sped_video),
                    "original_duration": speed_result.get("original_duration"),
                    "new_duration": speed_result.get("duration"),
                    "time_saved": speed_result.get("time_saved"),
                    "factor": speed_factor,
                    "used_actual_placements": True
                })
                results["final_video"] = str(sped_video)
                print(f"✅ Video sped up: {speed_result.get('original_duration', 0):.1f}s → {speed_result.get('duration', 0):.1f}s")
                print(f"   Preserved {len(audio_placements)} audio segments at normal speed")
            else:
                print(f"⚠️ Speed-gaps failed: {speed_result.get('error')}")
                print(f"   Continuing with original video (audio intact)")

        # Step 5: Add talking heads if requested and placements available
        th_opts = parsed.get("options", {})
        if th_opts.get("talking_head_enabled") and results.get("final_video"):
            placements = (dist_result or {}).get("placements")
            if placements:
                from vg_talking_head import composite_talking_heads

                requested_segments = th_opts.get("talking_head_segments")
                if requested_segments and "*" not in requested_segments:
                    requested_set = {s.lower() for s in requested_segments}
                    placements = [p for p in placements if p["id"].lower() in requested_set]

                if placements:
                    model_raw = (th_opts.get("talking_head_model") or "").strip().lower()
                    model = "sadtalker" if "sad" in model_raw else "omnihuman"
                    position = th_opts.get("talking_head_position", "bottom-right")
                    size_px = th_opts.get("talking_head_size_px", 280)

                    th_output = rp.run_dir / "final_talking_heads.mp4"
                    th_result = composite_talking_heads(
                        main_video=str(results["final_video"]),
                        placements=placements,
                        audio_dir=str(rp.audio_dir),
                        output_path=str(th_output),
                        model=model,
                        position=position,
                        size_px=size_px
                    )

                    if th_result.get("success"):
                        results["steps"].append({
                            "step": "talking_heads",
                            "success": True,
                            "video": str(th_output),
                            "segments": th_result.get("segments_composited")
                        })
                        results["final_video"] = str(th_output)
                    else:
                        results["steps"].append({
                            "step": "talking_heads",
                            "success": False,
                            "error": th_result.get("error")
                        })
            else:
                results["steps"].append({
                    "step": "talking_heads",
                    "success": False,
                    "error": "No placements available for talking heads; distribute step may have failed"
                })
        
        if results.get("video") is None and video_path:
            results["video"] = str(video_path)

        # Build run report (Markdown) and update request file
        def _build_run_report(run_dir: Path, timeline_path_val: Optional[str]) -> str:
            lines = [
                f"# Run Report: {run_id}",
                "",
                f"- Run directory: {run_dir}",
                f"- Final video: {results.get('final_video')}",
                f"- Video (converted): {results.get('video')}",
                f"- Timeline source: {timeline_path_val or 'n/a'}",
                f"- Request file: {file_path}",
                ""
            ]

            if timeline_markers:
                lines.append("## Timeline Markers")
                lines.append("")
                lines.append(markers_to_md_block(timeline_markers))

            lines.append("## Screenshots")
            lines.append("")
            screenshot_dir = rp.raw_dir / "screenshots"
            if screenshot_dir.exists():
                for shot in sorted(screenshot_dir.glob("*.png")):
                    lines.append(f"- {shot}")
            else:
                lines.append("- None")

            lines.append("")
            lines.append("## Issues")
            lines.append("")
            issues = []
            if dist_result and dist_result.get("missing_markers"):
                issues.append(f"Missing timeline markers: {', '.join(dist_result.get('missing_markers'))}")
            if dist_result and dist_result.get("segments_distributed", 0) < len(parsed.get("voiceover_segments", [])):
                issues.append("Not all narration segments were placed.")
            if results.get("final_video") and th_opts.get("talking_head_enabled") and not any(step.get("step") == "talking_heads" and step.get("success") for step in results.get("steps", [])):
                issues.append("Talking heads were not composited (missing placements).")
            if not issues:
                issues.append("None detected.")
            lines.extend([f"- {issue}" for issue in issues])
            lines.append("")
            return "\n".join(lines)

        report_md = _build_run_report(rp.run_dir, timeline_path)
        report_path = rp.run_dir / "run_report.md"
        report_path.write_text(report_md, encoding="utf-8")
        results["run_report"] = str(report_path)

        # Update request file with latest run report
        try:
            request_text = file_path.read_text(encoding="utf-8")
            start_tag = "<!-- RUN_RESULTS_START -->"
            end_tag = "<!-- RUN_RESULTS_END -->"
            report_block = f"{start_tag}\n\n{report_md}\n\n{end_tag}\n"
            if start_tag in request_text and end_tag in request_text:
                before = request_text.split(start_tag)[0]
                after = request_text.split(end_tag)[1]
                file_path.write_text(before + report_block + after, encoding="utf-8")
            else:
                file_path.write_text(request_text + "\n\n" + report_block, encoding="utf-8")
        except Exception:
            pass

        return results
    
    except Exception as e:
        return error_response(e, "Video generation failed")
