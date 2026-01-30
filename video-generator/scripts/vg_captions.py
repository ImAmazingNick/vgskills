"""
Caption generation and subtitle functionality for vg CLI.

CONSOLIDATED module containing:
- Basic caption generation (SRT/VTT)
- Advanced features (sync adjustment, animations)
- Word-level streaming captions (TikTok/YouTube style)

All caption functionality lives here - use this module for caption operations.
"""

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

from vg_common import (
    get_ffmpeg, require_ffmpeg, get_duration, 
    classify_error, get_suggestion, error_response, success_response
)
from vg_core_utils.md_parser import parse_voiceover_segments_from_md
from vg_core_utils.timeline import load_timeline_markers


def find_audio_file(audio_dir: Path, segment_id: str) -> Optional[Path]:
    """Find audio file for segment ID with fuzzy matching.
    
    Searches for files matching patterns:
    - {segment_id}.mp3 (exact match)
    - *_{segment_id}.mp3 (prefixed, e.g., 01_intro.mp3)
    - {segment_id}_*.mp3 (suffixed)
    - Case-insensitive matching
    
    Returns the first matching file, or None if not found.
    """
    # Try exact match first
    exact = audio_dir / f"{segment_id}.mp3"
    if exact.exists():
        return exact
    
    # Try patterns with glob
    segment_lower = segment_id.lower()
    
    # Prefixed pattern: *_intro.mp3, 01_intro.mp3
    for f in audio_dir.glob("*.mp3"):
        name_lower = f.stem.lower()
        # Check if segment_id is at the end after underscore
        if name_lower.endswith(f"_{segment_lower}"):
            return f
        # Check if segment_id is at the start before underscore
        if name_lower.startswith(f"{segment_lower}_"):
            return f
        # Check exact match case-insensitive
        if name_lower == segment_lower:
            return f
    
    return None


@dataclass
class CaptionEntry:
    """Single caption entry with timing and text."""
    start_s: float
    end_s: float
    text: str
    segment_id: Optional[str] = None
    
    @property
    def duration_s(self) -> float:
        """Caption duration in seconds."""
        return self.end_s - self.start_s
    
    def to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def to_srt_entry(self, index: int) -> str:
        """
        Convert to SRT format entry.
        
        Args:
            index: 1-based caption index
        
        Returns:
            SRT formatted string for this caption
        """
        start_time = self.to_srt_time(self.start_s)
        end_time = self.to_srt_time(self.end_s)
        
        # Wrap text to max chars per line
        wrapped_text = self._wrap_text(self.text, max_chars=42)
        
        return f"{index}\n{start_time} --> {end_time}\n{wrapped_text}\n"
    
    def to_vtt_entry(self, index: int) -> str:
        """
        Convert to WebVTT format entry.
        
        Args:
            index: 1-based caption index
        
        Returns:
            VTT formatted string for this caption
        """
        start_time = self.to_srt_time(self.start_s).replace(',', '.')
        end_time = self.to_srt_time(self.end_s).replace(',', '.')
        
        # Wrap text to max chars per line
        wrapped_text = self._wrap_text(self.text, max_chars=42)
        
        return f"{index}\n{start_time} --> {end_time}\n{wrapped_text}\n"
    
    @staticmethod
    def _wrap_text(text: str, max_chars: int = 42) -> str:
        """
        Wrap text to max characters per line.
        
        Args:
            text: Text to wrap
            max_chars: Maximum characters per line
        
        Returns:
            Wrapped text with newlines
        """
        if len(text) <= max_chars:
            return text
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + (1 if current_line else 0)  # +1 for space
            
            if current_length + word_length <= max_chars:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)


def calculate_caption_times(
    voiceover_segments: List[Dict[str, Any]],
    timeline_markers: Dict[str, float],
    audio_dir: Path
) -> List[CaptionEntry]:
    """
    Calculate caption start/end times from voiceover segments and timeline.
    
    Args:
        voiceover_segments: List of segments with id, anchor, offset_s, text
        timeline_markers: Dict mapping marker names to timestamps (seconds)
        audio_dir: Directory containing audio files (segment_id.mp3)
    
    Returns:
        List of CaptionEntry objects with calculated timing
    
    Raises:
        ValueError: If required markers are missing or audio files not found
    """
    captions = []
    
    for segment in voiceover_segments:
        segment_id = segment.get("id")
        anchor = segment.get("anchor")
        offset_s = segment.get("offset_s", 0.0)
        text = segment.get("text", "")
        
        if not segment_id or not anchor or not text:
            continue
        
        # Check if audio file exists first (skip segments without audio)
        # Uses fuzzy matching for prefixed names like 01_intro.mp3
        audio_file = find_audio_file(audio_dir, segment_id)
        if not audio_file:
            print(f"⚠️  Skipping segment '{segment_id}': audio file not found (tried {segment_id}.mp3 and variants)")
            continue
        
        # Get anchor time from timeline (skip if marker missing)
        if anchor not in timeline_markers:
            print(f"⚠️  Skipping segment '{segment_id}': anchor marker '{anchor}' not found in timeline")
            continue
        
        anchor_time = timeline_markers[anchor]
        start_time = anchor_time + offset_s
        
        duration = get_duration(audio_file)
        if duration is None or duration <= 0:
            raise ValueError(f"Could not get duration for audio file: {audio_file}")
        
        end_time = start_time + duration
        
        captions.append(CaptionEntry(
            start_s=start_time,
            end_s=end_time,
            text=text,
            segment_id=segment_id
        ))
    
    # Sort by start time
    captions.sort(key=lambda c: c.start_s)
    
    return captions


def validate_caption_timing(captions: List[CaptionEntry]) -> Dict[str, Any]:
    """
    Validate caption timing for issues.
    
    Checks for:
    - Overlapping captions
    - Captions that are too fast (<2 chars/sec)
    - Large gaps between captions (>5 seconds)
    
    Args:
        captions: List of caption entries
    
    Returns:
        Dict with validation results and warnings
    """
    issues = []
    warnings = []
    
    for i, caption in enumerate(captions):
        # Check reading speed (minimum 2 chars per second)
        chars_per_sec = len(caption.text) / caption.duration_s if caption.duration_s > 0 else 0
        if chars_per_sec > 20:  # Too fast (>20 chars/sec)
            warnings.append(f"Caption {i+1} ('{caption.text[:30]}...') is too fast: {chars_per_sec:.1f} chars/sec")
        
        # Check for overlaps with next caption
        if i < len(captions) - 1:
            next_caption = captions[i + 1]
            if caption.end_s > next_caption.start_s:
                overlap = caption.end_s - next_caption.start_s
                issues.append(f"Caption {i+1} overlaps with {i+2} by {overlap:.2f}s")
            
            # Check for large gaps
            gap = next_caption.start_s - caption.end_s
            if gap > 5.0:
                warnings.append(f"Large gap ({gap:.1f}s) between caption {i+1} and {i+2}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "total_captions": len(captions),
        "total_duration": captions[-1].end_s - captions[0].start_s if captions else 0
    }


def generate_srt_file(captions: List[CaptionEntry], output_path: Union[str, Path]) -> dict:
    """
    Generate SRT subtitle file from caption entries.
    
    Args:
        captions: List of caption entries
        output_path: Path to output SRT file
    
    Returns:
        Dict with success status and file info
    """
    try:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate SRT content
        srt_content = []
        for i, caption in enumerate(captions, start=1):
            srt_content.append(caption.to_srt_entry(i))
        
        # Write to file
        srt_text = '\n'.join(srt_content)
        output.write_text(srt_text, encoding='utf-8')
        
        return success_response(
            srt_file=str(output),
            format="srt",
            captions_count=len(captions),
            size_bytes=output.stat().st_size
        )
    
    except Exception as e:
        return error_response(e, "Failed to generate SRT file")


def generate_vtt_file(captions: List[CaptionEntry], output_path: Union[str, Path]) -> dict:
    """
    Generate WebVTT subtitle file from caption entries.
    
    Args:
        captions: List of caption entries
        output_path: Path to output VTT file
    
    Returns:
        Dict with success status and file info
    """
    try:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate VTT content (starts with WEBVTT header)
        vtt_content = ["WEBVTT\n"]
        for i, caption in enumerate(captions, start=1):
            vtt_content.append(caption.to_vtt_entry(i))
        
        # Write to file
        vtt_text = '\n'.join(vtt_content)
        output.write_text(vtt_text, encoding='utf-8')
        
        return success_response(
            vtt_file=str(output),
            format="vtt",
            captions_count=len(captions),
            size_bytes=output.stat().st_size
        )
    
    except Exception as e:
        return error_response(e, "Failed to generate VTT file")


def parse_caption_style(
    style_name: str,
    captions_md_path: Optional[Union[str, Path]] = None,
    request_md_content: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse caption style from CAPTIONS.md or request file.
    
    Args:
        style_name: Name of style preset (e.g., 'youtube', 'professional')
        captions_md_path: Path to CAPTIONS.md (defaults to video-generator/CAPTIONS.md)
        request_md_content: Optional request file content for inline style overrides
    
    Returns:
        Dict with style settings (font, size, color, etc.)
    """
    # Default to CAPTIONS.md in video-generator directory
    if captions_md_path is None:
        script_dir = Path(__file__).parent.parent  # video-generator/
        captions_md_path = script_dir / "CAPTIONS.md"
    else:
        captions_md_path = Path(captions_md_path)
    
    # Read CAPTIONS.md
    if not captions_md_path.exists():
        # Return default style if CAPTIONS.md doesn't exist yet
        return _get_default_style(style_name)
    
    md_content = captions_md_path.read_text(encoding='utf-8')
    style = _parse_style_from_md(md_content, style_name)
    
    # Override with request file style if provided
    if request_md_content:
        request_style = _parse_inline_style(request_md_content)
        if request_style:
            style.update(request_style)
    
    return style


def _parse_style_from_md(md_content: str, style_name: str) -> Dict[str, Any]:
    """Parse style table from CAPTIONS.md."""
    # Find the style section (### style_name)
    pattern = rf'###\s+{re.escape(style_name)}\s*\n(.*?)(?=###|\Z)'
    match = re.search(pattern, md_content, re.DOTALL)
    
    if not match:
        return _get_default_style(style_name)
    
    section = match.group(1)
    
    # Parse the settings table
    style_dict = {}
    for line in section.split('\n'):
        line = line.strip()
        if '|' not in line or line.startswith('|--') or line.startswith('| Setting'):
            continue
        
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) >= 2:
            key = parts[0].lower().replace(' ', '_')
            value = parts[1]
            style_dict[key] = value
    
    return style_dict


def _parse_inline_style(md_content: str) -> Dict[str, Any]:
    """Parse inline caption style from request MD file."""
    # Look for ## Caption Style section
    pattern = r'##\s+Caption Style\s*\n(.*?)(?=##|\Z)'
    match = re.search(pattern, md_content, re.DOTALL)
    
    if not match:
        return {}
    
    section = match.group(1)
    
    # Parse table if present
    style_dict = {}
    for line in section.split('\n'):
        line = line.strip()
        if '|' not in line or line.startswith('|--') or line.startswith('| Setting'):
            continue
        
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) >= 2:
            key = parts[0].lower().replace(' ', '_')
            value = parts[1]
            style_dict[key] = value
    
    return style_dict


def _get_default_style(style_name: str) -> Dict[str, Any]:
    """Get default built-in style."""
    styles = {
        "youtube": {
            "font": "Arial",
            "font_size": "24",
            "color": "white",
            "outline": "2px black",
            "shadow": "1px",
            "position": "bottom-center",
            "margin_bottom": "40px",
            "max_chars/line": "42",
            "max_lines": "2"
        },
        "professional": {
            "font": "Helvetica",
            "font_size": "22",
            "color": "white",
            "outline": "1px black",
            "shadow": "none",
            "position": "bottom-center",
            "margin_bottom": "30px",
            "max_chars/line": "50",
            "max_lines": "2"
        },
        "tiktok": {
            "font": "Impact",
            "font_size": "36",
            "color": "white",
            "outline": "3px black",
            "shadow": "2px",
            "position": "top-center",
            "margin_top": "200px",
            "max_chars/line": "20",
            "max_lines": "3"
        },
        "accessibility": {
            "font": "Arial",
            "font_size": "28",
            "color": "yellow",
            "outline": "3px black",
            "shadow": "2px",
            "position": "bottom-center",
            "margin_bottom": "50px",
            "max_chars/line": "40",
            "max_lines": "2"
        }
    }
    
    return styles.get(style_name, styles["professional"])


def style_to_ffmpeg_subtitle_filter(style: Dict[str, Any]) -> str:
    """
    Convert style dict to FFmpeg subtitle filter force_style parameter.
    
    Args:
        style: Style settings dict
    
    Returns:
        FFmpeg subtitle force_style string
    """
    # Map style settings to ASS subtitle format
    font_name = style.get("font", "Arial")
    font_size = int(style.get("font_size", "24"))
    
    # Color conversion (handle both color names and hex)
    color = style.get("color", "white").lower()
    color_map = {
        "white": "&HFFFFFF&",
        "yellow": "&H00FFFF&",
        "black": "&H000000&",
        "red": "&H0000FF&",
        "blue": "&HFF0000&",
        "green": "&H00FF00&"
    }
    primary_color = color_map.get(color, "&HFFFFFF&")
    
    # Outline
    outline_str = style.get("outline", "2px black")
    outline_size = int(re.search(r'(\d+)', outline_str).group(1)) if re.search(r'(\d+)', outline_str) else 2
    outline_color = "&H000000&"  # Default black
    
    # Shadow
    shadow_str = style.get("shadow", "1px")
    shadow = 0 if shadow_str == "none" else 1
    
    # Margin (vertical position)
    position = style.get("position", "bottom-center")
    margin_v = 40  # Default
    if "margin_bottom" in style:
        margin_v = int(re.search(r'(\d+)', style["margin_bottom"]).group(1))
    elif "margin_top" in style:
        margin_v = int(re.search(r'(\d+)', style["margin_top"]).group(1))
    
    # Alignment (2=bottom center, 5=center, 8=top center)
    alignment = 2  # bottom-center default
    if "top" in position:
        alignment = 8
    elif "center" in position and "bottom" not in position:
        alignment = 5
    
    # Build ASS style string
    force_style = (
        f"FontName={font_name},"
        f"FontSize={font_size},"
        f"PrimaryColour={primary_color},"
        f"OutlineColour={outline_color},"
        f"BorderStyle=3,"
        f"Outline={outline_size},"
        f"Shadow={shadow},"
        f"MarginV={margin_v},"
        f"Alignment={alignment}"
    )
    
    return force_style


def burn_captions_into_video(
    video_path: Union[str, Path],
    srt_path: Union[str, Path],
    output_path: Union[str, Path],
    style: Optional[Dict[str, Any]] = None,
    style_name: str = "professional"
) -> dict:
    """
    Burn SRT captions into video using FFmpeg.
    
    Args:
        video_path: Path to input video
        srt_path: Path to SRT subtitle file
        output_path: Path to output video
        style: Optional style dict (if None, uses style_name)
        style_name: Name of style preset to use
    
    Returns:
        Dict with success status and output file info
    """
    try:
        video = Path(video_path)
        srt = Path(srt_path)
        output = Path(output_path)
        
        # Validate inputs
        if not video.exists():
            raise FileNotFoundError(f"Video file not found: {video}")
        if not srt.exists():
            raise FileNotFoundError(f"SRT file not found: {srt}")
        
        # Get FFmpeg
        ffmpeg = get_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg not found. Install ffmpeg or ffmpeg-static npm package.")
        
        # Parse style
        if style is None:
            style = parse_caption_style(style_name)
        
        force_style = style_to_ffmpeg_subtitle_filter(style)
        
        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command
        # Use subtitles filter to burn in captions
        srt_escaped = str(srt).replace('\\', '\\\\').replace(':', '\\:')
        
        cmd = [
            ffmpeg, "-y",
            "-i", str(video),
            "-vf", f"subtitles={srt_escaped}:force_style='{force_style}'",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output)
        ]
        
        # Run FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        # Get output info
        duration = get_duration(output)
        size = output.stat().st_size
        
        return success_response(
            video=str(output),
            duration=duration,
            size_bytes=size,
            style_applied=style_name,
            captions_burned=True
        )
    
    except Exception as e:
        return error_response(e, "Failed to burn captions into video")


# =============================================================================
# ADVANCED CAPTION FEATURES (formerly vg_captions_advanced.py)
# =============================================================================

def adjust_caption_times_for_edits(
    captions: List[CaptionEntry],
    trim_start: float = 0.0,
    speed_sections: Optional[List[Dict[str, Any]]] = None
) -> List[CaptionEntry]:
    """
    Adjust caption times based on video edits (trim, speed changes).
    
    Args:
        captions: Original caption entries
        trim_start: Seconds trimmed from start of video
        speed_sections: List of {start_s, end_s, speed} sections
    
    Returns:
        Adjusted caption entries with corrected timing
    """
    if speed_sections is None:
        speed_sections = []
    
    adjusted_captions = []
    
    for caption in captions:
        # Apply trim offset
        new_start = caption.start_s - trim_start
        new_end = caption.end_s - trim_start
        
        # Skip captions that were trimmed out
        if new_end <= 0:
            continue
        
        new_start = max(0, new_start)
        
        # Apply speed adjustments
        if speed_sections:
            new_start = _adjust_time_for_speed(new_start, speed_sections)
            new_end = _adjust_time_for_speed(new_end, speed_sections)
        
        adjusted_captions.append(CaptionEntry(
            start_s=new_start,
            end_s=new_end,
            text=caption.text,
            segment_id=caption.segment_id
        ))
    
    return adjusted_captions


def _adjust_time_for_speed(time: float, speed_sections: List[Dict[str, Any]]) -> float:
    """
    Adjust a single timestamp for speed changes.
    
    Speed sections are applied sequentially:
    - If time is before section: no change
    - If time is in section: compress based on speed
    - If time is after section: shift backward by compression amount
    """
    adjusted_time = time
    cumulative_shift = 0.0
    
    for section in sorted(speed_sections, key=lambda s: s['start_s']):
        start = section['start_s']
        end = section['end_s']
        speed = section['speed']
        
        section_duration = end - start
        compressed_duration = section_duration / speed
        compression = section_duration - compressed_duration
        
        if time < start:
            # Time is before this section, no effect yet
            continue
        elif time <= end:
            # Time is within this section, compress it
            position_in_section = time - start
            compressed_position = position_in_section / speed
            adjusted_time = start + compressed_position - cumulative_shift
            break
        else:
            # Time is after this section, shift it backward
            cumulative_shift += compression
    
    return adjusted_time - cumulative_shift


def get_protected_audio_segments(
    voiceover_segments: List[Dict[str, Any]],
    timeline_markers: Dict[str, float]
) -> List[Tuple[float, float]]:
    """
    Get list of time ranges that contain audio and should be protected from speed-up.
    
    Args:
        voiceover_segments: List of voiceover segments with anchor, offset, duration
        timeline_markers: Dict mapping marker names to timestamps
    
    Returns:
        List of (start_time, end_time) tuples for protected ranges
    """
    protected_ranges = []
    
    for segment in voiceover_segments:
        anchor = segment.get("anchor")
        offset_s = segment.get("offset_s", 0.0)
        
        if anchor not in timeline_markers:
            continue
        
        # Get start time
        anchor_time = timeline_markers[anchor]
        start_time = anchor_time + offset_s
        
        # Get duration from segment or calculate from audio file
        duration = segment.get("duration_s")
        if duration is None:
            # Try to get from audio file
            audio_file = segment.get("audio_file")
            if audio_file and Path(audio_file).exists():
                duration = get_duration(Path(audio_file))
        
        if duration:
            end_time = start_time + duration
            protected_ranges.append((start_time, end_time))
    
    # Merge overlapping ranges
    if not protected_ranges:
        return []
    
    protected_ranges.sort(key=lambda x: x[0])
    merged = [protected_ranges[0]]
    
    for start, end in protected_ranges[1:]:
        if start <= merged[-1][1]:
            # Overlapping, merge
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    return merged


def filter_silence_intervals_with_audio_protection(
    silence_intervals: List[Tuple[float, float]],
    protected_ranges: List[Tuple[float, float]],
    padding_s: float = 0.5
) -> List[Tuple[float, float]]:
    """
    Remove silence intervals that overlap with protected audio segments.
    
    Args:
        silence_intervals: Detected silence ranges
        protected_ranges: Audio segments to protect
        padding_s: Extra padding around audio segments (seconds)
    
    Returns:
        Filtered silence intervals that don't overlap with audio
    """
    filtered = []
    
    for silence_start, silence_end in silence_intervals:
        # Check if this silence overlaps with any protected range
        keep_silence = True
        
        for audio_start, audio_end in protected_ranges:
            # Add padding to protected range
            protected_start = audio_start - padding_s
            protected_end = audio_end + padding_s
            
            # Check for overlap
            if not (silence_end <= protected_start or silence_start >= protected_end):
                # Overlap detected, skip this silence interval
                keep_silence = False
                break
        
        if keep_silence:
            filtered.append((silence_start, silence_end))
    
    return filtered


def burn_captions_with_animation(
    video_path: str,
    srt_path: str,
    output_path: str,
    style: Optional[Dict[str, Any]] = None,
    style_name: str = "professional",
    fade_duration: float = 0.2
) -> dict:
    """
    Burn captions with fade-in/fade-out animations.
    
    Args:
        video_path: Path to input video
        srt_path: Path to SRT file
        output_path: Path to output video
        style: Style dict
        style_name: Style preset name
        fade_duration: Fade in/out duration in seconds
    
    Returns:
        Dict with success status
    """
    try:
        video = Path(video_path)
        srt = Path(srt_path)
        output = Path(output_path)
        
        if not video.exists():
            raise FileNotFoundError(f"Video not found: {video}")
        if not srt.exists():
            raise FileNotFoundError(f"SRT not found: {srt}")
        
        ffmpeg = get_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg not found")
        
        # Parse style and force smaller font for better readability
        if style is None:
            style = parse_caption_style(style_name)
        
        # Override font size to be much smaller (16px)
        style["font_size"] = "16"
        
        # Use outline style (BorderStyle=1) instead of opaque box
        force_style = style_to_ffmpeg_subtitle_filter(style)
        # Replace BorderStyle=3 with BorderStyle=1 for outline only
        force_style = force_style.replace("BorderStyle=3", "BorderStyle=1")
        
        # Add fade effect to style
        fade_ms = int(fade_duration * 1000)
        force_style += f",Fade={fade_ms},{fade_ms}"
        
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Escape path for FFmpeg
        srt_escaped = str(srt).replace('\\', '\\\\').replace(':', '\\:')
        
        cmd = [
            ffmpeg, "-y",
            "-i", str(video),
            "-vf", f"subtitles={srt_escaped}:force_style='{force_style}'",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        duration = get_duration(output)
        size = output.stat().st_size
        
        return success_response(
            video=str(output),
            duration=duration,
            size_bytes=size,
            style_applied=style_name,
            captions_burned=True,
            animation="fade",
            fade_duration_s=fade_duration
        )
    
    except Exception as e:
        return error_response(e, "Failed to burn captions with animation")


# =============================================================================
# WORD-LEVEL STREAMING CAPTIONS (formerly vg_captions_wordlevel.py)
# =============================================================================

@dataclass
class WordCaption:
    """Single word with timing for streaming captions."""
    word: str
    start_s: float
    end_s: float
    
    def to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def split_text_into_words(text: str) -> List[str]:
    """Split text into words, preserving punctuation attached to words."""
    return text.split()


def calculate_word_timings(
    text: str,
    start_time: float,
    duration: float
) -> List[WordCaption]:
    """
    Calculate word-level timings based on text length.
    
    Distributes time across words proportionally to character count.
    """
    words = split_text_into_words(text)
    if not words:
        return []
    
    # Calculate total character count (including spaces between words)
    total_chars = sum(len(w) for w in words) + len(words) - 1
    
    word_captions = []
    current_time = start_time
    
    for i, word in enumerate(words):
        # Calculate duration proportional to word length
        word_chars = len(word) + (1 if i < len(words) - 1 else 0)  # +1 for space
        word_duration = (word_chars / total_chars) * duration
        
        # Minimum duration per word (0.15s for readability)
        word_duration = max(0.15, word_duration)
        
        word_captions.append(WordCaption(
            word=word,
            start_s=current_time,
            end_s=current_time + word_duration
        ))
        
        current_time += word_duration
    
    return word_captions


def _format_srt_time_simple(seconds: float) -> str:
    """Format seconds to SRT time (standalone function for word-level captions)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_word_level_srt(
    segments: List[Dict[str, Any]],
    output_path: str,
    words_per_line: int = 4,
    max_lines: int = 2
) -> dict:
    """
    Generate SRT with word-level timing for streaming effect.
    
    Instead of showing entire sentences, shows small groups of words
    that appear progressively.
    
    Args:
        segments: List of {start_s, end_s, text} segments
        output_path: Output SRT file path
        words_per_line: Words to show at once (default: 4)
        max_lines: Maximum lines visible (default: 2)
    """
    try:
        all_word_groups = []
        
        for segment in segments:
            start_s = segment['start_s']
            end_s = segment['end_s']
            text = segment['text']
            duration = end_s - start_s
            
            # Calculate word timings
            word_captions = calculate_word_timings(text, start_s, duration)
            
            # Group words into small chunks
            for i in range(0, len(word_captions), words_per_line):
                chunk = word_captions[i:i + words_per_line]
                if chunk:
                    group_text = ' '.join(w.word for w in chunk)
                    group_start = chunk[0].start_s
                    group_end = chunk[-1].end_s
                    
                    all_word_groups.append({
                        'start': group_start,
                        'end': group_end,
                        'text': group_text
                    })
        
        # Generate SRT content
        srt_lines = []
        for i, group in enumerate(all_word_groups, start=1):
            start_time = _format_srt_time_simple(group['start'])
            end_time = _format_srt_time_simple(group['end'])
            text = group['text']
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")
        
        # Write SRT file
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('\n'.join(srt_lines), encoding='utf-8')
        
        return success_response(
            srt_file=str(output),
            word_groups=len(all_word_groups),
            words_per_line=words_per_line
        )
    
    except Exception as e:
        return error_response(e, "Word-level SRT generation failed")


def burn_small_captions(
    video_path: str,
    srt_path: str,
    output_path: str,
    font_size: int = 10,
    margin_bottom: int = 20
) -> dict:
    """
    Burn captions with ACTUALLY small font.
    
    FFmpeg font sizes are in video pixels, so we need much smaller values.
    For 1080p video, font_size=10 is roughly like 18pt in normal terms.
    """
    try:
        video = Path(video_path)
        srt = Path(srt_path)
        output = Path(output_path)
        
        if not video.exists():
            raise FileNotFoundError(f"Video not found: {video}")
        if not srt.exists():
            raise FileNotFoundError(f"SRT not found: {srt}")
        
        ffmpeg = get_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg not found")
        
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Escape path for FFmpeg
        srt_escaped = str(srt).replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
        
        # Build force_style with SMALL font
        force_style = (
            f"FontName=Arial,"
            f"FontSize={font_size},"
            f"PrimaryColour=&HFFFFFF&,"
            f"OutlineColour=&H000000&,"
            f"BorderStyle=1,"  # Outline only (not opaque box)
            f"Outline=1,"      # Thin outline
            f"Shadow=0,"
            f"MarginV={margin_bottom},"
            f"Alignment=2"     # Bottom center
        )
        
        cmd = [
            ffmpeg, "-y",
            "-i", str(video),
            "-vf", f"subtitles={srt_escaped}:force_style='{force_style}'",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        
        duration = get_duration(output)
        size = output.stat().st_size
        
        return success_response(
            video=str(output),
            duration=duration,
            size_bytes=size,
            font_size=font_size,
            style="small_streaming"
        )
    
    except Exception as e:
        return error_response(e, "Failed to burn small captions")


def create_streaming_captions(
    video_path: str,
    segments: List[Dict[str, Any]],
    output_path: str,
    words_per_group: int = 3,
    font_size: int = 10
) -> dict:
    """
    One-step function to create streaming word-by-word captions.
    
    Args:
        video_path: Input video
        segments: List of {start_s, end_s, text} caption segments
        output_path: Output video with captions
        words_per_group: Words to show at once (default: 3)
        font_size: Font size in FFmpeg units (default: 10 for small)
    """
    try:
        # Generate word-level SRT
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as f:
            temp_srt = f.name
        
        result = generate_word_level_srt(
            segments=segments,
            output_path=temp_srt,
            words_per_line=words_per_group
        )
        
        if not result.get('success'):
            return result
        
        # Burn captions
        result = burn_small_captions(
            video_path=video_path,
            srt_path=temp_srt,
            output_path=output_path,
            font_size=font_size
        )
        
        # Cleanup temp file
        Path(temp_srt).unlink(missing_ok=True)
        
        return result
    
    except Exception as e:
        return error_response(e, "Streaming captions creation failed")
