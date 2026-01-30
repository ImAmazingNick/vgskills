"""
TTS functionality for vg CLI.

ElevenLabs TTS integration with caching.
"""

from pathlib import Path
from typing import Optional
import os
import hashlib

from vg_common import VGError, classify_error, get_suggestion, get_duration, cache_key, get_cached, save_to_cache
from vg_cost import estimate_tts_cost, log_cost_entry

# Try to import ElevenLabs - optional dependency
try:
    from elevenlabs import generate, save, set_api_key
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

def tts_with_json_output(
    text: str,
    output_path: Path,
    voice_id: Optional[str] = None,
    use_cache: bool = True
) -> dict:
    """
    Generate TTS audio with structured JSON output and CONTENT-BASED caching.
    
    Requires ELEVENLABS_API_KEY environment variable.
    Uses MD5 hash of text+voice for cache key to avoid redundant API calls.

    Returns dict suitable for CLI output.
    """
    try:
        # Validate input
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        voice_id = voice_id or "alloy"

        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate content-based cache key (like previous powerful solution)
        cache_key_text = f"{text.strip()}|{voice_id}".lower()
        cache_key_hash = hashlib.md5(cache_key_text.encode()).hexdigest()[:16]

        # Check cache first if enabled
        if use_cache:
            cached_file = get_cached("tts", cache_key_hash)
            if cached_file and cached_file.exists():
                # Use cached audio
                import shutil
                shutil.copy(cached_file, output_path)

                duration = get_duration(output_path)
                size = output_path.stat().st_size

                return {
                    "success": True,
                    "audio": str(output_path),
                    "path": str(output_path),  # Alias for agentic workflows
                    "duration": duration,
                    "duration_s": duration,  # Explicit seconds for agentic workflows
                    "size": size,
                    "voice_id": voice_id,
                    "text_length": len(text),
                    "characters": len(text),  # Alias for agentic workflows
                    "cached": True,
                    "cache_key": cache_key_hash,
                    "cost": 0.0,  # No cost for cached results
                    "cost_currency": "USD",
                    "mode": "cached"
                }

        # REQUIRE real ElevenLabs API key - reject demo/example keys
        api_key = os.getenv("ELEVENLABS_API_KEY")

        if not api_key:
            return {
                "success": False,
                "error": "ELEVENLABS_API_KEY not set. Real API key required for production audio generation.",
                "code": "MISSING_API_KEY",
                "suggestion": "Set ELEVENLABS_API_KEY environment variable with a real ElevenLabs API key"
            }

        # Reject known demo/example keys (temporarily allow .env.example key for testing)
        demo_keys = ["demo_key"]  # Temporarily removed the .env.example key for testing
        if api_key in demo_keys:
            return {
                "success": False,
                "error": f"ELEVENLABS_API_KEY is a demo/example key. Real API key required for production audio generation.",
                "code": "DEMO_KEY_REJECTED",
                "suggestion": "Replace with a real ElevenLabs API key from https://elevenlabs.io/app/profile"
            }

        # Use REAL ElevenLabs API only
        from elevenlabs_tts import synthesize_to_file, load_elevenlabs_config

        config = load_elevenlabs_config(voice_id=voice_id)
        result_path = synthesize_to_file(text=text, out_path=output_path, config=config)

        # Get actual file info
        actual_size = result_path.stat().st_size
        duration = get_duration(result_path)

        # Calculate cost (ElevenLabs charges ~$0.30 per 1000 characters)
        cost = len(text) * 0.0003

        # Save to cache for future use
        if use_cache:
            save_to_cache("tts", cache_key_hash, result_path, {
                "text_hash": hashlib.md5(text.strip().encode()).hexdigest(),
                "voice_id": voice_id,
                "text_length": len(text),
                "cost": cost
            })

        # Log cost
        log_cost_entry("elevenlabs_tts", cost, {"voice_id": voice_id, "text_length": len(text)})

        return {
            "success": True,
            "audio": str(result_path),
            "path": str(result_path),  # Alias for agentic workflows
            "duration": duration,
            "duration_s": duration,  # Explicit seconds for agentic workflows
            "size": actual_size,
            "voice_id": config.voice_id,
            "text_length": len(text),
            "characters": len(text),  # Alias for agentic workflows
            "cached": False,
            "cache_key": cache_key_hash,
            "cost": round(cost, 4),
            "cost_currency": "USD",
            "mode": "production"
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def batch_tts(
    segments: list,
    output_dir: Path,
    voice_id: Optional[str] = None
) -> dict:
    """
    Generate TTS for multiple segments.

    segments: List of dicts with 'text' and optional 'id' keys
    """
    results = []
    total_duration = 0
    total_size = 0

    try:
        config = load_elevenlabs_config(voice_id=voice_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, segment in enumerate(segments):
            segment_id = segment.get('id', f"segment_{i+1}")
            text = segment.get('text', '').strip()

            if not text:
                results.append({
                    "id": segment_id,
                    "success": False,
                    "error": "Empty text",
                    "code": "VALIDATION"
                })
                continue

            output_path = output_dir / f"{segment_id}.mp3"

            try:
                result_path = synthesize_to_file(
                    text=text,
                    out_path=output_path,
                    config=config
                )

                duration = get_duration(result_path)
                size = result_path.stat().st_size

                results.append({
                    "id": segment_id,
                    "success": True,
                    "audio": str(result_path),
                    "duration": duration,
                    "size": size,
                    "text_length": len(text)
                })

                total_duration += duration
                total_size += size

            except Exception as e:
                results.append({
                    "id": segment_id,
                    "success": False,
                    "error": str(e),
                    "code": classify_error(e)
                })

        return {
            "success": True,
            "segments": results,
            "total_segments": len(segments),
            "successful_segments": sum(1 for r in results if r["success"]),
            "total_duration": total_duration,
            "total_size": total_size,
            "voice_id": config.voice_id
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": classify_error(e),
            "suggestion": get_suggestion(e)
        }