#!/usr/bin/env python3
"""
Generate real talking head videos using fal.ai API.

Supports multiple models:
- omnihuman: ByteDance OmniHuman v1.5 - High quality, full expressions
- sadtalker: SadTalker - Faster, lip-sync focused

Requires:
- FAL_API_KEY environment variable
- Audio segments already generated (MP3 files)
"""

import os
import sys
import json
import time
import base64
import subprocess
from pathlib import Path

# Try fal_client first, fall back to requests
try:
    import fal_client
    USE_FAL_CLIENT = True
    print("✅ Using fal_client library")
except ImportError:
    import requests
    USE_FAL_CLIENT = False
    print("⚠️  Using requests fallback (fal_client not found)")


# Configuration
FAL_API_KEY = os.environ.get("FAL_API_KEY", "")
PROJECT_DIR = Path(__file__).parent.parent
VIDEOS_DIR = PROJECT_DIR / "videos"
TALKING_HEAD_DIR = VIDEOS_DIR / "talking_heads"


def ensure_dirs():
    """Create necessary directories."""
    TALKING_HEAD_DIR.mkdir(parents=True, exist_ok=True)


def generate_character_image(force_regenerate: bool = False, style: str = "portrait") -> str:
    """Generate a presenter character image using fal.ai.
    
    Args:
        force_regenerate: Force regeneration even if cached image exists
        style: "portrait" for square face (overlays) or "studio" for fullscreen YouTuber studio
    
    Returns:
        Path to generated character image
    """
    if style == "studio":
        return generate_studio_character_image(force_regenerate)
    
    print("🎨 Generating realistic friendly presenter character...")
    
    character_path = TALKING_HEAD_DIR / "presenter_character_v2.png"
    
    # Check if we already have a character (unless forcing regeneration)
    if not force_regenerate and character_path.exists() and character_path.stat().st_size > 0:
        print(f"   ✅ Using existing character: {character_path}")
        return str(character_path)
    
    # Improved prompt for realistic, friendly, non-corporate look
    prompt = """Beautiful young woman with warm friendly smile, front-facing portrait photo,
    natural casual look, relaxed neutral expression with lips slightly parted,
    looking directly at camera with genuine warmth,
    soft natural lighting, clean simple background,
    photorealistic high resolution portrait, sharp facial features,
    casual comfortable clothing, approachable and trustworthy appearance,
    perfect for video presentation, cinematic quality photo"""
    
    if USE_FAL_CLIENT:
        os.environ["FAL_KEY"] = FAL_API_KEY
        
        result = fal_client.subscribe(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "square",
                "num_images": 1,
            },
        )
        
        image_url = result["images"][0]["url"]
        
        # Download the image
        import urllib.request
        urllib.request.urlretrieve(image_url, str(character_path))
    else:
        import requests
        headers = {
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://queue.fal.run/fal-ai/flux/schnell",
            headers=headers,
            json={
                "prompt": prompt,
                "image_size": "square",
                "num_images": 1,
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            image_url = result["images"][0]["url"]
            img_response = requests.get(image_url, timeout=60)
            character_path.write_bytes(img_response.content)
        else:
            raise Exception(f"Failed to generate character: {response.text}")
    
    print(f"   ✅ Character saved to: {character_path}")
    return str(character_path)


def generate_studio_character_image(force_regenerate: bool = False) -> str:
    """Generate a fullscreen YouTuber studio character image for intro/outro/segment.
    
    Creates a realistic presenter in a professional YouTuber studio setting,
    suitable for fullscreen talking head segments (not overlays).
    
    Returns:
        Path to generated studio character image (landscape 16:9)
    """
    print("🎨 Generating YouTuber studio presenter character...")
    
    character_path = TALKING_HEAD_DIR / "presenter_studio.png"
    
    # Check if we already have a studio character (unless forcing regeneration)
    if not force_regenerate and character_path.exists() and character_path.stat().st_size > 0:
        print(f"   ✅ Using existing studio character: {character_path}")
        return str(character_path)
    
    # Prompt for fullscreen YouTuber studio scene
    prompt = """Professional YouTuber in modern studio setup, front-facing view,
    beautiful young woman content creator sitting at desk with microphone,
    warm friendly smile, looking directly at camera,
    professional studio lighting with soft key light,
    modern minimalist studio background with subtle RGB accent lighting,
    high-end camera quality, shallow depth of field,
    clean professional setup like popular tech YouTuber,
    casual but polished appearance, confident and engaging presence,
    photorealistic 4K quality, cinematic color grading,
    upper body visible, natural relaxed posture,
    professional podcast or video studio aesthetic"""
    
    if USE_FAL_CLIENT:
        os.environ["FAL_KEY"] = FAL_API_KEY
        
        result = fal_client.subscribe(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "landscape_16_9",  # Fullscreen 16:9 aspect ratio
                "num_images": 1,
            },
        )
        
        image_url = result["images"][0]["url"]
        
        # Download the image
        import urllib.request
        urllib.request.urlretrieve(image_url, str(character_path))
    else:
        import requests
        headers = {
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://queue.fal.run/fal-ai/flux/schnell",
            headers=headers,
            json={
                "prompt": prompt,
                "image_size": "landscape_16_9",  # Fullscreen 16:9 aspect ratio
                "num_images": 1,
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            image_url = result["images"][0]["url"]
            img_response = requests.get(image_url, timeout=60)
            character_path.write_bytes(img_response.content)
        else:
            raise Exception(f"Failed to generate studio character: {response.text}")
    
    print(f"   ✅ Studio character saved to: {character_path}")
    return str(character_path)


def generate_talking_head_video(character_image: str, audio_path: str, output_path: str, 
                                model: str = "omnihuman") -> str:
    """Generate lip-synced talking head video from character image and audio."""
    print(f"🎬 Generating talking head video for: {Path(audio_path).name}")
    print(f"   🤖 Model: {model.upper()}")
    
    output_file = Path(output_path)
    
    # Check if already exists
    if output_file.exists() and output_file.stat().st_size > 10000:
        print(f"   ✅ Using existing video: {output_file}")
        return str(output_file)
    
    if USE_FAL_CLIENT:
        os.environ["FAL_KEY"] = FAL_API_KEY
        
        # For models that don't support data URLs, upload files to fal storage
        if model == "omnihuman":
            print("   📤 Uploading files to fal.ai storage...")
            
            # Upload image - read as bytes first
            with open(character_image, "rb") as f:
                image_bytes = f.read()
            image_url = fal_client.upload(image_bytes, "image/png")
            print(f"   ✅ Image uploaded")
            
            # Upload audio - read as bytes first
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            audio_url = fal_client.upload(audio_bytes, "audio/mp3")
            print(f"   ✅ Audio uploaded")
        else:
            # For SadTalker, use data URLs
            with open(audio_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode("utf-8")
            audio_url = f"data:audio/mp3;base64,{audio_base64}"
            
            with open(character_image, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
            image_url = f"data:image/png;base64,{image_base64}"
        
        # Retry logic for API errors
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if model == "omnihuman":
                    print("   ⏳ Submitting to fal.ai OmniHuman v1.5 (high quality)...")
                    print("   📊 Settings: 720p, full expressions, semantic gestures")
                    
                    result = fal_client.subscribe(
                        "fal-ai/bytedance/omnihuman/v1.5",
                        arguments={
                            "image_url": image_url,
                            "audio_url": audio_url,
                            "resolution": "720p",
                            "turbo_mode": False,
                        },
                    )
                    video_url = result.get("video", {}).get("url") or result.get("video_url") or result.get("output", {}).get("url")
                    
                else:
                    print("   ⏳ Submitting to fal.ai SadTalker (fast mode)...")
                    
                    result = fal_client.subscribe(
                        "fal-ai/sadtalker",
                        arguments={
                            "source_image_url": image_url,
                            "driven_audio_url": audio_url,
                            "face_model_resolution": "512",
                            "expression_scale": 1.3,
                            "face_enhancer": "gfpgan",
                            "preprocess": "crop",
                            "still_mode": False,
                            "pose_style": 0,
                        },
                    )
                    video_url = result.get("video", {}).get("url") or result.get("video_url")
                
                break
            except Exception as e:
                last_error = e
                print(f"   ⚠️ Attempt {attempt + 1}/{max_retries} failed: {str(e)[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue
        else:
            raise Exception(f"All {max_retries} attempts failed. Last error: {last_error}")
        
        if not video_url:
            raise Exception(f"No video URL in result")
        
        # Download the video
        import urllib.request
        urllib.request.urlretrieve(video_url, str(output_file))
    
    print(f"   ✅ Video saved to: {output_file}")
    return str(output_file)


def get_ffmpeg_path() -> str:
    """Get the path to ffmpeg binary."""
    node_ffmpeg = Path(__file__).parent.parent.parent / "node_modules" / "ffmpeg-static" / "ffmpeg"
    if node_ffmpeg.exists():
        return str(node_ffmpeg)
    
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    
    return "ffmpeg"


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffmpeg."""
    ffmpeg = get_ffmpeg_path()
    
    result = subprocess.run(
        [ffmpeg, "-i", video_path],
        capture_output=True, text=True
    )
    
    import re
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if match:
        hours, minutes, seconds = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    
    return 5.0


def integrate_talking_head_into_video(
    main_video: str,
    talking_head_video: str,
    output_video: str,
    start_time: float,
    position: str = "bottom-right",
    size_px: int = 280
) -> str:
    """Overlay talking head video onto main video at specified timestamp."""
    print(f"🎬 Integrating talking head at {start_time:.1f}s (size: {size_px}px)...")
    
    th_duration = get_video_duration(talking_head_video)
    print(f"   Talking head duration: {th_duration:.1f}s")
    
    margin = 20
    if position == "bottom-right":
        overlay_pos = f"W-w-{margin}:H-h-{margin}"
    elif position == "bottom-left":
        overlay_pos = f"{margin}:H-h-{margin}"
    elif position == "top-right":
        overlay_pos = f"W-w-{margin}:{margin}"
    else:
        overlay_pos = f"{margin}:{margin}"
    
    ffmpeg = get_ffmpeg_path()
    
    # Strip audio from talking head
    th_video_no_audio = talking_head_video.replace(".mp4", "_noaudio.mp4")
    if not Path(th_video_no_audio).exists():
        strip_cmd = [
            ffmpeg, "-y",
            "-i", talking_head_video,
            "-an",
            "-c:v", "copy",
            th_video_no_audio
        ]
        subprocess.run(strip_cmd, capture_output=True, text=True)
    
    # Build FFmpeg command with picture-in-picture
    filter_complex = (
        f"[1:v]scale={size_px}:{size_px}[th];"
        f"[0:v][th]overlay={overlay_pos}:eof_action=pass[outv]"
    )
    
    cmd = [
        ffmpeg, "-y",
        "-i", main_video,
        "-itsoffset", str(start_time),
        "-i", th_video_no_audio,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a",
        "-c:a", "aac", "-b:a", "192k",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_video
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ⚠️ FFmpeg stderr: {result.stderr[:500]}")
        raise Exception(f"FFmpeg failed: {result.stderr}")
    print(f"   ✅ Integrated video saved to: {output_video}")
    return output_video


def main():
    """Main function to generate and integrate talking heads."""
    ensure_dirs()
    
    if not FAL_API_KEY:
        print("❌ FAL_API_KEY not set!")
        return 1
    
    print("=" * 60)
    print("🎬 TALKING HEAD GENERATION & INTEGRATION")
    print("=" * 60)
    
    # Find the latest processed video
    processed_dir = VIDEOS_DIR / "processed"
    voiceover_videos = list(processed_dir.glob("*_voiceover.mp4"))
    
    if not voiceover_videos:
        print("❌ No voiceover video found.")
        return 1
    
    main_video = str(max(voiceover_videos, key=lambda p: p.stat().st_mtime))
    print(f"📹 Main video: {main_video}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
