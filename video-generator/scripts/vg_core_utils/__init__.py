"""
Video Generator Utilities

Shared utilities for video processing, timeline handling, and MD parsing.

This is the core utilities package. All shared parsing and timeline
logic should live here - CLI commands use these functions.

AGENTIC DESIGN:
- For agentic workflows, use `load_timeline_markers()` + `get_timeline_summary()`
  to understand recording events, then pass explicit times to `vg compose place`
- Legacy functions (`calculate_segment_times_*`) still work for backward compatibility
"""

from .timeline import (
    # Core parsing (used by both legacy and agentic)
    load_timeline_markers,
    write_timeline_markers,
    markers_to_md_block,
    fix_overlaps_cascading,
    validate_timeline_completeness,
    PositionedSegment,
    
    # Legacy matching (backward compatibility with vg compose distribute)
    calculate_segment_times_strict,
    calculate_segment_times_lenient,
    
    # Agentic helpers (for AI agent workflows)
    get_marker_time,
    find_markers_containing,
    get_timeline_summary,
    apply_time_adjustment,
    check_overlaps,
)

from .md_parser import (
    # Main parse function (SINGLE SOURCE OF TRUTH)
    parse_request_file,
    validate_request_file,
    ParseError,
    
    # Individual section parsers (for advanced use)
    parse_voiceover_segments_from_md,
    parse_conditional_segments_from_md,
    parse_actions_from_md,
    parse_authentication_from_md,
    parse_browser_settings_from_md,
    parse_options_from_md,
    parse_output_from_md,
    parse_platform_from_md,
    parse_goal_from_md,
    parse_scenario_prompts_from_md,
    parse_success_criteria_from_md,
    extract_scenario_flow_text,
)

__all__ = [
    # Timeline utilities (core)
    'load_timeline_markers',
    'write_timeline_markers',
    'markers_to_md_block',
    'fix_overlaps_cascading',
    'validate_timeline_completeness',
    'PositionedSegment',
    
    # Timeline utilities (legacy matching - backward compatible)
    'calculate_segment_times_strict',
    'calculate_segment_times_lenient',
    
    # Timeline utilities (agentic helpers)
    'get_marker_time',
    'find_markers_containing',
    'get_timeline_summary',
    'apply_time_adjustment',
    'check_overlaps',

    # Main MD parser (PREFERRED)
    'parse_request_file',
    'validate_request_file',
    'ParseError',
    
    # Individual section parsers
    'parse_voiceover_segments_from_md',
    'parse_conditional_segments_from_md',
    'parse_actions_from_md',
    'parse_authentication_from_md',
    'parse_browser_settings_from_md',
    'parse_options_from_md',
    'parse_output_from_md',
    'parse_platform_from_md',
    'parse_goal_from_md',
    'parse_scenario_prompts_from_md',
    'parse_success_criteria_from_md',
    'extract_scenario_flow_text',
]