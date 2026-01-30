"""
Post-processing helpers for recorded demo videos:
- Resolve ffmpeg (system or imageio-ffmpeg bundled)
- Convert Playwright WebM -> MP4
- Mux narration audio into MP4
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import re


def resolve_ffmpeg_cmd() -> list[str] | None:
    """Return ffmpeg command prefix, or None if unavailable."""
    # 1) System ffmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return ["ffmpeg"]
    except Exception:
        pass

    # 2) ffmpeg-static from node_modules
    project_root = Path(__file__).resolve().parent.parent.parent
    ffmpeg_static_path = project_root / "node_modules" / "ffmpeg-static" / "ffmpeg"
    if ffmpeg_static_path.exists():
        try:
            subprocess.run(
                [str(ffmpeg_static_path), "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return [str(ffmpeg_static_path)]
        except Exception:
            pass

    # 3) Bundled ffmpeg via imageio-ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe:
            return [exe]
    except Exception:
        pass

    return None


def ensure_mp4_from_webm(
    webm_path: Path,
    *,
    overwrite: bool = True,
    preset: str = "ultrafast",
    crf: str = "22",
) -> Path:
    """Convert a recorded .webm into .mp4 (H.264) and return the mp4 path."""
    if webm_path.suffix.lower() != ".webm":
        raise ValueError(f"Expected .webm input, got: {webm_path}")
    if not webm_path.exists():
        raise FileNotFoundError(str(webm_path))

    mp4_path = webm_path.with_suffix(".mp4")
    if mp4_path.exists() and mp4_path.stat().st_size > 0 and not overwrite:
        return mp4_path

    ffmpeg_cmd = resolve_ffmpeg_cmd()
    if not ffmpeg_cmd:
        raise RuntimeError(
            "ffmpeg not found. Install system ffmpeg or add imageio-ffmpeg."
        )

    cmd = [
        *ffmpeg_cmd,
        "-y" if overwrite else "-n",
        "-i",
        str(webm_path),
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-threads",
        "0",
        "-crf",
        crf,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(mp4_path),
    ]
    subprocess.run(cmd, check=True)

    if not mp4_path.exists() or mp4_path.stat().st_size == 0:
        raise RuntimeError("MP4 output not created.")

    return mp4_path


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def _duration_seconds_via_ffmpeg(ffmpeg_cmd: list[str], media_path: Path) -> float:
    """Return media duration by parsing `ffmpeg -i` stderr output."""
    proc = subprocess.run(
        [*ffmpeg_cmd, "-i", str(media_path)],
        capture_output=True,
        text=True,
    )
    haystack = (proc.stderr or "") + "\n" + (proc.stdout or "")
    m = _DURATION_RE.search(haystack)
    if not m:
        raise RuntimeError(f"Could not parse duration for {media_path.name}")
    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = float(m.group(3))
    return hh * 3600 + mm * 60 + ss


def duration_seconds(media_path: Path) -> float:
    """Public helper: duration in seconds (ffmpeg -i parse)."""
    ffmpeg_cmd = resolve_ffmpeg_cmd()
    if not ffmpeg_cmd:
        raise RuntimeError("ffmpeg not found.")
    return _duration_seconds_via_ffmpeg(ffmpeg_cmd, media_path)


def mux_audio_into_mp4(
    *,
    video_mp4: Path,
    audio_path: Path,
    out_mp4: Path,
    overwrite: bool = True,
) -> Path:
    """Mux narration audio into MP4 and return out_mp4."""
    if not video_mp4.exists():
        raise FileNotFoundError(str(video_mp4))
    if not audio_path.exists():
        raise FileNotFoundError(str(audio_path))

    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_cmd = resolve_ffmpeg_cmd()
    if not ffmpeg_cmd:
        raise RuntimeError("ffmpeg not found.")

    video_dur = _duration_seconds_via_ffmpeg(ffmpeg_cmd, video_mp4)

    cmd = [
        *ffmpeg_cmd,
        "-y" if overwrite else "-n",
        "-i",
        str(video_mp4),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-filter_complex",
        f"[1:a]apad,atrim=0:{video_dur:.3f}[a]",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]

    subprocess.run(cmd, check=True)

    if not out_mp4.exists() or out_mp4.stat().st_size == 0:
        raise RuntimeError("Muxed MP4 output not created.")

    return out_mp4
