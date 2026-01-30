from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    run_dir: Path
    raw_dir: Path
    audio_dir: Path

    @property
    def timeline_json(self) -> Path:
        return self.run_dir / "timeline.json"

    @property
    def timeline_md(self) -> Path:
        return self.run_dir / "timeline.md"


def project_root() -> Path:
    # From video-generator/scripts/, go up to project root
    return Path(__file__).resolve().parent.parent.parent


def videos_dir() -> Path:
    return project_root() / "videos"


def runs_dir() -> Path:
    return videos_dir() / "runs"


def run_paths(run_id: str) -> RunPaths:
    rd = runs_dir() / run_id
    return RunPaths(
        run_id=run_id,
        run_dir=rd,
        raw_dir=rd / "raw",
        audio_dir=rd / "audio",
    )


def guess_run_id_from_stem(video_stem: str) -> str:
    """Derive run_id from video filename stem."""
    return video_stem


def run_paths_for_video_stem(video_stem: str) -> RunPaths:
    return run_paths(guess_run_id_from_stem(video_stem))


def find_latest_run_video() -> Optional[Path]:
    """Return newest video under videos/runs/**/raw (webm/mp4), else None."""
    base = runs_dir()
    if not base.exists():
        return None

    candidates = []
    for ext in ("*.mp4", "*.webm"):
        candidates.extend(base.glob(f"*/raw/{ext}"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

