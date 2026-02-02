"""
MD file parsing utilities for video-generator.

SINGLE SOURCE OF TRUTH for all request file parsing.
All request parsing logic should live here - CLI commands should only transform output.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Lazy import to avoid circular dependency
def _render_template(template_id: str, overrides: dict):
    from vg_narration_templates import render_template
    return render_template(template_id, overrides)


# =============================================================================
# ERROR CODES for parsing failures
# =============================================================================

class ParseError(Exception):
    """Base class for parsing errors with structured info."""
    def __init__(self, message: str, code: str = "PARSE_ERROR", suggestion: str = None):
        super().__init__(message)
        self.code = code
        self.suggestion = suggestion or "Check the request file format"


# =============================================================================
# VOICEOVER SEGMENT PARSING
# =============================================================================

def parse_voiceover_segments_from_md(md_content: str) -> List[Dict[str, Any]]:
    """
    Parse voiceover segments directly from a markdown file.
    
    SUPPORTS BOTH FORMATS:
    1. Legacy table format: <!-- VOICEOVER_SEGMENTS_START --> table <!-- VOICEOVER_SEGMENTS_END -->
    2. Agentic numbered-list format: ## Narration section with 1. **id** (hint): "text"

    Args:
        md_content: Raw markdown content

    Returns:
        List of segment dictionaries with id, anchor, offset_s, text
    """
    # Try legacy format first
    segments = _parse_legacy_voiceover_table(md_content)
    
    # If empty, try agentic numbered-list format
    if not segments:
        segments = parse_agentic_narration_from_md(md_content)
    
    return segments


def _parse_legacy_voiceover_table(md_content: str) -> List[Dict[str, Any]]:
    """Parse legacy table format voiceover segments."""
    # Extract content between markers
    pattern = r'<!-- VOICEOVER_SEGMENTS_START -->(.*?)<!-- VOICEOVER_SEGMENTS_END -->'
    match = re.search(pattern, md_content, re.DOTALL)

    if not match:
        return []

    table_content = match.group(1).strip()
    lines = table_content.split('\n')

    segments = []
    for line in lines:
        # Skip empty lines, header row, and separator row
        line = line.strip()
        if not line or line.startswith('|--') or line.startswith('| Segment'):
            continue
        if '|' not in line:
            continue

        # Parse table row: | Segment | Anchor Marker | Offset | Text |
        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]  # Remove empty parts

        if len(parts) >= 4:
            segment_id = parts[0]
            anchor_marker = parts[1]
            offset_str = parts[2]
            text = parts[3]

            # Handle text that might contain | characters (rejoin remaining parts)
            if len(parts) > 4:
                text = ' | '.join(parts[3:])

            # Parse offset (remove 's' suffix, default to 0.0)
            offset_match = re.match(r'([\d.]+)s?', offset_str)
            offset = float(offset_match.group(1)) if offset_match else 0.0

            segments.append({
                "id": segment_id,
                "anchor": anchor_marker,  # Note: using 'anchor' to match timeline.py expectations
                "offset_s": offset,
                "text": text
            })

    return segments


def extract_prompts_from_segments(segments: List[Dict[str, Any]]) -> List[str]:
    """
    Extract prompt strings from voiceover segment text.
    """
    prompts: List[str] = []
    for seg in segments:
        text = seg.get("text", "")
        if not text:
            continue
        # Prefer single-quoted prompts
        prompts.extend(re.findall(r"'([^']+)'", text))
        # Also allow double-quoted prompts
        prompts.extend(re.findall(r'"([^"]+)"', text))

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for p in prompts:
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped


def parse_agentic_narration_from_md(md_content: str) -> List[Dict[str, Any]]:
    """
    Parse agentic narration format from markdown.
    
    AGENTIC FORMAT:
    ## Narration
    
    1. **intro** (after page loads): "Welcome to..."
    2. **typing** (when typing starts): "Type your request..."
    3. **processing** (during AI work): "The AI is analyzing..."
    
    This is the simplified intent-based format where:
    - AI figures out exact marker matching
    - Intent in parentheses guides AI decision
    - Text in quotes is the narration
    
    Returns list of segments with: id, intent, text
    (No anchor/offset - AI calculates these)
    """
    # Find ## Narration section
    pattern = r'## Narration\s*\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    
    section = match.group(1).strip()
    segments = []
    
    # Match numbered list format: 1. **id** (intent): "text"
    # Also supports: 1. **id** (intent): text without quotes
    list_pattern = r'^\d+\.\s*\*\*(\w+)\*\*\s*\(([^)]+)\):\s*(.+)$'
    
    for line in section.split('\n'):
        line = line.strip()
        if not line or line.startswith('Describe') or line.startswith('#'):
            continue
        
        match = re.match(list_pattern, line)
        if match:
            seg_id = match.group(1).strip()
            intent = match.group(2).strip()
            text = match.group(3).strip()
            
            # Remove surrounding quotes if present
            if (text.startswith('"') and text.endswith('"')) or \
               (text.startswith("'") and text.endswith("'")):
                text = text[1:-1]
            
            # Map common intents to suggested anchors (AI can override)
            intent_to_anchor = {
                "after page loads": "t_page_loaded",
                "page loads": "t_page_loaded",
                "when typing": "t_prompt1_focus",
                "when typing starts": "t_prompt1_focus",
                "typing starts": "t_prompt1_focus",
                "during ai work": "t_processing1_started",
                "during processing": "t_processing1_started",
                "ai processing": "t_processing1_started",
                "when result appears": "t_agent_done_1",
                "result appears": "t_agent_done_1",
                "at the end": "t_scroll_start",
                "end": "t_scroll_start",
                "wrap up": "t_scroll_start",
            }
            
            # Suggest anchor based on intent (AI can override)
            suggested_anchor = intent_to_anchor.get(intent.lower(), f"t_{seg_id}")
            
            segments.append({
                "id": seg_id,
                "intent": intent,
                "text": text,
                # For backward compatibility with existing code
                "anchor": suggested_anchor,
                "offset_s": 0.5,  # Default offset, AI can adjust
                # Flag to indicate this is agentic format
                "agentic": True,
            })
    
    return segments


def parse_talking_heads_from_md(md_content: str) -> List[Dict[str, Any]]:
    """
    Parse talking head segments from markdown.
    
    FORMAT:
    ## Talking Heads
    
    1. **th_intro** (at: 0): "Hi! I'm your guide."
    2. **th_processing** (at: t_processing1_started + 5s): "Working on it..."
    3. **th_outro** (at: end): "That's it! Try it yourself."
    
    Also accepts: ## Talking Heads (Optional)
    
    Returns list of TH segments with: id, text, timing_hint, position
    AI interprets timing_hint to calculate actual times.
    """
    # Find ## Talking Heads section (with optional suffix like "(Optional)")
    pattern = r'## Talking Heads[^\n]*\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    
    section = match.group(1).strip()
    segments = []
    
    # Pattern: 1. **id** (at: timing): "text"
    # The (at: ...) part is optional
    inline_pattern = r'^\d+\.\s*\*\*(\w+)\*\*\s*(?:\(at:\s*([^)]+)\))?\s*:\s*(.+)$'
    
    for line in section.split('\n'):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('**Timing'):
            continue
        
        match = re.match(inline_pattern, line)
        if match:
            seg_id = match.group(1).strip()
            timing_hint = match.group(2).strip() if match.group(2) else None
            text = match.group(3).strip()
            
            # Remove surrounding quotes
            if (text.startswith('"') and text.endswith('"')) or \
               (text.startswith("'") and text.endswith("'")):
                text = text[1:-1]
            
            # Determine type based on timing hint
            th_type = "overlay"  # Default
            if timing_hint:
                timing_lower = timing_hint.lower()
                if timing_lower == "0" or timing_lower == "start":
                    th_type = "intro"  # Fullscreen at start
                elif timing_lower == "end":
                    th_type = "outro"  # Fullscreen at end
            
            segments.append({
                "id": seg_id,
                "text": text,
                "timing_hint": timing_hint,  # AI interprets: "0", "end", "t_marker + 5s"
                "type": th_type,
                "position": "bottom-right",  # Default for overlays
            })
    
    return segments


def parse_simple_options_from_md(md_content: str) -> Dict[str, Any]:
    """
    Parse simplified options format from markdown.
    
    SIMPLIFIED FORMAT:
    ## Options
    
    - **Voiceover:** yes
    - **Talking head:** no
    - **Speed gaps:** yes, 3x
    - **Trim start:** 5 seconds
    
    Returns dict with parsed options.
    """
    options = {}
    
    # Find ## Options section
    pattern = r'## Options\s*\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return options
    
    section = match.group(1).strip()
    
    # Parse each option line
    for line in section.split('\n'):
        line = line.strip()
        if not line.startswith('-'):
            continue
        
        # Handle "- **Voiceover:** yes" format
        # Key is between ** and **: or **:
        match = re.match(r'^-\s*\*\*([^*]+)\*\*:?\s*(.*)$', line)
        if not match:
            # Try without bold: "- Voiceover: yes"
            match = re.match(r'^-\s*([^:]+):\s*(.*)$', line)
        
        if not match:
            continue
        
        key = match.group(1).strip().rstrip(':').lower().replace(' ', '_')
        value = match.group(2).strip().lower()
        
        # Parse different option types
        if key == 'voiceover':
            options['voiceover_enabled'] = value in ['yes', 'true']
        
        elif key == 'talking_head':
            if value in ['yes', 'true']:
                options['talking_head_enabled'] = True
            elif value in ['no', 'false']:
                options['talking_head_enabled'] = False
            else:
                # Could have position: "yes, bottom-right"
                options['talking_head_enabled'] = 'yes' in value
                if 'bottom-right' in value:
                    options['talking_head_position'] = 'bottom-right'
                elif 'bottom-left' in value:
                    options['talking_head_position'] = 'bottom-left'
                elif 'top-right' in value:
                    options['talking_head_position'] = 'top-right'
                elif 'top-left' in value:
                    options['talking_head_position'] = 'top-left'
        
        elif key == 'speed_gaps':
            if 'yes' in value or 'true' in value:
                options['speed_gaps_enabled'] = True
                # Extract factor if present: "yes, 3x"
                factor_match = re.search(r'(\d+(?:\.\d+)?)\s*x', value)
                if factor_match:
                    options['speed_factor'] = float(factor_match.group(1))
            else:
                options['speed_gaps_enabled'] = False
        
        elif key == 'trim_start':
            # Extract number: "5 seconds" or "5s" or just "5"
            num_match = re.search(r'(\d+(?:\.\d+)?)', value)
            if num_match:
                options['trim_start'] = float(num_match.group(1))
        
        elif key == 'trim_end':
            num_match = re.search(r'(\d+(?:\.\d+)?)', value)
            if num_match:
                options['trim_end'] = float(num_match.group(1))
        
        elif key == 'browser_driver':
            # Browser driver: current | agent-browser
            if 'agent' in value or 'agent-browser' in value:
                options['browser_driver'] = 'agent-browser'
            else:
                options['browser_driver'] = 'current'
    
    return options


def parse_conditional_segments_from_md(md_content: str) -> List[Dict[str, Any]]:
    """
    Parse conditional voiceover segments from markdown.

    Table format between <!-- CONDITIONAL_SEGMENTS_START --> and <!-- CONDITIONAL_SEGMENTS_END -->:
    | Segment | Start Marker | End Marker | Min Duration | Offset | Text | Repeatable | Max Repeats | Repeat Interval | Condition Type | Max Duration |
    """
    pattern = r'<!-- CONDITIONAL_SEGMENTS_START -->(.*?)<!-- CONDITIONAL_SEGMENTS_END -->'
    match = re.search(pattern, md_content, re.DOTALL)
    if not match:
        return []

    table_content = match.group(1).strip()
    lines = table_content.split('\n')

    def _to_bool(value: str) -> bool:
        return value.strip().lower() in ["yes", "true", "1"]

    def _to_float(value: str, default: float = 0.0) -> float:
        try:
            return float(re.sub(r'[^0-9.\-]+', '', value))
        except Exception:
            return default

    segments = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('|--') or line.startswith('| Segment'):
            continue
        if '|' not in line:
            continue

        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]

        if len(parts) >= 6:
            seg_id = parts[0]
            start_marker = parts[1]
            end_marker = parts[2]
            min_duration = _to_float(parts[3], 0.0)
            offset = _to_float(parts[4], 0.0)
            text = parts[5]

            repeatable = _to_bool(parts[6]) if len(parts) > 6 else False
            max_repeats = int(_to_float(parts[7], 1)) if len(parts) > 7 else 1
            repeat_interval = _to_float(parts[8], 0.0) if len(parts) > 8 else 0.0
            condition_type = parts[9].strip().lower() if len(parts) > 9 else "duration_between"
            max_duration = _to_float(parts[10], 0.0) if len(parts) > 10 else 0.0

            segments.append({
                "id": seg_id,
                "condition": {
                    "type": condition_type or "duration_between",
                    "start_marker": start_marker,
                    "end_marker": end_marker,
                    "min_duration_s": min_duration,
                    "max_duration_s": max_duration if max_duration > 0 else None
                },
                "anchor": start_marker,
                "offset_s": offset,
                "text": text,
                "repeatable": repeatable,
                "max_repeats": max_repeats,
                "repeat_interval_s": repeat_interval
            })

    return segments


def parse_actions_from_md(md_content: str) -> List[Dict[str, Any]]:
    """
    Parse custom recording actions from markdown.

    Table format between <!-- ACTIONS_START --> and <!-- ACTIONS_END -->:
    | Marker | Action | Selector | Value | Wait |
    """
    pattern = r'<!-- ACTIONS_START -->(.*?)<!-- ACTIONS_END -->'
    match = re.search(pattern, md_content, re.DOTALL)
    if not match:
        return []

    table_content = match.group(1).strip()
    lines = table_content.split('\n')
    actions: List[Dict[str, Any]] = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('|--') or line.startswith('| Marker'):
            continue
        if '|' not in line:
            continue

        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]

        if len(parts) >= 2:
            marker = parts[0] if len(parts) > 0 else ""
            action = parts[1] if len(parts) > 1 else ""
            selector = parts[2] if len(parts) > 2 else ""
            value = parts[3] if len(parts) > 3 else ""
            wait_s = parts[4] if len(parts) > 4 else ""

            actions.append({
                "marker": marker or None,
                "action": action,
                "selector": selector or None,
                "value": value or None,
                "wait_s": wait_s or None
            })

    return actions


def parse_scenario_prompts_from_md(md_content: str) -> List[str]:
    """
    Extract quoted prompt text from the Scenario Flow section.
    """
    pattern = r'## Scenario Flow(.*?)(?=\n## |\Z)'
    match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    section = match.group(1)
    prompts: List[str] = []

    # Only handle lines like: - Type: **Some prompt text**
    for line in section.splitlines():
        line = line.strip()
        if not line.lower().startswith("- type"):
            continue
        # Prefer quoted text if present
        quoted = re.findall(r'"([^"]+)"', line)
        if quoted:
            prompts.extend(quoted)
            continue
        # Fallback to bold text
        bold = re.findall(r'\*\*([^*]+)\*\*', line)
        if bold:
            prompts.extend(bold)
            continue
        # Fallback to raw content after colon
        if ":" in line:
            _, rest = line.split(":", 1)
            rest = rest.strip().strip("*").strip()
            if rest:
                prompts.append(rest)

    return [p.strip() for p in prompts if p.strip()]


def parse_success_criteria_from_md(md_content: str) -> List[str]:
    """
    Parse success criteria checkboxes from markdown.
    """
    pattern = r'## Success Criteria(.*?)(?=\n## |\Z)'
    match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    section = match.group(1)
    checks = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("- [ ]") or line.startswith("- [x]"):
            checks.append(line.split("]", 1)[1].strip())
    return [c for c in checks if c]


def extract_scenario_flow_text(md_content: str) -> str:
    """
    Extract the Scenario Flow section as raw text for AI to read.
    
    Returns the full text of the Scenario Flow section, preserving
    natural language descriptions that an AI agent can understand.
    """
    pattern = r'## Scenario Flow(.*?)(?=\n## |\Z)'
    match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def parse_guided_actions_from_scenario_flow(md_content: str) -> List[Dict[str, Any]]:
    """
    Convert Scenario Flow text into a best-effort action list.
    """
    pattern = r'## Scenario Flow(.*?)(?=\n## |\Z)'
    match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    section = match.group(1)
    actions: List[Dict[str, Any]] = []
    prompt_index = 0

    def _extract_prompt(line: str) -> Optional[str]:
        quoted = re.findall(r'"([^"]+)"', line)
        if quoted:
            return quoted[0].strip()
        bold = re.findall(r'\*\*([^*]+)\*\*', line)
        if bold:
            return bold[0].strip()
        if ":" in line:
            return line.split(":", 1)[1].strip().strip("*").strip()
        return None

    for raw_line in section.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if lower.startswith("- type"):
            prompt = _extract_prompt(line)
            if prompt:
                prompt_index += 1
                actions.extend([
                    {"marker": f"t_prompt{prompt_index}_focus", "action": "click", "selector": "textarea"},
                    {"marker": f"t_prompt{prompt_index}_typed", "action": "type", "selector": "textarea", "value": prompt},
                    {"marker": f"t_prompt{prompt_index}_submitted", "action": "press", "value": "Enter"},
                    {"marker": f"t_processing{prompt_index}_started", "action": "mark"}
                ])
        elif "wait" in lower and ("dashboard" in lower or "processing" in lower or "ai" in lower):
            if prompt_index > 0:
                actions.append({"marker": f"t_agent_done_{prompt_index}", "action": "wait_agent_done"})
        elif "scroll" in lower:
            actions.append({"marker": "t_scroll_start", "action": "scroll", "value": "800"})

    return actions


def parse_narration_template_from_md(md_content: str) -> Dict[str, Any]:
    """
    Parse narration template config from markdown.

    Block format between <!-- NARRATION_TEMPLATE_START --> and <!-- NARRATION_TEMPLATE_END -->:
      Template: ai_agent_default
      prompt_text: Create cross-channel marketing analytics dashboard
      followup_prompt: Add 3 more KPI widgets at bottom of the dashboard
    """
    pattern = r'<!-- NARRATION_TEMPLATE_START -->(.*?)<!-- NARRATION_TEMPLATE_END -->'
    match = re.search(pattern, md_content, re.DOTALL)
    if not match:
        return {}

    block = match.group(1).strip()
    template_id = None
    overrides: Dict[str, Any] = {}

    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = [p.strip() for p in line.split(":", 1)]
        if key.lower() == "template":
            template_id = value
        else:
            overrides[key] = value

    if not template_id:
        return {}

    return {"template_id": template_id, "overrides": overrides}


# =============================================================================
# AUTHENTICATION PARSING
# =============================================================================

def parse_authentication_from_md(md_content: str) -> Dict[str, Any]:
    """
    Parse authentication configuration from markdown.
    
    Supports:
    - Cookie-based auth (name, value from env var, domain, path, secure, httpOnly)
    - Header-based auth (name, value from env var)
    - No auth
    
    Returns dict with authentication details.
    """
    auth = {}
    
    auth_match = re.search(r'## Authentication\s*\n(.*?)(?=\n## |\Z)', md_content, re.DOTALL)
    if not auth_match:
        return auth
    
    auth_text = auth_match.group(1)
    
    # Parse all fields
    field_patterns = {
        "type": r'\*\*Type:\*\*\s*(.+)',
        "cookie_name": r'\*\*Cookie Name:\*\*\s*(.+)',
        "cookie_value": r'\*\*Cookie Value:\*\*\s*(.+)',
        "cookie_domain": r'\*\*Cookie Domain:\*\*\s*(.+)',
        "cookie_path": r'\*\*Cookie Path:\*\*\s*(.+)',
        "header_name": r'\*\*Header Name:\*\*\s*(.+)',
        "header_value": r'\*\*Header Value:\*\*\s*(.+)',
    }
    
    for field, pattern in field_patterns.items():
        match = re.search(pattern, auth_text)
        if match:
            value = match.group(1).strip()
            # Handle env var references like "From environment variable `VAR_NAME`"
            env_match = re.search(r'environment variable\s*`?(\w+)`?', value, re.IGNORECASE)
            if env_match:
                env_var = env_match.group(1)
                auth[field] = os.environ.get(env_var, "")
                auth[f"{field}_env_var"] = env_var
            else:
                auth[field] = value
    
    # Boolean fields
    bool_patterns = {
        "cookie_secure": r'\*\*Cookie Secure:\*\*\s*(.+)',
        "cookie_http_only": r'\*\*Cookie HttpOnly:\*\*\s*(.+)',
    }
    
    for field, pattern in bool_patterns.items():
        match = re.search(pattern, auth_text)
        if match:
            auth[field] = match.group(1).strip().lower() in ["true", "yes", "1"]
    
    return auth


# =============================================================================
# BROWSER SETTINGS PARSING
# =============================================================================

def parse_browser_settings_from_md(md_content: str) -> Dict[str, Any]:
    """
    Parse browser settings from markdown.
    
    Supports: viewport, headless, slow_motion, demo_effects
    """
    settings = {}
    
    settings_match = re.search(r'## Browser Settings\s*\n(.*?)(?=\n## |\Z)', md_content, re.DOTALL)
    if not settings_match:
        return settings
    
    settings_text = settings_match.group(1)
    
    # Viewport
    viewport_match = re.search(r'\*\*Viewport:\*\*\s*(\d+)\s*x\s*(\d+)', settings_text)
    if viewport_match:
        settings["viewport"] = {
            "width": int(viewport_match.group(1)),
            "height": int(viewport_match.group(2))
        }
    
    # Boolean settings
    bool_patterns = {
        "headless": r'\*\*Headless:\*\*\s*(yes|no|true|false)',
        "slow_motion": r'\*\*Slow Motion:\*\*\s*(yes|no|true|false)',
        "demo_effects": r'\*\*Demo Effects:\*\*\s*(yes|no|true|false)',
    }
    
    for field, pattern in bool_patterns.items():
        match = re.search(pattern, settings_text, re.IGNORECASE)
        if match:
            settings[field] = match.group(1).lower() in ["yes", "true"]
    
    return settings


# =============================================================================
# OPTIONS PARSING (voiceover, talking head, editing)
# =============================================================================

def parse_options_from_md(md_content: str) -> Dict[str, Any]:
    """
    Parse options section from markdown.
    
    Supports:
    - Voiceover: enable, voice_provider, voice_id
    - Talking Head: enable, model, position, size, segments
    - Editing: trim_start, trim_end, speed_factor
    """
    options = {}
    
    options_match = re.search(r'## Options\s*\n(.*?)(?=\n## |\Z)', md_content, re.DOTALL)
    if not options_match:
        return options
    
    options_text = options_match.group(1)
    
    # Voiceover options
    vo_enabled = re.search(r'\*\*Enable:\*\*\s*(yes|no)', options_text, re.IGNORECASE)
    vo_provider = re.search(r'\*\*Voice Provider:\*\*\s*(.+)', options_text)
    vo_voice_id = re.search(r'\*\*Voice ID:\*\*\s*(.+)', options_text)
    
    if vo_enabled:
        options["voiceover_enabled"] = vo_enabled.group(1).lower() == 'yes'
    if vo_provider:
        options["voice_provider"] = vo_provider.group(1).strip()
    if vo_voice_id:
        options["voice_id"] = vo_voice_id.group(1).strip()
    
    # Talking head options (look for subsection)
    th_section = re.search(r'### Talking Head\s*\n(.*?)(?=\n### |\n## |\Z)', options_text, re.DOTALL)
    if th_section:
        th_text = th_section.group(1)
        
        th_enabled = re.search(r'\*\*Enable:\*\*\s*(yes|no)', th_text, re.IGNORECASE)
        if th_enabled:
            options["talking_head_enabled"] = th_enabled.group(1).lower() == 'yes'
        
        th_patterns = {
            "talking_head_model": r'\*\*Model:\*\*\s*(.+)',
            "talking_head_position": r'\*\*Position:\*\*\s*(.+)',
        }
        
        for field, pattern in th_patterns.items():
            match = re.search(pattern, th_text)
            if match:
                options[field] = match.group(1).strip()
        
        # Talking head segments
        th_segments = re.search(r'\*\*Segments:\*\*\s*(.+)', th_text)
        if th_segments:
            raw_segments = th_segments.group(1).strip()
            if raw_segments.lower() in ["all", "all segments", "*"]:
                options["talking_head_segments"] = ["*"]
            else:
                options["talking_head_segments"] = [
                    s.strip() for s in re.split(r'[,\s]+', raw_segments) if s.strip()
                ]
        
        # Talking head size
        th_size = re.search(r'\*\*Size:\*\*\s*(.+)', th_text)
        if th_size:
            size_match = re.search(r'(\d+)', th_size.group(1))
            if size_match:
                options["talking_head_size_px"] = int(size_match.group(1))
    
    # Editing options
    edit_section = re.search(r'### Editing\s*\n(.*?)(?=\n### |\n## |\Z)', options_text, re.DOTALL)
    if edit_section:
        edit_text = edit_section.group(1)
        
        trim_start = re.search(r'\*\*Trim Start:\*\*\s*(\d+)', edit_text)
        trim_end = re.search(r'\*\*Trim End:\*\*\s*(\d+)', edit_text)
        speed_factor = re.search(r'\*\*Speed Factor:\*\*\s*([\d.]+)', edit_text)
        # Speed Gaps: yes/no - speeds up gaps BEFORE adding audio (preserves voiceover)
        speed_gaps = re.search(r'\*\*Speed (?:Up|Gaps):\*\*\s*(yes|no|true|false)', edit_text, re.IGNORECASE)
        
        if trim_start:
            options["trim_start"] = float(trim_start.group(1))
        if trim_end:
            options["trim_end"] = float(trim_end.group(1))
        if speed_factor:
            options["speed_factor"] = float(speed_factor.group(1))
        if speed_gaps:
            options["speed_gaps_enabled"] = speed_gaps.group(1).lower() in ("yes", "true")
    
    return options


# =============================================================================
# OUTPUT SETTINGS PARSING
# =============================================================================

def parse_output_from_md(md_content: str) -> Dict[str, Any]:
    """
    Parse output settings from markdown.
    
    Supports: filename_pattern, format, resolution, duration
    """
    output = {}
    
    output_match = re.search(r'## Output\s*\n(.*?)(?=\n## |\Z)', md_content, re.DOTALL)
    if not output_match:
        return output
    
    output_text = output_match.group(1)
    
    patterns = {
        "filename_pattern": r'\*\*Filename Pattern:\*\*\s*(.+)',
        "format": r'\*\*Format:\*\*\s*(.+)',
        "resolution": r'\*\*Resolution:\*\*\s*(.+)',
        "duration": r'\*\*Duration:\*\*\s*(.+)',
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, output_text)
        if match:
            output[field] = match.group(1).strip()
    
    return output


# =============================================================================
# GOAL PARSING
# =============================================================================

def parse_goal_from_md(md_content: str) -> str:
    """
    Parse goal description from markdown.
    """
    goal_match = re.search(r'## Goal\s*\n(.*?)(?=\n## |\Z)', md_content, re.DOTALL)
    if goal_match:
        return goal_match.group(1).strip()
    return ""


# =============================================================================
# PLATFORM INFO PARSING
# =============================================================================

def parse_platform_from_md(md_content: str) -> Dict[str, Any]:
    """
    Parse platform info from markdown.
    
    Returns dict with name and url.
    """
    platform = {"name": "Unknown", "url": None}
    
    # Try ## Platform section first
    platform_section = re.search(r'## Platform\s*\n(.*?)(?=\n## |\Z)', md_content, re.DOTALL)
    if platform_section:
        section_text = platform_section.group(1)
        
        name_match = re.search(r'\*\*(?:Platform|Name):\*\*\s*(.+)', section_text)
        url_match = re.search(r'\*\*URL:\*\*\s*(.+)', section_text)
        
        if name_match:
            platform["name"] = name_match.group(1).strip().strip('*')
        if url_match:
            platform["url"] = url_match.group(1).strip().strip('*')
    else:
        # Fallback: look for standalone patterns
        platform_match = re.search(r'Platform:\s*([^\n]+)', md_content, re.IGNORECASE)
        url_match = re.search(r'URL:\s*([^\n]+)', md_content, re.IGNORECASE)
        
        if platform_match:
            platform["name"] = platform_match.group(1).strip().strip('*')
        if url_match:
            platform["url"] = url_match.group(1).strip().strip('*')
    
    return platform


# =============================================================================
# MAIN PARSE FUNCTION - SINGLE SOURCE OF TRUTH
# =============================================================================

def parse_request_file(request_path: Path) -> Dict[str, Any]:
    """
    Parse a complete request file and extract ALL relevant data.
    
    This is the SINGLE SOURCE OF TRUTH for request parsing.
    CLI commands should use this function and not re-parse the file.

    Args:
        request_path: Path to the markdown request file

    Returns:
        Dictionary with ALL parsed request data:
        - platform: {name, url}
        - authentication: {type, cookie_*, header_*}
        - browser_settings: {viewport, headless, etc}
        - goal: str
        - segments: voiceover segments
        - conditional_segments: conditional narration
        - actions: custom recording actions
        - scenario_prompts: prompts from scenario flow
        - success_criteria: validation checks
        - guided_actions: inferred actions from scenario
        - voiceover_prompts: prompts extracted from narration
        - options: {voiceover_enabled, talking_head_*, trim_*, etc}
        - output: {filename_pattern, format, etc}
        - template_used: template ID if using narration template
    
    Raises:
        FileNotFoundError: If request file doesn't exist
        ParseError: If file has critical parsing issues
    """
    if not request_path.exists():
        raise FileNotFoundError(f"Request file not found: {request_path}")

    content = request_path.read_text()

    # Parse all sections
    platform = parse_platform_from_md(content)
    authentication = parse_authentication_from_md(content)
    browser_settings = parse_browser_settings_from_md(content)
    goal = parse_goal_from_md(content)
    
    # Parse voiceover segments - try old format first, then new agentic format
    voiceover_segments = parse_voiceover_segments_from_md(content)
    narration_format = "legacy"
    
    if not voiceover_segments:
        # Try new agentic narration format
        voiceover_segments = parse_agentic_narration_from_md(content)
        if voiceover_segments:
            narration_format = "agentic"
    
    conditional_segments = parse_conditional_segments_from_md(content)
    template_config = parse_narration_template_from_md(content)
    actions = parse_actions_from_md(content)
    scenario_prompts = parse_scenario_prompts_from_md(content)
    success_criteria = parse_success_criteria_from_md(content)
    guided_actions = parse_guided_actions_from_scenario_flow(content)
    scenario_flow_text = extract_scenario_flow_text(content)
    voiceover_prompts = extract_prompts_from_segments(voiceover_segments)
    
    # Parse talking heads section (separate from voiceover)
    talking_heads = parse_talking_heads_from_md(content)
    
    # Parse options - try old format first, then merge with simplified format
    options = parse_options_from_md(content)
    simple_options = parse_simple_options_from_md(content)
    
    # Merge options (simple_options can override)
    for key, value in simple_options.items():
        if value is not None and key not in options:
            options[key] = value
        elif value is not None:
            # Simple format overrides if it has a value
            options[key] = value
    
    output = parse_output_from_md(content)

    # Handle narration templates
    template_used = None
    template_conditionals: List[Dict[str, Any]] = []

    if template_config:
        template_id = template_config.get("template_id")
        overrides = template_config.get("overrides", {})
        if template_id:
            try:
                template_segments, template_conditionals, _ = _render_template(template_id, overrides)
                if not voiceover_segments:
                    voiceover_segments = template_segments
                    template_used = template_id
            except Exception:
                pass  # Template rendering failed, continue with explicit segments

    if not conditional_segments and template_conditionals:
        conditional_segments = template_conditionals

    # Merge trim_start from options if present (backward compatibility)
    trim_start = options.get("trim_start")
    if trim_start is None:
        trim_start_match = re.search(r'Trim Start:\s*(\d+)', content, re.IGNORECASE)
        if trim_start_match:
            trim_start = float(trim_start_match.group(1))

    return {
        # File info
        "file": str(request_path),
        "request_path": str(request_path),
        
        # Platform & auth
        "platform": platform,
        "authentication": authentication,
        "browser_settings": browser_settings,
        
        # Content
        "goal": goal,
        "segments": voiceover_segments,
        "voiceover_segments": voiceover_segments,  # Alias for compatibility
        "conditional_segments": conditional_segments,
        "segment_count": len(voiceover_segments),
        "has_voiceover": len(voiceover_segments) > 0,
        "narration_format": narration_format,  # "legacy" or "agentic"
        
        # Talking heads (separate from voiceover)
        "talking_heads": talking_heads,
        "has_talking_heads": len(talking_heads) > 0,
        
        # Recording
        "actions": actions,
        "scenario_prompts": scenario_prompts,
        "success_criteria": success_criteria,
        "guided_actions": guided_actions,
        "scenario_flow_text": scenario_flow_text,  # Raw text for AI to read
        "voiceover_prompts": voiceover_prompts,
        
        # Options & output
        "options": options,
        "output": output,
        
        # Derived values
        "trim_start": trim_start,
        "template_used": template_used,
        
        # Convenience accessors (for backward compatibility)
        "url": platform.get("url"),
    }


def validate_request_file(request_path: Path) -> Dict[str, Any]:
    """
    Validate that a request file has all required components.

    Returns validation result with issues and suggestions.
    """
    try:
        result = parse_request_file(request_path)

        issues = []
        if not result["has_voiceover"]:
            issues.append("No voiceover segments found in request file")
        if not result["url"]:
            issues.append("No URL specified in request file")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "segment_count": result["segment_count"],
            "platform": result["platform"],
            "url": result["url"]
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "request_path": str(request_path)
        }