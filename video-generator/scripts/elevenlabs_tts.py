"""
ElevenLabs Text-to-Speech helper.

Security:
- Reads API key from ELEVENLABS_API_KEY env var (or explicit arg).
- Never logs secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

import requests


@dataclass(frozen=True)
class ElevenLabsTtsConfig:
    api_key: str
    voice_id: str
    model_id: str = "eleven_multilingual_v2"
    output_format: str = "mp3_44100_128"
    base_url: str = "https://api.elevenlabs.io"


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def load_elevenlabs_config(
    *,
    api_key: Optional[str] = None,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    output_format: Optional[str] = None,
) -> ElevenLabsTtsConfig:
    api_key = api_key or _env("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing ElevenLabs API key. Set ELEVENLABS_API_KEY in your environment."
        )

    # Default voice id: ElevenLabs historically provides a common demo voice id.
    # You can (and should) set ELEVENLABS_VOICE_ID explicitly for your account.
    voice_id = voice_id or _env("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"

    model_id = model_id or _env("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2"
    output_format = output_format or _env("ELEVENLABS_OUTPUT_FORMAT") or "mp3_44100_128"

    return ElevenLabsTtsConfig(
        api_key=api_key,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
    )


def synthesize_to_file(
    *,
    text: str,
    out_path: Path,
    config: Optional[ElevenLabsTtsConfig] = None,
    timeout_s: int = 30,
) -> Path:
    """
    Generate narration audio from text and write it to out_path.

    Returns the written file path.
    """
    if not text or not text.strip():
        raise ValueError("TTS text is empty.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    config = config or load_elevenlabs_config()

    url = f"{config.base_url}/v1/text-to-speech/{config.voice_id}"
    params = {"output_format": config.output_format}
    headers = {
        "xi-api-key": config.api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    payload = {
        "text": text,
        "model_id": config.model_id,
    }

    resp = requests.post(url, params=params, headers=headers, json=payload, timeout=timeout_s, stream=True)
    if resp.status_code >= 400:
        # Avoid printing headers (contains the key).
        raise RuntimeError(
            f"ElevenLabs TTS failed: HTTP {resp.status_code} - {resp.text[:500]}"
        )

    out_path.write_bytes(resp.content)
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("TTS output was not written or is empty.")

    return out_path

