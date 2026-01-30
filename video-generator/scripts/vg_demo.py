"""
Demo/mock implementations for testing the video generator pipeline.

Creates dummy audio and video files to demonstrate the complete workflow.
"""

import os
from pathlib import Path
from typing import Optional

def create_demo_voiceover(text: str, output_path: str, voice: str = "alloy") -> dict:
    """
    Create a demo voiceover file (mock TTS).
    In real usage, this would call ElevenLabs API.
    """
    try:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Create a dummy audio file with some basic content
        # In real implementation, this would be actual audio from TTS API
        dummy_content = f"Mock audio for: {text[:50]}... (Voice: {voice})"
        output.write_text(dummy_content)

        # Mock duration calculation (roughly 150 words per minute)
        word_count = len(text.split())
        estimated_duration = word_count / 150 * 60  # seconds

        return {
            "success": True,
            "audio": str(output),
            "duration": estimated_duration,
            "size": len(dummy_content),
            "voice_id": voice,
            "text_length": len(text),
            "mock": True
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "MOCK_ERROR"
        }

def create_demo_talking_head(audio_path: str, output_path: str, model: str = "omnihuman") -> dict:
    """
    Create a demo talking head video (mock generation).
    In real usage, this would call FAL.ai API.
    """
    try:
        audio = Path(audio_path)
        output = Path(output_path)

        if not audio.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        output.parent.mkdir(parents=True, exist_ok=True)

        # Create a dummy video file
        # In real implementation, this would be actual video from AI generation
        dummy_content = f"Mock talking head video based on audio: {audio.name} (Model: {model})"
        output.write_text(dummy_content)

        # Mock duration (same as audio)
        mock_duration = 5.0  # placeholder

        return {
            "success": True,
            "video": str(output),
            "duration": mock_duration,
            "size": len(dummy_content),
            "model": model,
            "audio_source": str(audio),
            "mock": True
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "MOCK_ERROR"
        }

def create_demo_composition(video_path: str, audio_path: str, output_path: str) -> dict:
    """
    Create a demo composition (mock sync).
    In real usage, this would use ffmpeg to mux audio and video.
    """
    try:
        video = Path(video_path)
        audio = Path(audio_path)
        output = Path(output_path)

        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")
        if not audio.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        output.parent.mkdir(parents=True, exist_ok=True)

        # Create a dummy composed file
        dummy_content = f"Mock composed video: {video.name} + {audio.name}"
        output.write_text(dummy_content)

        return {
            "success": True,
            "video": str(output),
            "original_video": str(video),
            "audio_track": str(audio),
            "duration": 10.0,  # placeholder
            "size": len(dummy_content),
            "method": "demo_composition",
            "mock": True
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "MOCK_ERROR"
        }