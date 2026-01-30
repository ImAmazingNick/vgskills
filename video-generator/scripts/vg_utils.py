"""
Utility functions for vg CLI.

File listing, info, cleanup, and status operations.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import shutil

from vg_common import get_file_info, get_duration, clear_cache, get_cache_stats

PROJECT_ROOT = Path(__file__).resolve().parent
VIDEOS_DIR = PROJECT_ROOT / "videos"
RUNS_DIR = VIDEOS_DIR / "runs"

def list_assets(asset_type: Optional[str] = None, recent_count: Optional[int] = None) -> dict:
    """
    List all video/audio assets.
    """
    try:
        assets = []

        # Search patterns based on type
        search_dirs = [VIDEOS_DIR]
        if asset_type == "video":
            patterns = ["*.mp4", "*.webm", "*.mov"]
        elif asset_type == "audio":
            patterns = ["*.mp3", "*.m4a", "*.wav"]
        elif asset_type == "timeline":
            patterns = ["*timeline*.json", "*timeline*.md"]
        else:
            patterns = ["*.mp4", "*.webm", "*.mov", "*.mp3", "*.m4a", "*.wav", "*timeline*.json", "*timeline*.md"]

        # Find files
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for pattern in patterns:
                for file_path in search_dir.rglob(pattern):
                    if file_path.is_file():
                        stat = file_path.stat()
                        assets.append({
                            "path": str(file_path),
                            "type": file_path.suffix.lstrip('.'),
                            "size": stat.st_size,
                            "created": stat.st_ctime,
                            "modified": stat.st_mtime,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2)
                        })

        # Sort by modification time (newest first)
        assets.sort(key=lambda x: x["modified"], reverse=True)

        # Limit to recent count if specified
        if recent_count:
            assets = assets[:recent_count]

        return {
            "success": True,
            "assets": assets,
            "total_count": len(assets),
            "total_size_mb": round(sum(a["size_mb"] for a in assets), 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNKNOWN"
        }

def get_asset_info(file_path: str) -> dict:
    """
    Get detailed information about a file.
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "code": "FILE_NOT_FOUND"
            }

        # Get basic file info
        info = get_file_info(path)

        # Add additional metadata
        stat = path.stat()
        info.update({
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "created_iso": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_iso": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_video": path.suffix.lower() in ['.mp4', '.webm', '.mov', '.avi'],
            "is_audio": path.suffix.lower() in ['.mp3', '.m4a', '.wav', '.aac']
        })

        # Try to get video-specific info with ffprobe
        if info["is_video"] or info["is_audio"]:
            try:
                import subprocess
                result = subprocess.run([
                    "ffprobe", "-v", "error",
                    "-show_entries", "stream=codec_name,codec_type,width,height,bit_rate,sample_rate,channels",
                    "-of", "json",
                    str(path)
                ], capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    import json
                    probe_data = json.loads(result.stdout)
                    info["streams"] = probe_data.get("streams", [])
            except Exception:
                pass  # ffprobe failed, continue without stream info

        return {
            "success": True,
            "info": info
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNKNOWN"
        }

def cleanup_assets(older_than_days: Optional[int] = None, dry_run: bool = False) -> dict:
    """
    Clean up old temporary files and cache.
    """
    try:
        deleted = []
        total_freed_bytes = 0

        # Define cleanup targets
        cleanup_patterns = [
            "**/*.tmp",
            "**/*.temp",
            "**/cache/**",
            "**/temp/**"
        ]

        # Find files to clean up
        for pattern in cleanup_patterns:
            for temp_file in VIDEOS_DIR.rglob(pattern.split('/')[-1]):
                if temp_file.is_file():
                    # Check age if specified
                    if older_than_days:
                        age_days = (datetime.now() - datetime.fromtimestamp(temp_file.stat().st_mtime)).days
                        if age_days < older_than_days:
                            continue

                    file_info = {
                        "path": str(temp_file),
                        "size": temp_file.stat().st_size,
                        "age_days": (datetime.now() - datetime.fromtimestamp(temp_file.stat().st_mtime)).days
                    }

                    if not dry_run:
                        temp_file.unlink(missing_ok=True)

                    deleted.append(file_info)
                    total_freed_bytes += file_info["size"]

        return {
            "success": True,
            "deleted": deleted,
            "total_deleted": len(deleted),
            "freed_bytes": total_freed_bytes,
            "freed_mb": round(total_freed_bytes / (1024 * 1024), 2),
            "dry_run": dry_run
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNKNOWN"
        }

def get_system_status() -> dict:
    """
    Get current system status and session info.
    """
    try:
        # Get disk usage for videos directory
        total, used, free = shutil.disk_usage(str(VIDEOS_DIR))

        # Count assets
        asset_counts = {}
        total_size = 0

        for asset in VIDEOS_DIR.rglob("*"):
            if asset.is_file():
                ext = asset.suffix.lower()
                asset_counts[ext] = asset_counts.get(ext, 0) + 1
                total_size += asset.stat().st_size

        # Get recent runs
        recent_runs = []
        if RUNS_DIR.exists():
            for run_dir in sorted(RUNS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if run_dir.is_dir():
                    recent_runs.append({
                        "name": run_dir.name,
                        "modified": run_dir.stat().st_mtime,
                        "modified_iso": datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat()
                    })
                    if len(recent_runs) >= 5:  # Limit to 5 most recent
                        break

        # Get cache stats
        cache_stats = get_cache_stats()

        return {
            "success": True,
            "status": {
                "videos_dir": str(VIDEOS_DIR),
                "disk_usage": {
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "usage_percent": round(used / total * 100, 1)
                },
                "assets": {
                    "counts": asset_counts,
                    "total_files": sum(asset_counts.values()),
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                },
                "cache": cache_stats,
                "recent_runs": recent_runs,
                "timestamp": datetime.now().isoformat()
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNKNOWN"
        }

def cache_clear(cache_type: Optional[str] = None, older_than_hours: Optional[int] = None) -> dict:
    """
    Clear cache entries.
    """
    try:
        removed_count = clear_cache(cache_type=cache_type, older_than_hours=older_than_hours)

        return {
            "success": True,
            "removed_count": removed_count,
            "cache_type": cache_type,
            "older_than_hours": older_than_hours
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNKNOWN"
        }

def cache_status() -> dict:
    """
    Get cache status and statistics.
    """
    try:
        stats = get_cache_stats()

        return {
            "success": True,
            "cache_stats": stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "UNKNOWN"
        }