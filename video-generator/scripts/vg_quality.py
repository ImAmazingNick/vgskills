"""
Video quality functionality for vg CLI.

Video validation, analysis, and optimization.
"""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import subprocess
import json
import shutil
from array import array

from vg_common import VGError, classify_error, get_suggestion, get_duration, get_ffmpeg as _get_ffmpeg


def _read_audio_pcm(path: Path, max_seconds: int = 30, sample_rate: int = 8000) -> Optional[array]:
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        return None

    cmd = [
        ffmpeg, "-v", "error",
        "-i", str(path),
        "-ac", "1",
        "-ar", str(sample_rate),
        "-t", str(max_seconds),
        "-f", "s16le",
        "pipe:1"
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        return None
    data = array("h")
    data.frombytes(proc.stdout)
    return data


def _estimate_audio_sync_offset(
    video_path: Path,
    audio_path: Path,
    max_offset_ms: int = 2000,
    step_ms: int = 50
) -> Optional[float]:
    """Estimate sync offset between video audio and external audio."""
    video_pcm = _read_audio_pcm(video_path)
    audio_pcm = _read_audio_pcm(audio_path)
    if not video_pcm or not audio_pcm:
        return None

    sample_rate = 8000
    max_offset_samples = int(max_offset_ms * sample_rate / 1000)
    step_samples = max(1, int(step_ms * sample_rate / 1000))

    max_len = min(len(video_pcm), len(audio_pcm), sample_rate * 30)
    if max_len <= 0:
        return None

    best_offset = 0
    best_score = None

    def score_for_offset(offset: int) -> float:
        if offset >= 0:
            a = video_pcm[0:max_len - offset]
            b = audio_pcm[offset:max_len]
        else:
            a = video_pcm[-offset:max_len]
            b = audio_pcm[0:max_len + offset]
        if not a or not b:
            return -1.0
        num = sum(x * y for x, y in zip(a, b))
        den_a = sum(x * x for x in a) ** 0.5
        den_b = sum(y * y for y in b) ** 0.5
        if den_a == 0 or den_b == 0:
            return -1.0
        return num / (den_a * den_b)

    for offset in range(-max_offset_samples, max_offset_samples + 1, step_samples):
        score = score_for_offset(offset)
        if best_score is None or score > best_score:
            best_score = score
            best_offset = offset

    return round(best_offset * 1000 / sample_rate, 2)

def validate_video(file_path: str) -> dict:
    """
    Validate video/audio file integrity.
    """
    try:
        video = Path(file_path)

        if not video.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "code": "FILE_NOT_FOUND"
            }

        # Check file size
        size = video.stat().st_size
        if size == 0:
            return {
                "success": False,
                "error": "File is empty",
                "code": "VALIDATION",
                "valid": False,
                "issues": ["empty_file"],
                "score": 0.0
            }

        # Try to get basic info with ffprobe
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_name,codec_type,width,height,bit_rate,duration",
                "-of", "json",
                str(video)
            ], capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"FFprobe failed: {result.stderr}",
                    "code": "VALIDATION",
                    "valid": False,
                    "issues": ["corrupted_file"],
                    "score": 0.0
                }

            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            fps = None
            if video_stream:
                def _parse_fps(value):
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

            if not streams:
                return {
                    "success": False,
                    "error": "No streams found in file",
                    "code": "VALIDATION",
                    "valid": False,
                    "issues": ["no_streams"],
                    "score": 0.0
                }

            # Basic validation passed
            duration = get_duration(video)

            return {
                "success": True,
                "valid": True,
                "issues": [],
                "score": 1.0,
                "duration": duration,
                "size": size,
                "streams": len(streams),
                "video": {
                    "width": video_stream.get("width") if video_stream else None,
                    "height": video_stream.get("height") if video_stream else None,
                    "fps": round(fps, 3) if fps else None
                },
                "file_info": {
                    "path": str(video),
                    "type": video.suffix.lstrip('.'),
                    "size_mb": size / (1024 * 1024)
                }
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Validation timeout",
                "code": "TRANSIENT",
                "valid": False,
                "issues": ["timeout"],
                "score": 0.0
            }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def analyze_video(video_path: str, audio_path: Optional[str] = None) -> dict:
    """
    Analyze video quality and sync.
    """
    try:
        video = Path(video_path)
        audio = Path(audio_path) if audio_path else None

        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")
        if audio and not audio.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        # Get basic info
        video_duration = get_duration(video)
        audio_duration = get_duration(audio) if audio else None

        def _probe_streams(path: Path) -> Dict[str, Any]:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,start_time,duration",
                "-of", "json",
                str(path)
            ], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return {}
            data = json.loads(result.stdout)
            return data

        # Basic quality metrics
        quality_score = 0.9
        sync_drift_ms = 0.0

        recommendations = []
        if not audio and video.exists():
            try:
                stream_info = _probe_streams(video)
                audio_streams = [s for s in stream_info.get("streams", []) if s.get("codec_type") == "audio"]
                if audio_streams:
                    audio_duration = float(audio_streams[0].get("duration") or 0.0) or audio_duration
            except Exception:
                pass

        if video_duration and audio_duration:
            duration_diff = abs(video_duration - audio_duration)
            sync_drift_ms = round(duration_diff * 1000, 2)
            if duration_diff > 0.2:
                recommendations.append(f"Duration mismatch: video {video_duration:.2f}s, audio {audio_duration:.2f}s")
                quality_score -= 0.15

        # Probe stream start times when possible
        try:
            stream_info = _probe_streams(video)
            audio_streams = [s for s in stream_info.get("streams", []) if s.get("codec_type") == "audio"]
            video_streams = [s for s in stream_info.get("streams", []) if s.get("codec_type") == "video"]
            if audio_streams and video_streams:
                v_start = float(video_streams[0].get("start_time") or 0.0)
                a_start = float(audio_streams[0].get("start_time") or 0.0)
                start_offset_ms = abs(a_start - v_start) * 1000
                if start_offset_ms > 80:
                    recommendations.append(f"Audio start offset {start_offset_ms:.0f}ms vs video")
                    quality_score -= 0.1
        except Exception:
            pass

        # Estimate waveform-based sync offset if external audio provided
        waveform_offset_ms = None
        if audio and audio.exists():
            try:
                waveform_offset_ms = _estimate_audio_sync_offset(video, audio)
                if waveform_offset_ms is not None and abs(waveform_offset_ms) > 150:
                    recommendations.append(f"Waveform sync offset {waveform_offset_ms}ms (audio vs video)")
                    quality_score -= 0.15
            except Exception:
                waveform_offset_ms = None

        return {
            "success": True,
            "quality_score": max(0.0, quality_score),
            "sync_drift_ms": sync_drift_ms,
            "recommendations": recommendations,
            "video_duration": video_duration,
            "audio_duration": audio_duration,
            "analysis": {
                "has_audio": audio is not None,
                "duration_match": abs((video_duration or 0) - (audio_duration or 0)) < 0.2,
                "waveform_offset_ms": waveform_offset_ms
            }
        }

    except Exception as e:
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }

def optimize_video(
    input_path: str,
    output_path: str,
    target_size_mb: Optional[float] = None,
    quality: str = "high"
) -> dict:
    """
    Optimize/compress video with quality presets.
    """
    try:
        input_video = Path(input_path)
        output_video = Path(output_path)

        if not input_video.exists():
            raise FileNotFoundError(f"Input video not found: {input_video}")

        # Ensure output directory exists
        output_video.parent.mkdir(parents=True, exist_ok=True)

        # Quality presets
        presets = {
            "high": {"crf": 18, "preset": "slow", "target_mb": None},
            "medium": {"crf": 23, "preset": "medium", "target_mb": None},
            "low": {"crf": 28, "preset": "fast", "target_mb": None}
        }

        if quality not in presets:
            raise ValueError(f"Unknown quality preset: {quality}")

        preset = presets[quality]

        # Get input file size
        input_size = input_video.stat().st_size
        input_size_mb = input_size / (1024 * 1024)

        # Use real ffmpeg processing like the original scripts
        import subprocess

        # Ensure output has .mp4 extension
        if not str(output_video).endswith('.mp4'):
            output_video = output_video.with_suffix('.mp4')

        ffmpeg = _get_ffmpeg()
        if not ffmpeg:
            return {
                "success": False,
                "error": "ffmpeg not found. Required for video optimization.",
                "code": "CONFIG_ERROR",
                "suggestion": "Install ffmpeg: 'npm install ffmpeg-static' or install system ffmpeg"
            }

        # MP4 conversion using ffmpeg
            cmd = [
                ffmpeg, "-y",  # Overwrite output
                "-i", str(input_video),  # Input file
                "-c:v", "libx264",  # H.264 video codec
                "-preset", preset["preset"],  # Encoding preset
                "-crf", str(preset["crf"]),  # Quality (lower = better)
                "-c:a", "aac",  # AAC audio codec
                "-b:a", "128k",  # Audio bitrate
                "-movflags", "+faststart",  # Web optimization
                str(output_video)  # Output file
            ]

            # Add target size if specified
            if target_size_mb:
                # Calculate bitrate for target size (rough estimation)
                duration = 30  # Assume 30 seconds if we can't detect
                try:
                    # Try to get actual duration using ffprobe-like approach
                    probe_cmd = [ffmpeg, "-i", str(input_video)]
                    result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
                    import re
                    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
                    if match:
                        h, m, s = map(float, match.groups())
                        duration = h * 3600 + m * 60 + s
                except:
                    pass  # Use default duration

                if duration > 0:
                    target_bits = target_size_mb * 8 * 1024 * 1024  # Convert MB to bits
                    bitrate = int(target_bits / duration)  # Bits per second
                    cmd.insert(-1, "-b:v")  # Insert before output
                    cmd.insert(-1, f"{bitrate}")

            # Execute real ffmpeg conversion
            print(f"🎬 Converting {input_video.name} → {output_video.name} using ffmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                error_msg = f"FFmpeg conversion failed: {result.stderr[:500]}"
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            print(f"✅ Successfully converted to MP4!")

        # Get final output info
        output_size = output_video.stat().st_size
        output_size_mb = output_size / (1024 * 1024)
        compression_ratio = output_size / input_size if input_size > 0 else 1.0

        return {
            "success": True,
            "video": str(output_video),
            "original_size_mb": round(input_size_mb, 2),
            "compressed_size_mb": round(output_size_mb, 2),
            "compression_ratio": round(compression_ratio, 3),
            "quality": quality,
            "target_size_mb": target_size_mb,
            "settings": preset,
            "format": "mp4",
            "converted": True,
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