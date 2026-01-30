"""
Talking head functionality for vg CLI.

Wraps generate_talking_head.py for CLI integration.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict
import subprocess

from generate_talking_head import (
    generate_character_image,
    generate_talking_head_video,
    integrate_talking_head_into_video,
    get_ffmpeg_path
)
from vg_common import VGError, classify_error, get_suggestion, get_duration, cache_key, get_cached, save_to_cache


@dataclass
class TalkingHeadSegment:
    id: str
    audio_path: Path
    start_time_s: float
    duration_s: float
    video_path: Optional[Path] = None

def generate_character(output_path: Optional[str] = None, force: bool = False) -> dict:
    """
    Generate presenter character image.
    """
    try:
        result_path = generate_character_image(force_regenerate=force)

        if output_path:
            # Copy to specified location
            import shutil
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(result_path, output)
            result_path = str(output)

        return {
            "success": True,
            "image": result_path,
            "cached": not force
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def generate_talking_head(
    audio_path: str,
    output_path: str,
    character_image: Optional[str] = None,
    model: str = "omnihuman"
) -> dict:
    """
    Generate talking head video from audio with caching.
    """
    try:
        audio = Path(audio_path)
        output = Path(output_path)

        # Validate inputs
        if not audio.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        # Check cache first
        import hashlib
        audio_hash = hashlib.md5(audio.read_bytes()).hexdigest()
        cache_key_val = cache_key(audio_hash, character_image or "default", model, "talking_head")
        cached_path = get_cached("talking_head", cache_key_val)

        if cached_path:
            # Use cached result
            import shutil
            shutil.copy(cached_path, output)
            result_path = output_path
            cached = True
        else:
            # Generate new talking head video
            result_path = generate_talking_head_video(
                character_image=character_image,
                audio_path=audio_path,
                output_path=output_path,
                model=model
            )

            # Save to cache
            save_to_cache("talking_head", cache_key_val, Path(result_path), {
                "audio_hash": audio_hash,
                "character_image": character_image,
                "model": model
            })
            cached = False

        # Get duration
        duration = get_duration(Path(result_path))

        return {
            "success": True,
            "video": result_path,
            "duration": duration,
            "size": Path(result_path).stat().st_size,
            "model": model,
            "character_image": character_image,
            "cached": cached
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def composite_talking_head(
    main_video: str,
    talking_head_video: str,
    output_path: str,
    position: str = "bottom-right",
    size: int = 280,
    start_time: float = 0
) -> dict:
    """
    Composite talking head onto main video.
    """
    try:
        main = Path(main_video)
        talking_head = Path(talking_head_video)
        output = Path(output_path)

        # Validate inputs
        if not main.exists():
            raise FileNotFoundError(f"Main video not found: {main}")
        if not talking_head.exists():
            raise FileNotFoundError(f"Talking head video not found: {talking_head}")

        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        # Composite videos
        result_path = integrate_talking_head_into_video(
            main_video=main_video,
            talking_head_video=talking_head_video,
            output_video=output_path,
            start_time=start_time,
            position=position,
            size_px=size
        )

        # Get duration
        duration = get_duration(Path(result_path))

        return {
            "success": True,
            "video": result_path,
            "duration": duration,
            "size": Path(result_path).stat().st_size,
            "position": position,
            "size_px": size,
            "start_time": start_time
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }


def _strip_audio(ffmpeg: str, video_path: Path) -> Path:
    """Strip audio from talking head video to avoid double audio."""
    no_audio_path = video_path.with_name(f"{video_path.stem}_noaudio.mp4")
    if no_audio_path.exists() and no_audio_path.stat().st_size > 0:
        return no_audio_path

    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-an",
        "-c:v", "copy",
        str(no_audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to strip audio: {result.stderr}")
    return no_audio_path


def _integrate_talking_heads(
    main_video: Path,
    segments: List[TalkingHeadSegment],
    output_path: Path,
    position: str,
    size_px: int
) -> Path:
    """Integrate multiple talking head overlays into the main video."""
    if not segments:
        return main_video

    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")

    margin = 20
    if position == "bottom-right":
        overlay_pos = f"W-w-{margin}:H-h-{margin}"
    elif position == "bottom-left":
        overlay_pos = f"{margin}:H-h-{margin}"
    elif position == "top-right":
        overlay_pos = f"W-w-{margin}:{margin}"
    else:
        overlay_pos = f"{margin}:{margin}"

    inputs = ["-i", str(main_video)]
    filter_parts = []
    prev_output = "0:v"

    for i, seg in enumerate(segments):
        if not seg.video_path:
            continue

        no_audio = _strip_audio(ffmpeg, seg.video_path)
        inputs.extend(["-itsoffset", str(seg.start_time_s), "-i", str(no_audio)])

        th_scaled = f"th{i}"
        filter_parts.append(f"[{i + 1}:v]scale={size_px}:{size_px}[{th_scaled}]")

        end_time = seg.start_time_s + seg.duration_s
        out_label = "outv" if i == len(segments) - 1 else f"v{i}"
        enable_filter = f"between(t,{seg.start_time_s:.2f},{end_time:.2f})"
        filter_parts.append(
            f"[{prev_output}][{th_scaled}]overlay={overlay_pos}:enable='{enable_filter}':eof_action=pass[{out_label}]"
        )
        prev_output = out_label

    if not filter_parts:
        return main_video

    filter_complex = ";".join(filter_parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg overlay failed: {result.stderr}")

    return output_path


def composite_talking_heads(
    main_video: str,
    placements: List[Dict[str, float]],
    audio_dir: str,
    output_path: str,
    model: str = "omnihuman",
    position: str = "bottom-right",
    size_px: int = 280,
    character_image: Optional[str] = None
) -> dict:
    """Composite multiple talking heads on a video using placement timings."""
    try:
        main = Path(main_video)
        audio_root = Path(audio_dir)
        output = Path(output_path)

        if not main.exists():
            raise FileNotFoundError(f"Main video not found: {main}")
        if not audio_root.exists():
            raise FileNotFoundError(f"Audio directory not found: {audio_root}")

        segments: List[TalkingHeadSegment] = []
        for placement in placements:
            seg_id = placement.get("id")
            if not seg_id:
                continue
            audio_path = audio_root / f"{seg_id}.mp3"
            if not audio_path.exists():
                continue

            start_time = float(placement.get("start_time", 0.0))
            duration = float(placement.get("duration") or 0.0)
            if duration <= 0:
                duration = get_duration(audio_path)

            segments.append(TalkingHeadSegment(
                id=seg_id,
                audio_path=audio_path,
                start_time_s=start_time,
                duration_s=duration
            ))

        if not segments:
            raise ValueError("No valid placements with audio found for talking heads")

        segments.sort(key=lambda s: s.start_time_s)
        th_dir = output.parent / "talking_heads"
        th_dir.mkdir(parents=True, exist_ok=True)

        character = character_image or generate_character_image()
        valid_segments: List[TalkingHeadSegment] = []

        for seg in segments:
            th_out = th_dir / f"{seg.id}_talking_head.mp4"
            result = generate_talking_head(
                audio_path=str(seg.audio_path),
                output_path=str(th_out),
                character_image=character,
                model=model
            )
            if result.get("success"):
                seg.video_path = Path(result["video"])
                valid_segments.append(seg)

        if not valid_segments:
            raise RuntimeError("Talking head generation failed for all segments")

        final_path = _integrate_talking_heads(
            main_video=main,
            segments=valid_segments,
            output_path=output,
            position=position,
            size_px=size_px
        )

        return {
            "success": True,
            "video": str(final_path),
            "segments_composited": len(valid_segments),
            "position": position,
            "size_px": size_px,
            "model": model
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }