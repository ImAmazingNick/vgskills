"""
Shared utilities for vg CLI.

Error classification, path handling, caching, and media utilities.
"""

import hashlib
from pathlib import Path
from typing import Any, Optional, Union
import subprocess
import json
import os

# Error classification
class VGError(Exception):
    code = "UNKNOWN"
    suggestion = ""

class TransientError(VGError):
    """Errors that may succeed on retry."""
    code = "TRANSIENT"

class ValidationError(VGError):
    """Input validation errors."""
    code = "VALIDATION"

class ConfigError(VGError):
    """Configuration/setup errors."""
    code = "CONFIG"

class AuthError(VGError):
    """Authentication errors."""
    code = "AUTH_ERROR"

def classify_error(e: Exception) -> str:
    """Classify error for structured output."""
    error_str = str(e).lower()

    if "api" in error_str or "timeout" in error_str or "connection" in error_str:
        return "TRANSIENT"
    elif "not found" in error_str or "missing" in error_str:
        return "FILE_NOT_FOUND"
    elif "invalid" in error_str or "format" in error_str:
        return "VALIDATION"
    elif "key" in error_str or "auth" in error_str or "unauthorized" in error_str:
        return "AUTH_ERROR"
    else:
        return "UNKNOWN"

def get_suggestion(e: Exception) -> str:
    """Get actionable suggestion for error."""
    code = classify_error(e)

    suggestions = {
        "TRANSIENT": "This may be a temporary issue. Try again in a few seconds.",
        "FILE_NOT_FOUND": "Check that the input file path is correct and the file exists.",
        "VALIDATION": "Check the input parameters and file formats.",
        "AUTH_ERROR": "Check your authentication credentials and API keys.",
        "UNKNOWN": "Check the error message for details."
    }

    return suggestions.get(code, suggestions["UNKNOWN"])

def error_response(e: Exception, context: str = "") -> dict:
    """
    Create standardized error response dict from exception.
    
    Use this in command handlers to ensure consistent error format.
    
    Args:
        e: The exception that was raised
        context: Optional context about what operation failed
    
    Returns:
        Standardized error dict with success, error, code, suggestion
    """
    error_code = classify_error(e)
    error_msg = f"{context}: {str(e)}" if context else str(e)
    
    return {
        "success": False,
        "error": error_msg,
        "code": error_code,
        "suggestion": get_suggestion(e)
    }

def success_response(**kwargs) -> dict:
    """
    Create standardized success response dict.
    
    Args:
        **kwargs: Additional fields to include in response
    
    Returns:
        Dict with success=True and any additional fields
    """
    return {"success": True, **kwargs}

# Caching utilities
CACHE_DIR = Path.home() / ".cache" / "vg"
CACHE_METADATA_FILE = CACHE_DIR / "cache_metadata.json"

def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_METADATA_FILE.exists():
        CACHE_METADATA_FILE.write_text("{}")

def cache_key(content: str, *args) -> str:
    """Generate cache key from content."""
    key_data = content + "".join(str(a) for a in args)
    return hashlib.md5(key_data.encode()).hexdigest()[:16]

def load_cache_metadata() -> dict:
    """Load cache metadata."""
    ensure_cache_dir()
    try:
        return json.loads(CACHE_METADATA_FILE.read_text())
    except Exception:
        return {}

def save_cache_metadata(metadata: dict):
    """Save cache metadata."""
    ensure_cache_dir()
    CACHE_METADATA_FILE.write_text(json.dumps(metadata, indent=2, default=str))

def get_cached(cache_type: str, key: str) -> Optional[Path]:
    """Get cached file if exists and not expired."""
    cache_path = CACHE_DIR / cache_type / f"{key}.cache"
    if not cache_path.exists():
        return None

    # Check metadata for expiration (24 hours default)
    metadata = load_cache_metadata()
    cache_entry = metadata.get(f"{cache_type}/{key}", {})
    created = cache_entry.get("created")

    if created:
        import time
        age_hours = (time.time() - created) / 3600
        if age_hours > 24:  # Expire after 24 hours
            # Remove expired cache
            cache_path.unlink(missing_ok=True)
            metadata.pop(f"{cache_type}/{key}", None)
            save_cache_metadata(metadata)
            return None

    return cache_path

def save_to_cache(cache_type: str, key: str, source: Path, metadata: dict = None) -> Path:
    """Save file to cache with metadata."""
    cache_dir = CACHE_DIR / cache_type
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{key}.cache"

    import shutil
    shutil.copy(source, cache_path)

    # Update metadata
    cache_metadata = load_cache_metadata()
    cache_key_full = f"{cache_type}/{key}"
    cache_metadata[cache_key_full] = {
        "created": source.stat().st_ctime,
        "size": source.stat().st_size,
        "source_path": str(source),
        **(metadata or {})
    }
    save_cache_metadata(cache_metadata)

    return cache_path

def clear_cache(cache_type: Optional[str] = None, older_than_hours: Optional[int] = None):
    """Clear cache files."""
    import time

    metadata = load_cache_metadata()
    to_remove = []

    for cache_key_full, cache_info in metadata.items():
        if cache_type and not cache_key_full.startswith(f"{cache_type}/"):
            continue

        cache_path = CACHE_DIR / cache_key_full.replace("/", "/") / f"{cache_key_full.split('/')[-1]}.cache"

        # Check age
        if older_than_hours:
            age_hours = (time.time() - cache_info.get("created", 0)) / 3600
            if age_hours < older_than_hours:
                continue

        # Remove file and metadata
        cache_path.unlink(missing_ok=True)
        to_remove.append(cache_key_full)

    # Update metadata
    for key in to_remove:
        metadata.pop(key, None)
    save_cache_metadata(metadata)

    return len(to_remove)

def get_cache_stats() -> dict:
    """Get cache statistics."""
    metadata = load_cache_metadata()
    total_size = 0
    type_counts = {}
    expired_count = 0

    import time
    current_time = time.time()

    for cache_key_full, cache_info in metadata.items():
        cache_type = cache_key_full.split("/")[0]
        type_counts[cache_type] = type_counts.get(cache_type, 0) + 1
        total_size += cache_info.get("size", 0)

        # Check if expired
        age_hours = (current_time - cache_info.get("created", 0)) / 3600
        if age_hours > 24:
            expired_count += 1

    return {
        "total_entries": len(metadata),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "by_type": type_counts,
        "expired_count": expired_count
    }

# Media utilities
def get_duration(file_path: Path) -> float:
    """Get duration of audio/video file.
    
    Uses ffmpeg stderr parsing (works without ffprobe).
    Falls back to ffprobe if available.
    """
    import re
    
    # Try ffmpeg first (more reliable - uses get_ffmpeg() resolution)
    ffmpeg = get_ffmpeg()
    if ffmpeg:
        try:
            result = subprocess.run(
                [ffmpeg, "-i", str(file_path)],
                capture_output=True, text=True, timeout=10
            )
            # Parse duration from stderr: "Duration: 00:04:49.88"
            match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', result.stderr)
            if match:
                hours, minutes, seconds = match.groups()
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except Exception:
            pass
    
    # Fallback to ffprobe if available
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(file_path)
        ], capture_output=True, text=True, timeout=10)

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 0.0

def get_file_info(file_path: Path) -> dict:
    """Get comprehensive file info."""
    if not file_path.exists():
        return {"exists": False}

    info = {
        "exists": True,
        "path": str(file_path),
        "size": file_path.stat().st_size,
        "type": file_path.suffix.lstrip('.')
    }

    if file_path.suffix in ['.mp4', '.webm', '.mp3', '.m4a', '.wav']:
        info["duration"] = get_duration(file_path)
        # Add video stream details (resolution, fps) when available
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,width,height,avg_frame_rate,r_frame_rate",
                "-of", "json",
                str(file_path)
            ], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get("streams", [])
                video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                if video_stream:
                    width = video_stream.get("width")
                    height = video_stream.get("height")

                    def _parse_fps(value: Optional[str]) -> Optional[float]:
                        if not value or value == "0/0":
                            return None
                        if "/" in value:
                            num, den = value.split("/", 1)
                            try:
                                num_f = float(num)
                                den_f = float(den)
                                return num_f / den_f if den_f else None
                            except ValueError:
                                return None
                        try:
                            return float(value)
                        except ValueError:
                            return None

                    fps = _parse_fps(video_stream.get("avg_frame_rate")) or _parse_fps(video_stream.get("r_frame_rate"))
                    info["video"] = {
                        "width": width,
                        "height": height,
                        "fps": round(fps, 3) if fps else None
                    }
        except Exception:
            pass

    return info

# FFmpeg resolution - consolidated from multiple implementations
def get_ffmpeg() -> Optional[str]:
    """
    Get path to ffmpeg binary with comprehensive fallback strategy.
    
    Tries in order:
    1. System ffmpeg (via PATH)
    2. node_modules/ffmpeg-static (project root)
    3. node_modules/ffmpeg-static (alternative locations)
    4. imageio-ffmpeg bundled binary
    
    Returns:
        Path to ffmpeg binary or None if not found
    """
    # 1. Try system ffmpeg first (most reliable)
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=2
        )
        return "ffmpeg"
    except Exception:
        pass
    
    # 2. Try node_modules/ffmpeg-static (from project root)
    project_root = Path(__file__).resolve().parent.parent.parent
    node_ffmpeg = project_root / "node_modules" / "ffmpeg-static" / "ffmpeg"
    if node_ffmpeg.exists() and node_ffmpeg.stat().st_size > 1000000:  # At least 1MB
        try:
            subprocess.run(
                [str(node_ffmpeg), "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=2
            )
            return str(node_ffmpeg)
        except Exception:
            pass
    
    # 3. Try alternative node_modules paths
    alternative_paths = [
        Path(__file__).parent.parent / "node_modules" / "ffmpeg-static" / "ffmpeg",
        Path.home() / "node_modules" / "ffmpeg-static" / "ffmpeg",
        Path("/usr/local/lib/node_modules/ffmpeg-static/ffmpeg"),
    ]
    for alt_path in alternative_paths:
        if alt_path.exists() and alt_path.stat().st_size > 1000000:
            try:
                subprocess.run(
                    [str(alt_path), "-version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=2
                )
                return str(alt_path)
            except Exception:
                pass
    
    # 4. Try imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except ImportError:
        pass
    except Exception:
        pass
    
    return None


def require_ffmpeg() -> str:
    """
    Get ffmpeg path or raise error if not found.
    
    Returns:
        Path to ffmpeg binary
        
    Raises:
        RuntimeError: If ffmpeg is not found
    """
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Install via: 'npm install ffmpeg-static' or install system ffmpeg"
        )
    return ffmpeg


# Path normalization
def normalize_path(path: Union[str, Path], must_exist: bool = False) -> Path:
    """Normalize path to absolute Path object."""
    p = Path(path).expanduser().resolve()
    if must_exist and not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p

# Environment variable validation
ENV_VARS = {
    "ELEVENLABS_API_KEY": {"required_for": ["audio.tts"], "optional": False},
    "FAL_API_KEY": {"required_for": ["talking-head.generate"], "optional": False},
    "DTS_SESSIONID": {"required_for": ["record"], "optional": True}
}

def validate_env_for_command(command: str) -> dict:
    """Validate required env vars for a command."""
    missing = []
    for var, config in ENV_VARS.items():
        if command in config.get("required_for", []):
            if not os.environ.get(var) and not config.get("optional"):
                missing.append(var)

    if missing:
        return {
            "success": False,
            "error": f"Missing required environment variables: {', '.join(missing)}",
            "code": "CONFIG_ERROR",
            "suggestion": f"Set these environment variables: {', '.join(missing)}"
        }
    return {"success": True}