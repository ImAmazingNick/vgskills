"""
Composition functionality for vg CLI.

Video composition operations (sync, overlay, etc.).
"""

from pathlib import Path
from typing import Optional
import subprocess

from video_postprocess import ensure_mp4_from_webm
from vg_common import VGError, classify_error, get_suggestion, get_duration

def sync_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    timeline_path: Optional[str] = None
) -> dict:
    """
    Sync audio with video using ffmpeg.
    
    Requires ffmpeg to be available (via node_modules/ffmpeg-static or system).
    """
    try:
        video = Path(video_path)
        audio = Path(audio_path)
        output = Path(output_path)

        # Validate inputs
        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")
        if not audio.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        import shutil
        import subprocess
        from vg_common import get_ffmpeg

        # Ensure output has .mp4 extension
        if not str(output).endswith('.mp4'):
            output = output.with_suffix('.mp4')

        # Require ffmpeg - no fallback
        ffmpeg = get_ffmpeg()
        if not ffmpeg:
            return {
                "success": False,
                "error": "ffmpeg not found. Required for audio/video sync.",
                "code": "CONFIG_ERROR",
                "suggestion": "Install ffmpeg: 'npm install ffmpeg-static' or install system ffmpeg"
            }

        # Audio/video muxing using ffmpeg
        if True:  # Always use ffmpeg (no demo fallback)
            # Re-encode video when source is WebM to avoid MP4 codec issues
            video_codec_args = ["-c:v", "copy"]
            if video.suffix.lower() == ".webm":
                video_codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]

            # Real audio/video muxing using ffmpeg
            cmd = [
                ffmpeg, "-y",  # Overwrite output
                "-i", str(video),  # Video input
                "-i", str(audio),  # Audio input
                *video_codec_args,
                "-c:a", "aac",  # Encode audio to AAC
                "-b:a", "128k",  # Audio bitrate
                "-shortest",  # End when shortest input ends
                "-movflags", "+faststart",  # Web optimization
                str(output)  # Output file
            ]

            # Execute real ffmpeg muxing
            print(f"🎵 Syncing audio {audio.name} with video {video.name}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                error_msg = f"FFmpeg audio sync failed: {result.stderr[:500]}"
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            print(f"✅ Audio successfully synced with video!")

        # Get output info
        duration = get_duration(output)
        size = output.stat().st_size

        return {
            "success": True,
            "video": str(output),
            "duration": duration,
            "size": size,
            "method": "ffmpeg_mux" if ffmpeg else "demo_sync",
            "audio_synced": True,
            "timeline_used": timeline_path is not None,
            "processing_mode": "real" if ffmpeg else "demo",
            "ffmpeg_used": ffmpeg
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def overlay_video(
    main_video: str,
    overlay_video: str,
    output_path: str,
    position: str = "bottom-right",
    size_percent: int = 30
) -> dict:
    """
    Overlay one video on top of another.
    """
    try:
        main = Path(main_video)
        overlay = Path(overlay_video)
        output = Path(output_path)

        # Validate inputs
        if not main.exists():
            raise FileNotFoundError(f"Main video not found: {main}")
        if not overlay.exists():
            raise FileNotFoundError(f"Overlay video not found: {overlay}")

        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

        # Calculate position coordinates
        # For simplicity, use basic positioning
        x_pos = "W-tw-10" if "right" in position else "10"
        y_pos = "H-th-10" if "bottom" in position else "10"

        # Calculate size
        size_filter = f"scale=iw*{size_percent/100}:ih*{size_percent/100}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(main),
            "-i", str(overlay),
            "-filter_complex",
            f"[1:v]{size_filter}[ovrl];[0:v][ovrl]overlay={x_pos}:{y_pos}",
            "-c:a", "copy",
            str(output)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg overlay failed: {result.stderr}")

        duration = get_duration(output)

        return {
            "success": True,
            "video": str(output),
            "duration": duration,
            "size": output.stat().st_size,
            "position": position,
            "size_percent": size_percent
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }