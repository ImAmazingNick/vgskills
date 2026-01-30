"""
Timeline utilities for video-generator.

AGENTIC DESIGN:
- AI agent reads timeline markers and decides audio placements
- Python code provides simple parsing functions, no matching heuristics
- For agentic workflows, AI uses `load_timeline_markers()` to get events,
  then passes explicit times to `vg compose place`

LEGACY FUNCTIONS (backward compatibility):
- `calculate_segment_times_strict()` - used by `vg compose distribute`
- `calculate_segment_times_lenient()` - fuzzy matching fallback

The agentic approach replaces these with AI reasoning.
"""

from pathlib import Path
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class PositionedSegment:
    """A narration segment with its calculated start time."""
    id: str
    text: str
    start_time_s: float
    audio_path: Optional[Path] = None
    duration_s: float = 0.0


def _parse_timeline_markers_from_md(md_content: str) -> Dict[str, float]:
    markers: Dict[str, float] = {}

    pattern = r'<!-- TIMELINE_MARKERS_START -->(.*?)<!-- TIMELINE_MARKERS_END -->'
    match = re.search(pattern, md_content, re.DOTALL)
    if match:
        table_content = match.group(1).strip()
        lines = table_content.split('\n')
    else:
        # Fallback: find any table with "| Marker | Time"
        lines = md_content.split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('|--') or line.startswith('| Marker'):
            continue
        if '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]
        if len(parts) >= 2:
            marker = parts[0]
            time_str = parts[1]
            try:
                value = float(re.sub(r'[^0-9.\-]+', '', time_str))
                markers[marker] = value
            except Exception:
                continue

    return markers


def load_timeline_markers(timeline_path: Path) -> Dict[str, float]:
    """Load timeline markers from JSON or Markdown file."""
    if not timeline_path.exists():
        raise FileNotFoundError(f"Timeline not found: {timeline_path}")

    if timeline_path.suffix.lower() == ".md":
        return _parse_timeline_markers_from_md(timeline_path.read_text())

    return json.loads(timeline_path.read_text())


def write_timeline_markers(
    timeline_path: Path,
    markers: Dict[str, float],
    exclude_internal: bool = True
) -> Path:
    """
    Write timeline markers to a markdown file.
    
    This is the SINGLE function for writing timeline markers.
    Used by recording, request generation, and any other place that creates timelines.
    
    Args:
        timeline_path: Path to write the timeline.md file
        markers: Dictionary of marker names to timestamps (seconds)
        exclude_internal: If True, skip markers starting with '_'
    
    Returns:
        Path to the written file
    """
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        "<!-- TIMELINE_MARKERS_START -->",
        "| Marker | Time (s) |",
        "|--------|----------|"
    ]
    
    for key, value in sorted(markers.items(), key=lambda x: x[1]):
        if exclude_internal and key.startswith("_"):
            continue
        try:
            lines.append(f"| {key} | {float(value):.2f} |")
        except (TypeError, ValueError):
            lines.append(f"| {key} | {value} |")
    
    lines.append("<!-- TIMELINE_MARKERS_END -->")
    
    timeline_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return timeline_path


def markers_to_md_block(markers: Dict[str, float], exclude_internal: bool = True) -> str:
    """
    Convert markers dict to a markdown block string.
    
    Useful for embedding timeline markers into request files.
    
    Args:
        markers: Dictionary of marker names to timestamps
        exclude_internal: If True, skip markers starting with '_'
    
    Returns:
        Markdown string with markers table
    """
    lines = [
        "<!-- TIMELINE_MARKERS_START -->",
        "| Marker | Time (s) |",
        "|--------|----------|"
    ]
    
    for key, value in sorted(markers.items(), key=lambda x: x[1]):
        if exclude_internal and key.startswith("_"):
            continue
        try:
            lines.append(f"| {key} | {float(value):.2f} |")
        except (TypeError, ValueError):
            lines.append(f"| {key} | {value} |")
    
    lines.append("<!-- TIMELINE_MARKERS_END -->")
    return "\n".join(lines)


def calculate_segment_times_strict(
    segments: List[Dict],
    markers: Dict[str, float]
) -> List[PositionedSegment]:
    """
    LEGACY: Calculate start times for segments using STRICT marker requirements.
    
    DEPRECATED for agentic workflows. Use `vg compose place` with AI-calculated times instead.
    Kept for backward compatibility with `vg compose distribute`.

    Unlike the complex fallback logic, this requires exact timeline markers
    and fails fast if they're not found - just like the powerful previous solution.

    Args:
        segments: List of segment definitions with 'anchor', 'offset_s', and 'audio_file'
        markers: Timeline markers from the recording

    Returns:
        List of PositionedSegment with calculated start times

    Raises:
        ValueError: If required timeline marker is not found
    """
    positioned = []

    for seg in segments:
        anchor = seg.get("anchor")
        offset = seg.get("offset_s", 0.0)

        if anchor not in markers:
            raise ValueError(f"Required timeline marker '{anchor}' not found. "
                           f"Available markers: {list(markers.keys())}")

        start_time = markers[anchor] + offset
        positioned.append(PositionedSegment(
            id=seg["id"],
            text=seg["text"],
            start_time_s=max(0, start_time),  # Ensure non-negative
            audio_path=Path(seg["audio_file"]) if seg.get("audio_file") else None
        ))

    # Sort by start time for consistency
    positioned.sort(key=lambda s: s.start_time_s)

    return positioned


def calculate_segment_times_lenient(
    segments: List[Dict],
    markers: Dict[str, float]
) -> tuple[List[PositionedSegment], List[str]]:
    """
    LEGACY: Calculate start times for segments with SMART marker matching.
    
    DEPRECATED for agentic workflows. Use `vg compose place` with AI-calculated times instead.
    Kept for backward compatibility with `vg compose distribute`.
    
    Features:
    1. Exact match: anchor = t_dashboards_view → finds t_dashboards_view
    2. Fuzzy match: anchor = t_dashboards_view → finds t_dashboards_screenshot, t_dashboards_wait
    3. Inference: segment "dashboards" → finds any marker with "dashboards" in it
    
    Returns positioned segments and a list of missing anchor markers.
    """
    positioned: List[PositionedSegment] = []
    missing: List[str] = []

    for seg in segments:
        anchor = seg.get("anchor")
        offset = seg.get("offset_s", 0.0)
        seg_id = seg.get("id", "").lower()

        start_time = None
        
        # Strategy 1: Exact match
        if anchor and anchor in markers:
            start_time = markers[anchor] + offset
        
        # Strategy 2: Fuzzy match - find marker containing anchor name
        elif anchor:
            # Look for markers that contain the anchor base name
            # e.g., anchor = "t_dashboards_view" → matches "t_dashboards_screenshot"
            anchor_base = anchor.replace("_view", "").replace("_loaded", "").replace("_ready", "")
            for marker_name, marker_time in markers.items():
                if anchor_base in marker_name or marker_name in anchor:
                    start_time = marker_time + offset
                    print(f"   🔍 Fuzzy matched '{anchor}' → '{marker_name}' at {marker_time:.1f}s")
                    break
        
        # Strategy 3: Intelligent inference - match segment ID to marker
        if start_time is None and seg_id:
            # e.g., segment id = "dashboards" → find t_dashboards_view, t_dashboards_screenshot, etc.
            for marker_name, marker_time in markers.items():
                if seg_id in marker_name.lower():
                    start_time = marker_time + offset
                    print(f"   🔍 Inferred '{seg_id}' → '{marker_name}' at {marker_time:.1f}s")
                    break
        
        if start_time is not None:
            positioned.append(PositionedSegment(
                id=seg["id"],
                text=seg["text"],
                start_time_s=max(0, start_time),
                audio_path=Path(seg["audio_file"]) if seg.get("audio_file") else None
            ))
        else:
            missing.append(anchor or f"(segment: {seg_id})")

    positioned.sort(key=lambda s: s.start_time_s)
    return positioned, missing

def fix_overlaps_cascading(segments: List[PositionedSegment]) -> List[PositionedSegment]:
    """
    Fix overlapping segments using simple cascading delays.

    This is the simple, effective approach from the previous powerful solution:
    - 300ms gap between segments
    - If segments would overlap, delay the later one

    Args:
        segments: List of positioned segments (assumed sorted by start_time)

    Returns:
        List with overlaps fixed
    """
    if not segments:
        return segments

    fixed = [segments[0]]  # First segment unchanged

    for seg in segments[1:]:
        prev = fixed[-1]
        prev_end = prev.start_time_s + prev.duration_s

        if seg.start_time_s < prev_end:
            # Overlap detected - delay this segment
            seg.start_time_s = prev_end + 0.3  # 300ms gap

        fixed.append(seg)

    return fixed


def validate_timeline_completeness(
    required_markers: List[str],
    timeline_path: Path
) -> Dict[str, Any]:
    """
    Validate that timeline contains all required markers.

    Returns validation result with missing markers and suggestions.
    """
    try:
        markers = load_timeline_markers(timeline_path)
        missing = [m for m in required_markers if m not in markers]

        return {
            "valid": len(missing) == 0,
            "missing_markers": missing,
            "available_markers": list(markers.keys()),
            "timeline_path": str(timeline_path),
            "marker_count": len(markers)
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "timeline_path": str(timeline_path)
        }


# ============================================================================
# AGENTIC HELPER FUNCTIONS
# ============================================================================
# These are simple utility functions for AI agents to use.
# No matching logic - AI makes the decisions.

def get_marker_time(markers: Dict[str, float], marker_name: str) -> Optional[float]:
    """
    AGENTIC: Get time for a specific marker.
    
    Returns None if marker doesn't exist (AI decides what to do).
    """
    return markers.get(marker_name)


def find_markers_containing(markers: Dict[str, float], pattern: str) -> Dict[str, float]:
    """
    AGENTIC: Find all markers containing a pattern.
    
    AI can use this to discover available markers:
    - find_markers_containing(markers, "agent_done") → all completion markers
    - find_markers_containing(markers, "prompt") → all prompt-related markers
    
    Returns matching markers (AI decides which to use).
    """
    return {k: v for k, v in markers.items() if pattern.lower() in k.lower()}


def get_timeline_summary(timeline_path: Path) -> Dict[str, Any]:
    """
    AGENTIC: Get timeline summary for AI to analyze.
    
    Returns:
    - markers: dict of all markers and times
    - duration: estimated video duration (last marker time)
    - marker_count: number of markers
    - marker_names: list of marker names (sorted by time)
    
    AI uses this to understand what happened during recording.
    """
    try:
        markers = load_timeline_markers(timeline_path)
        sorted_markers = sorted(markers.items(), key=lambda x: x[1])
        
        return {
            "success": True,
            "markers": markers,
            "marker_names": [m[0] for m in sorted_markers],
            "marker_count": len(markers),
            "first_marker": sorted_markers[0] if sorted_markers else None,
            "last_marker": sorted_markers[-1] if sorted_markers else None,
            "estimated_duration": sorted_markers[-1][1] if sorted_markers else 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def apply_time_adjustment(
    placements: List[Dict],
    adjustment: Dict
) -> List[Dict]:
    """
    AGENTIC: Apply time adjustment to placements.
    
    adjustment format (from vg edit trim):
        {"type": "offset", "seconds": -8}  # subtract 8s from all times
    
    adjustment format (from vg edit speed-gaps):
        Use time_map from speed_gaps output instead
    
    Returns new placements with adjusted times.
    """
    adj_type = adjustment.get("type", "offset")
    
    if adj_type == "offset":
        offset = adjustment.get("seconds", 0)
        return [
            {**p, "start_s": max(0, p.get("start_s", 0) + offset)}
            for p in placements
        ]
    
    return placements  # Unknown adjustment type, return unchanged


def check_overlaps(placements: List[Dict]) -> List[Dict]:
    """
    AGENTIC: Check for overlapping audio placements.
    
    Returns list of overlap issues (empty if no overlaps).
    AI can use this to validate before composing.
    
    Each placement should have: start_s, duration_s
    """
    if len(placements) < 2:
        return []
    
    # Sort by start time
    sorted_placements = sorted(placements, key=lambda p: p.get("start_s", 0))
    
    overlaps = []
    for i in range(len(sorted_placements) - 1):
        current = sorted_placements[i]
        next_p = sorted_placements[i + 1]
        
        current_end = current.get("start_s", 0) + current.get("duration_s", 0)
        next_start = next_p.get("start_s", 0)
        
        if current_end > next_start:
            overlaps.append({
                "segment1": current.get("id", f"segment_{i}"),
                "segment1_end": current_end,
                "segment2": next_p.get("id", f"segment_{i+1}"),
                "segment2_start": next_start,
                "overlap_s": current_end - next_start
            })
    
    return overlaps