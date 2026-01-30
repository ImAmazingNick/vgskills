"""
REAL Playwright recording functionality for vg CLI.

Uses the PROVEN DemoRecorder framework from working scripts.
Smart waiting logic moved to vg_smart_waiting.py module.
"""

import os
from pathlib import Path
import time
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from project_paths import run_paths
from vg_common import VGError, classify_error, get_suggestion, get_duration
from vg_core_utils import write_timeline_markers

# Import smart waiting functions (with underscore aliases for backward compatibility)
from vg_smart_waiting import (
    _thinking_visible,
    _dashboard_visible,
    _followup_input_enabled,
    _find_enabled_followup_input,
    _find_primary_input,
    _find_primary_input_deep,
    _find_enabled_followup_input_deep,
    _query_selector_deep,
    _find_largest_input,
    _focus_prompt_area,
    _wait_agent_dashboard_done,
    _wait_followup_input_enabled,
    _wait_for_primary_input,
)

PROJECT_ROOT = Path(__file__).resolve().parent


# =============================================================================
# SCREENSHOT UTILITY
# =============================================================================

def _screenshot_preserve_view(page, path: Path, full_page: bool = False) -> None:
    """Take screenshot without changing user-visible view."""
    try:
        scroll_pos = page.evaluate("() => ({ x: window.scrollX, y: window.scrollY })")
    except Exception:
        scroll_pos = None
    page.screenshot(path=str(path), full_page=full_page)
    if scroll_pos:
        try:
            page.evaluate("(pos) => window.scrollTo(pos.x, pos.y)", scroll_pos)
        except Exception:
            pass


def validate_recording_quality(timeline_markers: Dict[str, float], run_dir: Path) -> Dict[str, Any]:
    """
    Validate recording quality and provide suggestions for improvement.
    
    Returns:
        {"valid": bool, "issues": [...], "suggestions": [...]}
    """
    issues = []
    suggestions = []
    warnings = []
    
    # Get timeline boundaries
    t_start = timeline_markers.get("t_start_recording", 0)
    t_end = timeline_markers.get("t_recording_complete") or max(timeline_markers.values())
    total_duration = t_end - t_start
    
    # Check if page load took most of the time
    t_page_loaded = timeline_markers.get("t_page_loaded", 0)
    load_time = t_page_loaded - t_start
    
    if load_time > total_duration * 0.7:  # More than 70% was loading
        issues.append(f"Page load took {load_time:.1f}s ({load_time/total_duration*100:.0f}% of recording)")
        suggestions.append("⚠️  Session cookie may be invalid - page might be stuck on auth/loading")
        suggestions.append("Add 'wait_visible' with specific expected elements (e.g., text=Dashboards)")
        suggestions.append("Add screenshot immediately after page load to verify content")
    elif load_time > total_duration * 0.5:  # 50-70% loading
        warnings.append(f"Page load took {load_time:.1f}s ({load_time/total_duration*100:.0f}% of recording)")
        suggestions.append("Consider using faster load strategy (domcontentloaded)")
    
    # Check for very short action times (might indicate content not loaded)
    action_markers = {k: v for k, v in timeline_markers.items() 
                     if k not in ["t_start_recording", "t_page_loaded", "t_recording_complete", "t_screenshot_initial_page"]}
    if action_markers:
        action_start = min(action_markers.values())
        action_end = max(action_markers.values())
        action_duration = action_end - action_start
        
        if action_duration < 10 and len(action_markers) > 3:  # Actions completed very quickly
            issues.append(f"All actions completed in {action_duration:.1f}s (may indicate missing content or failed interactions)")
            suggestions.append("Add 'screenshot' after each major action to verify page changed")
            suggestions.append("Add 'wait_visible' for expected content after each click")
    
    # Check screenshot count
    screenshot_dir = run_dir / "raw" / "screenshots"
    screenshots = []
    if screenshot_dir.exists():
        screenshots = list(screenshot_dir.glob("*.png"))
        
        # Count non-initial screenshots
        action_screenshots = [s for s in screenshots if "initial" not in s.name.lower()]
        
        if len(screenshots) < 3:
            issues.append(f"Only {len(screenshots)} screenshot(s) captured (need more to verify actions)")
            suggestions.append("Add 'screenshot' action after each click/navigation to verify content")
        
        if len(action_screenshots) == 0 and len(screenshots) > 0:
            issues.append("No screenshots after actions - cannot verify if navigation worked")
            suggestions.append("CRITICAL: Add screenshot actions after clicks to verify pages changed")
    else:
        issues.append("No screenshots captured")
        suggestions.append("Add screenshot actions to verify page state")
    
    # Determine if recording is likely failed
    critical_failure = (
        load_time > total_duration * 0.8 or  # 80%+ loading
        (len(screenshots) if screenshot_dir.exists() else 0) < 2  # Almost no screenshots
    )
    
    return {
        "valid": len(issues) == 0,
        "likely_failed": critical_failure,
        "issues": issues,
        "warnings": warnings,
        "suggestions": suggestions,
        "timeline_summary": {
            "total_duration": total_duration,
            "load_time": load_time,
            "action_time": total_duration - load_time,
            "screenshot_count": len(screenshots) if screenshot_dir.exists() else 0
        }
    }


def _execute_actions(
    recorder,
    actions: List[Dict[str, Any]],
    markers: Dict[str, float],
    t0: float,
    screenshot_dir: Path,
    wait_timeout: int,
    stable_time: int
) -> None:
    """Execute custom action list from request file."""
    page = recorder.page

    for idx, action in enumerate(actions):
        action_type = (action.get("action") or "").strip().lower()
        marker = action.get("marker")
        selector = action.get("selector")
        value = action.get("value")
        wait_s_raw = action.get("wait_s")

        def _mark():
            if marker:
                markers[marker] = time.time() - t0

        if action_type in ["click", "focus"]:
            if not selector:
                raise ValueError(f"Action {idx+1} missing selector for click")
            
            # Verify element exists and is visible before clicking
            try:
                page.wait_for_selector(selector, timeout=5000, state="visible")
            except Exception as e:
                error_msg = f"❌ Action {idx+1} ({action_type} '{selector}'): Element not found or not visible"
                print(f"   {error_msg}")
                raise ValueError(f"{error_msg}. Page may not have loaded properly. Original error: {e}")
            
            page.click(selector)
            _mark()
        elif action_type == "fill":
            if not selector:
                raise ValueError(f"Action {idx+1} missing selector for fill")
            page.fill(selector, value or "")
            _mark()
        elif action_type == "type":
            if not selector:
                raise ValueError(f"Action {idx+1} missing selector for type")
            delay_ms = int(action.get("delay_ms") or 25)
            page.type(selector, value or "", delay=delay_ms)
            _mark()
        elif action_type == "press":
            page.keyboard.press(value or "Enter")
            _mark()
        elif action_type == "wait_selector":
            if not selector:
                raise ValueError(f"Action {idx+1} missing selector for wait_selector")
            timeout_ms = int(action.get("timeout_ms") or 60000)
            page.wait_for_selector(selector, timeout=timeout_ms)
            _mark()
        elif action_type == "wait_text":
            if not value:
                raise ValueError(f"Action {idx+1} missing value for wait_text")
            timeout_ms = int(action.get("timeout_ms") or 60000)
            page.wait_for_selector(f"text={value}", timeout=timeout_ms)
            _mark()
        elif action_type == "wait_agent_done":
            _wait_agent_dashboard_done(page, timeout_s=wait_timeout, stable_s=stable_time)
            _mark()
        elif action_type == "wait_followup_input":
            _wait_followup_input_enabled(page, timeout_s=wait_timeout)
            _mark()
        elif action_type == "scroll":
            amount = int(float(value or 800))
            page.mouse.wheel(0, amount)
            _mark()
        elif action_type == "screenshot":
            name = marker or f"step_{idx+1}"
            path = screenshot_dir / f"{name}_{int(time.time())}.png"
            try:
                _screenshot_preserve_view(page, path, full_page=True)
                print(f"   📸 Screenshot saved: {path.name}")
            except Exception as e:
                print(f"   ⚠️  Screenshot failed (continuing): {e}")
                # Continue even if screenshot fails - don't crash the whole recording
            _mark()
        elif action_type == "wait":
            wait_s = float(wait_s_raw or value or 1.0)
            page.wait_for_timeout(int(wait_s * 1000))
            _mark()
        elif action_type == "wait_network_idle":
            timeout_ms = int(action.get("timeout_ms") or value or 60000)
            try:
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except Exception as e:
                print(f"   ⚠️  Network idle timeout ({timeout_ms}ms): {e}")
            _mark()
        elif action_type == "wait_visible":
            if not selector:
                raise ValueError(f"Action {idx+1} missing selector for wait_visible")
            timeout_ms = int(action.get("timeout_ms") or value or 30000)
            
            print(f"   ⏳ Waiting up to {timeout_ms/1000:.0f}s for elements to be visible...")
            
            # Support comma-separated selectors as fallback cascade
            selectors = [s.strip() for s in selector.split(",")]
            found = False
            last_error = None
            
            for idx_sel, sel in enumerate(selectors):
                try:
                    per_selector_timeout = max(5000, timeout_ms // len(selectors))
                    print(f"      Trying selector {idx_sel+1}/{len(selectors)}: '{sel}' (timeout: {per_selector_timeout/1000:.0f}s)")
                    page.wait_for_selector(sel, timeout=per_selector_timeout, state="visible")
                    print(f"      ✅ Found: '{sel}'")
                    found = True
                    break
                except Exception as e:
                    print(f"      ⏭️  Not found: '{sel}'")
                    last_error = e
                    continue
            
            if not found:
                print(f"      🔄 Final attempt with full timeout on first selector...")
                # Final attempt with full timeout on first selector
                page.wait_for_selector(selectors[0], timeout=timeout_ms, state="visible")
                print(f"      ✅ Element appeared: '{selectors[0]}'")
            
            _mark()
        elif action_type == "mark":
            _mark()
        else:
            raise ValueError(f"Unknown action type '{action_type}' at step {idx+1}")


def _execute_auto_navigation(
    recorder,
    prompts: List[str],
    markers: Dict[str, float],
    t0: float,
    screenshot_dir: Path,
    validation_checks: List[str]
) -> None:
    """Best-effort auto navigation for non-AI scenarios."""
    page = recorder.page

    def _mark(name: str):
        markers[name] = time.time() - t0

    def _screenshot(name: str):
        path = screenshot_dir / f"{name}_{int(time.time())}.png"
        page.screenshot(path=str(path), full_page=True)

    # Step 1: initial state
    _mark("t_page_loaded")
    _screenshot("auto_page_loaded")

    input_el = _find_primary_input(page) or _find_primary_input_deep(page) or _find_largest_input(page)

    if input_el and prompts:
        for idx, prompt in enumerate(prompts, 1):
            try:
                # Re-find input before each prompt
                input_el = _find_primary_input(page) or _find_primary_input_deep(page) or _find_largest_input(page) or input_el
                input_el.click()
                _mark(f"t_prompt{idx}_focus")
                input_el.fill("")
                input_el.type(prompt, delay=30)
                _mark(f"t_prompt{idx}_typed")
                page.keyboard.press("Enter")
                _mark(f"t_prompt{idx}_submitted")
                _screenshot(f"auto_prompt{idx}_submitted")
                _mark(f"t_processing{idx}_started")

                # Wait for AI processing only if signs appear
                try:
                    if _thinking_visible(page) or _dashboard_visible(page):
                        _wait_agent_dashboard_done(page, timeout_s=180, stable_s=3)
                        _mark(f"t_agent_done_{idx}")
                except Exception:
                    _screenshot(f"auto_prompt{idx}_wait_failed")

                # Attempt to locate follow-up input for next prompt
                try:
                    follow_el = _find_enabled_followup_input(page) or _find_enabled_followup_input_deep(page)
                    if follow_el:
                        input_el = follow_el
                except Exception:
                    pass

                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
            except Exception:
                _screenshot(f"auto_prompt{idx}_failed")

    # Try clicking a primary CTA if present
    cta_selectors = [
        'button:has-text("Create")',
        'button:has-text("New")',
        'button:has-text("Connect")',
        'button:has-text("Import")',
        'button:has-text("Upload")',
        'button:has-text("Get started")',
        'button:has-text("Continue")'
    ]
    cta_sel = None
    for sel in cta_selectors:
        try:
            if page.locator(sel).count() > 0:
                cta_sel = sel
                break
        except Exception:
            continue
    if cta_sel:
        try:
            page.click(cta_sel)
            _mark("t_primary_cta_clicked")
            _screenshot("auto_primary_cta")
        except Exception:
            _screenshot("auto_primary_cta_failed")

    # Run validation checks with screenshots
    for i, check in enumerate(validation_checks, 1):
        check_lower = check.lower()
        if any(k in check_lower for k in ["dashboard", "chart", "widget"]):
            try:
                if not _dashboard_visible(page):
                    _wait_agent_dashboard_done(page, timeout_s=20, stable_s=2)
                _mark(f"t_validation_{i}")
                _screenshot(f"validation_{i}_dashboard")
            except Exception:
                _screenshot(f"validation_{i}_failed")
        else:
            _mark(f"t_validation_{i}")
            _screenshot(f"validation_{i}")

    # Scroll to show more content
    try:
        page.mouse.wheel(0, 800)
        _mark("t_scroll_start")
        _screenshot("auto_scroll_start")
    except Exception:
        _screenshot("auto_scroll_failed")


# =============================================================================
# RECORDING CONFIGURATION
# =============================================================================

def _extract_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL for cookie settings.
    
    Returns domain with leading dot for subdomain matching.
    Example: "https://app.example.com/page" -> ".example.com"
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None
        # Get base domain (last two parts for most domains)
        parts = hostname.split('.')
        if len(parts) >= 2:
            return '.' + '.'.join(parts[-2:])
        return '.' + hostname
    except Exception:
        return None


@dataclass
class RecordingConfig:
    """Configuration for browser recording session.
    
    Authentication:
        - Provide auth_cookies for full control over cookie settings
        - Or provide session_cookie with cookie_domain for simple auth
        - Without explicit auth, recording may fail on authenticated pages
    
    Prompts:
        - For ai-agent scenario, provide prompts explicitly
        - No default prompts - you must specify what the AI should do
    """
    url: str
    scenario: str = "ai-agent"
    prompts: List[str] = None  # AI prompts - must be provided explicitly
    actions: List[Dict[str, Any]] = None  # Custom action list
    auto_prompts: List[str] = None  # Auto-navigation prompts
    run_id: Optional[str] = None
    validation_checks: List[str] = None
    headless: bool = False
    
    # Authentication - explicit configuration required
    session_cookie: str = None  # Format: "name=value" or "value" (uses cookie_name)
    cookie_name: str = None  # Cookie name (defaults to extracting from session_cookie)
    cookie_domain: str = None  # Cookie domain (extracted from URL if not provided)
    auth_cookies: Optional[List[Dict[str, Any]]] = None  # Full cookie dicts (overrides above)
    auth_headers: Optional[Dict[str, str]] = None
    
    output_dir: Path = None
    wait_timeout: int = 240  # Max wait for AI processing (seconds)
    stable_time: int = 3  # Seconds of stability required

    def __post_init__(self):
        # Initialize empty lists
        if self.prompts is None:
            self.prompts = []
        if self.auto_prompts is None:
            self.auto_prompts = []
        if self.validation_checks is None:
            self.validation_checks = []
        
        # Extract cookie domain from URL if not provided
        if self.cookie_domain is None and self.url:
            self.cookie_domain = _extract_domain_from_url(self.url)


# =============================================================================
# HELPER FUNCTIONS FOR record_demo() - EXTRACTED FOR CLARITY
# =============================================================================

def _validate_api_keys() -> Optional[Dict[str, Any]]:
    """Validate required API keys are present.
    
    Returns:
        None if valid, error dict if missing keys
    """
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    fal_key = os.getenv("FAL_API_KEY")

    if not elevenlabs_key:
        return {
            "success": False,
            "error": "ELEVENLABS_API_KEY not set. Real API key required for production audio generation.",
            "code": "MISSING_API_KEY",
            "suggestion": "Set ELEVENLABS_API_KEY environment variable with a real ElevenLabs API key"
        }

    if not fal_key:
        return {
            "success": False,
            "error": "FAL_API_KEY not set. Real API key required for talking head generation.",
            "code": "MISSING_API_KEY",
            "suggestion": "Set FAL_API_KEY environment variable with a real FAL.ai API key"
        }

    return None  # All keys valid


def _build_auth_cookies(config: RecordingConfig) -> List[Dict[str, Any]]:
    """Build authentication cookies from config.
    
    Priority:
    1. auth_cookies - full control, use as-is
    2. session_cookie + cookie_name + cookie_domain - build cookie dict
    3. DTS_SESSIONID env var (legacy Improvado support with warning)
    4. Empty list - no authentication
    
    Returns:
        List of cookie dicts for Playwright
    """
    # Priority 1: Full cookie dicts provided
    if config.auth_cookies:
        return config.auth_cookies

    auth_cookies = []
    
    # Priority 2: Session cookie from config
    if config.session_cookie:
        # Parse session_cookie - can be "name=value" or just "value"
        if '=' in config.session_cookie and not config.session_cookie.startswith('='):
            # Format: "name=value" or "name=value;name2=value2"
            cookie_pairs = config.session_cookie.split(';')
            for pair in cookie_pairs:
                if '=' in pair:
                    name, value = pair.split('=', 1)
                    auth_cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': config.cookie_domain or _extract_domain_from_url(config.url),
                        'path': '/',
                        'secure': True,
                        'httpOnly': False
                    })
        else:
            # Format: just "value" - use cookie_name or default
            cookie_name = config.cookie_name or 'session'
            auth_cookies.append({
                'name': cookie_name,
                'value': config.session_cookie,
                'domain': config.cookie_domain or _extract_domain_from_url(config.url),
                'path': '/',
                'secure': True,
                'httpOnly': False
            })
        return auth_cookies
    
    # Priority 3: Legacy DTS_SESSIONID env var (Improvado backward compatibility)
    session_value = os.getenv("DTS_SESSIONID")
    if session_value:
        # Check if domain looks like Improvado
        domain = config.cookie_domain or _extract_domain_from_url(config.url)
        if domain and 'improvado' in (domain or '').lower():
            auth_cookies.append({
                'name': 'dts_sessionid',
                'value': session_value,
                'domain': domain,
                'path': '/',
                'secure': True,
                'httpOnly': False
            })
            print("   ⚠️  Using DTS_SESSIONID env var for authentication (legacy Improvado support)")
        else:
            # DTS_SESSIONID set but URL is not Improvado - warn and use generic session
            print(f"   ⚠️  DTS_SESSIONID env var set but URL domain is '{domain}'")
            print(f"   💡 For non-Improvado sites, use --session-cookie or auth_cookies config")
            auth_cookies.append({
                'name': 'session',
                'value': session_value,
                'domain': domain,
                'path': '/',
                'secure': True,
                'httpOnly': False
            })
        return auth_cookies
    
    # Priority 4: No authentication - may work for public pages
    print("   ℹ️  No authentication configured - page may require login")
    return auth_cookies


def _navigate_and_load_page(
    recorder,
    config: RecordingConfig,
    markers: Dict[str, float],
    t0: float,
    screenshot_dir: Path
) -> None:
    """Navigate to URL and wait for page to load.
    
    Updates markers dict in place.
    """
    print(f"   🌐 Navigating to: {config.url}")
    try:
        recorder.page.goto(config.url, timeout=120000)
        print(f"   ✅ Page loaded successfully")
    except Exception as e:
        print(f"   ⚠️  Initial navigation timed out (this is OK, page may still be loading): {e}")
        print(f"   ⏳ Continuing to wait for page content...")
    
    # Give page more time to render after navigation timeout
    try:
        print(f"   ⏳ Waiting for DOM content...")
        recorder.page.wait_for_load_state("domcontentloaded", timeout=60000)
        print(f"   ✅ DOM content loaded")
    except Exception as e:
        print(f"   ⚠️  DOM load timeout (continuing anyway): {e}")
    
    # Additional wait for JavaScript to initialize
    print(f"   ⏳ Waiting for page to stabilize...")
    recorder.page.wait_for_timeout(3000)
    markers["t_page_loaded"] = time.time() - t0
    print(f"   📍 Page load marked at {markers['t_page_loaded']:.1f}s")

    # Take initial screenshot
    initial_screenshot = screenshot_dir / f"initial_page_{int(time.time())}.png"
    _screenshot_preserve_view(recorder.page, initial_screenshot, full_page=True)
    print(f"   📸 Initial screenshot captured")
    markers["t_screenshot_initial_page"] = time.time() - t0


def _execute_ai_agent_scenario(
    recorder,
    config: RecordingConfig,
    markers: Dict[str, float],
    t0: float,
    screenshot_dir: Path
) -> None:
    """Execute AI agent scenario with prompts.
    
    Handles finding input, typing prompts, waiting for AI completion.
    Updates markers dict in place.
    """
    print(f"   🤖 Executing AI agent scenario with {len(config.prompts)} prompts")

    # Find input field
    input_el = _find_primary_input(recorder.page)
    if not input_el:
        input_el = _find_primary_input_deep(recorder.page)
    if not input_el:
        input_el = _find_largest_input(recorder.page)
    if not input_el:
        if _focus_prompt_area(recorder.page):
            print("   ⚠️ Fallback: focused prompt area by text")

    # Process each prompt
    for prompt_idx, prompt_text in enumerate(config.prompts):
        prompt_num = prompt_idx + 1
        is_followup = prompt_idx > 0
        
        if is_followup:
            print(f"   🧩 Sending follow-up prompt {prompt_num}...")
            # Find follow-up input
            input_el = _find_enabled_followup_input(recorder.page)
            if not input_el:
                input_el = _find_enabled_followup_input_deep(recorder.page)
            if not input_el:
                input_el = _find_largest_input(recorder.page)
            if not input_el:
                if _focus_prompt_area(recorder.page):
                    print(f"   ⚠️ Fallback: focused follow-up prompt area by text")
        
        print(f"   ✍️  Entering prompt {prompt_num}: '{prompt_text}'")
        
        # Focus and click input
        if input_el:
            input_el.click()
        else:
            recorder.page.mouse.click(960, 540)  # center fallback
        markers[f"t_prompt{prompt_num}_focus"] = time.time() - t0
        
        # Screenshot after focus
        prompt_screenshot = screenshot_dir / f"prompt{prompt_num}_focus_{int(time.time())}.png"
        _screenshot_preserve_view(recorder.page, prompt_screenshot, full_page=False)
        markers[f"t_screenshot_prompt{prompt_num}_focus"] = time.time() - t0

        # Type prompt
        typing_delay = 20 if is_followup else 25
        if input_el:
            input_el.fill("")
            input_el.type(prompt_text, delay=typing_delay)
        else:
            recorder.page.keyboard.type(prompt_text, delay=typing_delay)
        markers[f"t_prompt{prompt_num}_typed"] = time.time() - t0

        # Submit prompt
        print(f"   🚀 Submitting prompt {prompt_num}...")
        try:
            recorder.page.keyboard.press("Enter")
            if not is_followup:
                print("   ✅ Submitted with Enter key")
            recorder.page.wait_for_timeout(1000)
            markers[f"t_prompt{prompt_num}_submitted"] = time.time() - t0
        except Exception as e:
            print(f"   ⚠️  Enter key failed: {e}, trying button click...")
            submit_selectors = [
                'button[type="submit"]',
                '[data-testid*="submit"]',
                'button:has-text("Send")',
                'button:has-text("Submit")',
            ]
            for submit_sel in submit_selectors:
                try:
                    btn = recorder.page.locator(submit_sel).first
                    if btn.is_visible():
                        btn.click()
                        break
                except Exception:
                    continue
            markers[f"t_prompt{prompt_num}_submitted"] = time.time() - t0

        # Wait for processing to start
        thinking_timeout = 15000 if is_followup else 5000
        try:
            recorder.page.wait_for_selector("text=/Thinking/i", timeout=thinking_timeout)
            markers[f"t_processing{prompt_num}_started"] = time.time() - t0
            if not is_followup:
                print("   ⏳ Processing started (Thinking indicator visible)")
        except Exception:
            if not is_followup:
                print("   ⚠️  No 'Thinking' indicator found, continuing anyway...")
            markers[f"t_processing{prompt_num}_started"] = time.time() - t0

        # Screenshot during processing (first prompt only)
        if not is_followup:
            processing_screenshot = screenshot_dir / f"processing{prompt_num}_started_{int(time.time())}.png"
            _screenshot_preserve_view(recorder.page, processing_screenshot, full_page=False)
            markers[f"t_screenshot_processing{prompt_num}_started"] = time.time() - t0

        # Wait for AI processing to complete
        if is_followup:
            print("   ⏳ Waiting for agent to finish follow-up...")
        try:
            _wait_agent_dashboard_done(recorder.page, timeout_s=config.wait_timeout, stable_s=config.stable_time)
        except Exception:
            error_screenshot = screenshot_dir / f"agent_done_{prompt_num}_timeout_{int(time.time())}.png"
            recorder.page.screenshot(path=str(error_screenshot))
            raise
        markers[f"t_agent_done_{prompt_num}"] = time.time() - t0

        # Screenshot after completion
        done_name = "followup_done" if is_followup else f"agent_done_{prompt_num}"
        done_screenshot = screenshot_dir / f"{done_name}_{int(time.time())}.png"
        _screenshot_preserve_view(recorder.page, done_screenshot, full_page=False)
        markers[f"t_screenshot_{done_name}"] = time.time() - t0
        print(f"   ✅ Agent finished prompt {prompt_num}." + (" Dashboard is ready." if not is_followup else ""))

        # Hold for visibility (first prompt only)
        if not is_followup:
            recorder.page.wait_for_timeout(5000)
            markers["t_hold_done_1"] = time.time() - t0

    # Scroll dashboard after all prompts
    print("   🧭 Scrolling dashboard...")
    markers["t_scroll_start"] = time.time() - t0

    try:
        recorder.page.mouse.wheel(0, 1200)
        recorder.page.wait_for_timeout(1500)
        recorder.page.mouse.wheel(0, 1200)
        recorder.page.wait_for_timeout(1500)
        recorder.page.mouse.wheel(0, -800)
        recorder.page.wait_for_timeout(1500)
    except Exception as e:
        print(f"   ⚠️  Scroll failed: {e}")

    markers["t_scroll_end"] = time.time() - t0

    scroll_screenshot = screenshot_dir / f"scroll_complete_{int(time.time())}.png"
    _screenshot_preserve_view(recorder.page, scroll_screenshot, full_page=True)
    markers["t_screenshot_scroll_start"] = time.time() - t0


def _execute_simple_dashboard_scenario(
    recorder,
    markers: Dict[str, float],
    t0: float,
    screenshot_dir: Path
) -> None:
    """Execute simple dashboard scenario - just scroll the page."""
    print("   📊 Simple dashboard scenario - scrolling page...")
    recorder.page.wait_for_timeout(3000)
    
    try:
        recorder.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        markers["t_scroll_start"] = time.time() - t0
        recorder.page.wait_for_timeout(2000)
    except Exception:
        pass

    scroll_screenshot = screenshot_dir / f"scroll_complete_{int(time.time())}.png"
    _screenshot_preserve_view(recorder.page, scroll_screenshot, full_page=True)


def _finalize_recording(
    recorder,
    markers: Dict[str, float],
    screenshot_dir: Path,
    config: RecordingConfig
) -> Dict[str, Any]:
    """Finalize recording: stop, write timeline, validate, build result.
    
    Returns:
        Success result dict
    """
    # Record final marker
    markers["t_recording_complete"] = time.time() - markers.get("_t0", time.time())

    # Collect all screenshots
    screenshot_files = [str(f) for f in screenshot_dir.glob("*.png")]

    print(f"   ✅ REAL BROWSER RECORDING COMPLETED!")
    print(f"   📹 Video recorded (finalizing)...")
    print(f"   📸 Screenshots: {len(screenshot_files)} captured")
    print(f"   📋 Timeline: {len(markers)} markers recorded")
    print(f"   ⏱️  Duration: {markers['t_recording_complete']:.1f}s")

    # Stop recording to finalize video file
    recorder.stop_recording()

    if recorder.current_video_path:
        print(f"   📹 Video recorded: {recorder.current_video_path}")

    # Write timeline using consolidated utility
    timeline_path = recorder.run_dir / "timeline.md"
    write_timeline_markers(timeline_path, markers, exclude_internal=True)
    print(f"   🧾 Timeline written: {timeline_path}")

    # Validate recording quality
    validation = validate_recording_quality(markers, recorder.run_dir)
    
    if validation.get("likely_failed"):
        print(f"   🚨 RECORDING LIKELY FAILED - Content may not have loaded properly!")
        print(f"      Check screenshots to verify page actually loaded")
    
    if validation.get("warnings"):
        print(f"   ⚠️  Warnings:")
        for warning in validation["warnings"]:
            print(f"      • {warning}")
    
    if validation.get("issues"):
        print(f"   ⚠️  Recording quality issues detected:")
        for issue in validation["issues"]:
            print(f"      • {issue}")
    
    if validation.get("suggestions"):
        print(f"   💡 Suggestions for next run:")
        for suggestion in validation["suggestions"]:
            print(f"      • {suggestion}")

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    fal_key = os.getenv("FAL_API_KEY")

    return {
        "success": True,
        "video": str(recorder.current_video_path) if recorder.current_video_path else None,
        "timeline": str(timeline_path),
        "duration": markers["t_recording_complete"],
        "markers": {k: v for k, v in markers.items() if not k.startswith("_")},
        "validation": validation,
        "scenario": config.scenario,
        "url": config.url,
        "demo_mode": False,
        "real_mode": True,
        "screenshots": screenshot_files,
        "screenshots_dir": str(screenshot_dir),
        "api_keys_available": {
            "elevenlabs": bool(elevenlabs_key),
            "fal": bool(fal_key)
        },
        "note": "Real Playwright browser recording completed with smart AI waiting.",
        "run_id": recorder.run_id,
        "run_dir": str(recorder.run_dir),
        "raw_video": str(recorder.current_video_path) if recorder.current_video_path else None,
        "audio_dir": str(recorder.run_dir / "audio"),
        "video_dir": str(recorder.run_dir),
        "final_dir": str(recorder.run_dir)
    }


def _handle_recording_error(
    recorder,
    error: Exception,
    markers: Dict[str, float],
    screenshot_dir: Optional[Path]
) -> Dict[str, Any]:
    """Handle recording error: capture screenshot, save timeline, build error result.
    
    CRITICAL: Even when recording fails, save the timeline markers that were captured!
    This allows partial success - the video up to the error point can still be used.
    
    Returns:
        Error result dict with timeline saved
    """
    # Try to capture error screenshot
    if recorder and recorder.page and screenshot_dir:
        try:
            error_screenshot = screenshot_dir / f"error_{int(time.time())}.png"
            recorder.page.screenshot(path=str(error_screenshot))
            print(f"   📸 Error screenshot captured: {error_screenshot}")
        except Exception:
            pass

    # CRITICAL: Save timeline even on error
    # This preserves all the markers captured up to the failure point
    timeline_path = None
    if recorder and recorder.run_dir and markers:
        try:
            timeline_path = recorder.run_dir / "timeline.md"
            write_timeline_markers(timeline_path, markers, exclude_internal=True)
            print(f"   🧾 Timeline saved (despite error): {timeline_path}")
        except Exception as write_error:
            print(f"   ⚠️  Failed to write timeline: {write_error}")

    error_code = classify_error(error)
    return {
        "success": False,
        "error": str(error),
        "code": error_code,
        "suggestion": get_suggestion(error),
        "markers_so_far": {k: v for k, v in markers.items() if not k.startswith("_")} if markers else None,
        "timeline": str(timeline_path) if timeline_path and timeline_path.exists() else None
    }


# =============================================================================
# MAIN RECORDING FUNCTION
# =============================================================================

def record_demo(config: RecordingConfig) -> dict:
    """
    Record REAL browser demo using the PROVEN DemoRecorder approach.

    Uses the working base_demo.py framework with smart waiting logic.
    
    This function orchestrates the recording process:
    1. Validate API keys
    2. Setup recorder with authentication
    3. Navigate to URL and wait for load
    4. Execute scenario (custom actions, AI agent, auto, or simple)
    5. Finalize and return results
    """
    # 1. Validate API keys
    key_error = _validate_api_keys()
    if key_error:
        return key_error

    recorder = None
    markers = {}
    screenshot_dir = None
    stopped = False

    try:
        print(f"🎬 REAL BROWSER RECORDING: Recording {config.url}")
        print(f"   Scenario: {config.scenario}")
        print(f"   Prompts: {len(config.prompts)}")
        print(f"   Headless: {config.headless}")
        print(f"   Wait timeout: {config.wait_timeout}s")

        # 2. Setup recorder
        from base_demo import DemoRecorder
        
        auth_cookies = _build_auth_cookies(config)
        
        recorder = DemoRecorder()
        video_prefix = config.run_id if config.run_id else config.scenario
        recorder.start_recording(
            headless=config.headless,
            incognito=True,
            cookies=auth_cookies,
            demo_effects=False,
            video_prefix=video_prefix
        )

        if config.auth_headers:
            try:
                recorder.context.set_extra_http_headers(config.auth_headers)
            except Exception:
                pass

        t0 = time.time()
        markers["t_start_recording"] = 0.0
        markers["_t0"] = t0  # Internal reference for finalization

        print(f"   📹 Recording started: {recorder.current_video_path}")
        print(f"   🔐 Authentication: {len(auth_cookies)} cookies set")

        # Setup screenshot directory
        screenshot_dir = recorder.run_dir / "raw" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # 3. Navigate and load page
        _navigate_and_load_page(recorder, config, markers, t0, screenshot_dir)

        print(f"   📋 Scenario: {config.scenario} | auto_prompts={len(config.auto_prompts or [])} | ai_prompts={len(config.prompts or [])}", flush=True)

        # 4. Execute scenario
        if config.actions:
            # Custom or guided actions from request file
            action_type = "guided" if config.scenario == "guided" else "custom"
            print(f"   🧭 Executing {action_type} actions: {len(config.actions)} steps")
            _execute_actions(
                recorder=recorder,
                actions=config.actions,
                markers=markers,
                t0=t0,
                screenshot_dir=screenshot_dir,
                wait_timeout=config.wait_timeout,
                stable_time=config.stable_time
            )
        elif config.scenario == "ai-agent" and config.prompts:
            # AI agent scenario with prompts
            _execute_ai_agent_scenario(recorder, config, markers, t0, screenshot_dir)
        elif config.scenario == "ai-agent" and not config.prompts:
            # AI agent selected but no prompts - warn user
            print("   ⚠️  ai-agent scenario selected but no prompts provided!")
            print("   💡 Provide prompts via --request file or config.prompts")
            print("   ℹ️  Recording page without AI interaction...")
        elif config.auto_prompts:
            # Auto navigation with prompts
            print(f"   🤖 Auto navigation mode enabled ({len(config.auto_prompts or [])} prompts)")
            _execute_auto_navigation(
                recorder=recorder,
                prompts=config.auto_prompts or [],
                markers=markers,
                t0=t0,
                screenshot_dir=screenshot_dir,
                validation_checks=config.validation_checks
            )
        elif config.scenario == "auto":
            # Auto mode without prompts
            print("   🤖 Auto navigation mode enabled (no prompts provided)")
        elif config.scenario == "simple-dashboard":
            # Simple dashboard - just scroll
            _execute_simple_dashboard_scenario(recorder, markers, t0, screenshot_dir)

        # 5. Finalize recording
        stopped = True
        return _finalize_recording(recorder, markers, screenshot_dir, config)

    except Exception as e:
        return _handle_recording_error(recorder, e, markers, screenshot_dir)

    finally:
        if recorder and not stopped:
            try:
                recorder.stop_recording()
            except Exception:
                pass
