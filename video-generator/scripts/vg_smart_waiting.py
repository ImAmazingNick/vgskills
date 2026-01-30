"""
Smart waiting functions for browser automation.

Extracted from vg_recording.py for reusability and maintainability.
These functions handle waiting for AI agent completion, input detection,
and dashboard visibility across various UI patterns.
"""

import re
import time
from typing import List, Optional


# =============================================================================
# SELECTOR CONSTANTS
# =============================================================================

# Selectors for detecting AI processing indicators
THINKING_SELECTORS = [
    "text=/Thinking/i",
]

# Selectors for detecting dashboard/result content
DASHBOARD_SELECTORS = [
    "canvas",
    "[data-testid*='dashboard']",
    "[data-testid*='chart']",
    "[data-testid*='widget']",
    ".dashboard",
    "[class*='dashboard']",
    ".chart-container",
    ".widget",
    "text=/Dashboard/i",
]

# Selectors for follow-up input fields (after initial interaction)
FOLLOWUP_INPUT_SELECTORS = [
    'textarea[placeholder*="Ask" i]',
    'input[placeholder*="Ask" i]',
    'textarea[placeholder*="anything" i]',
    'input[placeholder*="anything" i]',
    'textarea[placeholder]',
    'input[placeholder]',
    '[contenteditable="true"]',
    '[role="textbox"]',
]

# Selectors for primary input fields (initial prompt)
PRIMARY_INPUT_SELECTORS = [
    'textarea[placeholder*="ask" i]',
    'textarea[placeholder*="prompt" i]',
    'input[placeholder*="ask" i]',
    'input[placeholder*="prompt" i]',
    'textarea[placeholder]',
    'input[placeholder]',
    'textarea',
    'input[type="text"]',
    '[role="textbox"]',
    '[contenteditable="true"]',
    '[data-testid*="input"]',
    '[data-testid*="prompt"]',
]

# Generic input selectors for shadow DOM and size-based detection
GENERIC_INPUT_SELECTORS = [
    'textarea',
    'input[type="text"]',
    'input',
    '[contenteditable="true"]',
    '[role="textbox"]',
]


# =============================================================================
# VISIBILITY CHECK FUNCTIONS
# =============================================================================

def thinking_visible(page) -> bool:
    """Check if 'Thinking' indicator is visible."""
    try:
        t = page.locator("text=/Thinking/i")
        return t.count() > 0 and t.first.is_visible()
    except Exception:
        return False


def dashboard_visible(page, selectors: Optional[List[str]] = None) -> bool:
    """Check if dashboard elements are visible (charts, widgets, canvas).
    
    Args:
        page: Playwright page object
        selectors: Optional custom selectors (uses DASHBOARD_SELECTORS if not provided)
    """
    check_selectors = selectors or DASHBOARD_SELECTORS
    for sel in check_selectors:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            continue
    return False


def followup_input_enabled(page) -> bool:
    """Check if follow-up input is enabled (agent ready for next prompt)."""
    for sel in FOLLOWUP_INPUT_SELECTORS[:4]:  # Only check Ask/anything placeholders
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                disabled = loc.get_attribute("disabled")
                if disabled is None:
                    return True
        except Exception:
            continue
    return False


# =============================================================================
# INPUT FINDING FUNCTIONS
# =============================================================================

def find_input(
    page,
    input_type: str = "primary",
    search_frames: bool = True,
    search_shadow: bool = False,
    use_placeholder_hint: bool = True
):
    """
    Unified input finder with configurable search behavior.
    
    Args:
        page: Playwright page object
        input_type: "primary" (initial prompt) or "followup" (after interaction)
        search_frames: Whether to search across iframes
        search_shadow: Whether to search inside shadow DOM
        use_placeholder_hint: Try placeholder-based detection first (primary only)
    
    Returns:
        Locator/handle for the found input, or None
    """
    # Select appropriate selectors based on input type
    selectors = PRIMARY_INPUT_SELECTORS if input_type == "primary" else FOLLOWUP_INPUT_SELECTORS
    
    # Build list of contexts to search
    contexts = [page]
    if search_frames:
        contexts.extend(list(page.frames))
    
    # For primary inputs, try placeholder-driven detection first
    if input_type == "primary" and use_placeholder_hint:
        for ctx in contexts:
            try:
                placeholder_loc = ctx.get_by_placeholder(re.compile(r"what do you want|build|ask|prompt", re.I))
                if placeholder_loc.count() > 0 and placeholder_loc.first.is_visible():
                    return placeholder_loc.first
            except Exception:
                pass
    
    # Standard selector-based search
    for ctx in contexts:
        for sel in selectors:
            try:
                loc = ctx.locator(sel)
                if loc.count() == 0:
                    continue
                el = loc.first
                if not el.is_visible():
                    continue
                if el.get_attribute("disabled") is not None:
                    continue
                return el
            except Exception:
                continue
    
    # Shadow DOM fallback if enabled
    if search_shadow:
        return query_selector_deep(page, GENERIC_INPUT_SELECTORS)
    
    return None


def query_selector_deep(page, selectors: List[str]):
    """Find element inside shadow DOM using JS traversal."""
    try:
        handle = page.evaluate_handle(
            """(selectors) => {
                const matches = (el, sel) => {
                  try { return el.matches(sel); } catch { return false; }
                };
                const walk = (root) => {
                  const stack = [root];
                  while (stack.length) {
                    const node = stack.pop();
                    if (!node) continue;
                    for (const sel of selectors) {
                      if (node instanceof Element && matches(node, sel)) {
                        return node;
                      }
                    }
                    if (node.shadowRoot) stack.push(node.shadowRoot);
                    if (node.children) {
                      for (const child of node.children) stack.push(child);
                    }
                  }
                  return null;
                };
                return walk(document);
            }""",
            selectors
        )
        return handle
    except Exception:
        return None


def find_largest_input(page, search_shadow: bool = True):
    """
    Find the largest visible input-like element.
    
    Useful as a fallback when standard selectors don't match.
    
    Args:
        page: Playwright page object
        search_shadow: Whether to traverse shadow DOM
    """
    try:
        handle = page.evaluate_handle(
            """(searchShadow) => {
                const candidates = [];
                const selectors = [
                  'textarea',
                  'input[type="text"]',
                  'input',
                  '[contenteditable="true"]',
                  '[role="textbox"]'
                ];
                const walk = (root) => {
                  const stack = [root];
                  while (stack.length) {
                    const node = stack.pop();
                    if (!node) continue;
                    if (node instanceof Element) {
                      for (const sel of selectors) {
                        if (node.matches(sel)) {
                          const rect = node.getBoundingClientRect();
                          if (rect.width > 20 && rect.height > 20) {
                            candidates.push({node, area: rect.width * rect.height});
                          }
                        }
                      }
                    }
                    if (searchShadow && node.shadowRoot) stack.push(node.shadowRoot);
                    if (node.children) {
                      for (const child of node.children) stack.push(child);
                    }
                  }
                };
                walk(document);
                if (!candidates.length) return null;
                candidates.sort((a,b) => b.area - a.area);
                return candidates[0].node;
            }""",
            search_shadow
        )
        # Convert JSHandle to ElementHandle (which has click(), fill(), etc.)
        if handle:
            element = handle.as_element()
            return element
        return None
    except Exception:
        return None


def focus_prompt_area(page) -> bool:
    """Try to focus the prompt area using visible text/placeholder."""
    try:
        placeholder = page.get_by_placeholder(re.compile(r"what do you want to build", re.I))
        if placeholder.count() > 0 and placeholder.first.is_visible():
            placeholder.first.click()
            return True
    except Exception:
        pass
    try:
        header = page.get_by_text(re.compile(r"what can i do for you", re.I))
        if header.count() > 0 and header.first.is_visible():
            header.first.click()
            return True
    except Exception:
        pass
    return False


# =============================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# =============================================================================
# These maintain the old function signatures for existing code

def find_primary_input(page):
    """Find the primary input field for the first prompt across frames."""
    return find_input(page, input_type="primary", search_frames=True, search_shadow=False)


def find_enabled_followup_input(page):
    """Find an enabled follow-up input locator across frames."""
    return find_input(page, input_type="followup", search_frames=True, search_shadow=False)


def find_primary_input_deep(page):
    """Find primary input inside shadow DOM."""
    return find_input(page, input_type="primary", search_frames=False, search_shadow=True)


def find_enabled_followup_input_deep(page):
    """Find follow-up input inside shadow DOM."""
    return find_input(page, input_type="followup", search_frames=False, search_shadow=True)


# =============================================================================
# WAIT FUNCTIONS
# =============================================================================

def wait_agent_dashboard_done(page, timeout_s: int = 240, stable_s: int = 3) -> None:
    """Wait until agent finished and dashboard is visible.

    Conditions (must be stable for `stable_s` seconds):
    - Dashboard elements exist
    - Thinking not visible
    - Follow-up input enabled (agent ready for next prompt)
    """
    print(f"   ⏳ Waiting for AI processing (up to {timeout_s}s)...")
    start = time.time()
    stable_start = None
    last_status = ""
    
    while time.time() - start < timeout_s:
        dash = dashboard_visible(page)
        thinking = thinking_visible(page)
        input_enabled = followup_input_enabled(page)

        status = f"dash={dash}, thinking={thinking}, input={input_enabled}"
        if status != last_status:
            elapsed = int(time.time() - start)
            print(f"      [{elapsed}s] {status}")
            last_status = status

        ok = dash and (not thinking) and input_enabled
        if ok:
            if stable_start is None:
                stable_start = time.time()
                print(f"      Conditions met, waiting {stable_s}s for stability...")
            elif time.time() - stable_start >= stable_s:
                print(f"   ✅ Agent finished after {int(time.time() - start)}s")
                return
        else:
            stable_start = None

        page.wait_for_timeout(500)

    raise TimeoutError(f"Timed out waiting for dashboard completion after {timeout_s}s")


def wait_for_input(
    page,
    input_type: str = "primary",
    timeout_s: int = 120,
    fallback_to_largest: bool = True
):
    """
    Unified wait function for input fields.
    
    Args:
        page: Playwright page object
        input_type: "primary" or "followup"
        timeout_s: Maximum seconds to wait
        fallback_to_largest: Try size-based detection as last resort
    
    Returns:
        Locator/handle for the found input
        
    Raises:
        TimeoutError: If no input found within timeout
    """
    type_label = "primary" if input_type == "primary" else "follow-up"
    print(f"   ⏳ Waiting for {type_label} input (up to {timeout_s}s)...")
    start = time.time()
    
    while time.time() - start < timeout_s:
        # Try standard search (frames, no shadow)
        el = find_input(page, input_type=input_type, search_frames=True, search_shadow=False)
        if el:
            print(f"   ✅ {type_label.capitalize()} input ready")
            return el
        
        # For followup, also try primary selectors as fallback
        if input_type == "followup":
            fallback = find_input(page, input_type="primary", search_frames=True, search_shadow=False)
            if fallback:
                print(f"   ⚠️ Follow-up input not detected, using primary input")
                return fallback
        
        # Try shadow DOM search
        deep = find_input(page, input_type=input_type, search_frames=False, search_shadow=True)
        if deep:
            print(f"   ✅ {type_label.capitalize()} input found in shadow DOM")
            return deep
        
        # Size-based fallback
        if fallback_to_largest:
            largest = find_largest_input(page, search_shadow=True)
            if largest:
                print(f"   ✅ {type_label.capitalize()} input inferred by size")
                return largest
        
        page.wait_for_timeout(500)
    
    raise TimeoutError(f"Timed out waiting for {type_label} chat input to be enabled.")


# Convenience wrappers for backward compatibility
def wait_followup_input_enabled(page, timeout_s: int = 120):
    """Wait for follow-up input to be enabled and return its locator."""
    return wait_for_input(page, input_type="followup", timeout_s=timeout_s)


def wait_for_primary_input(page, timeout_s: int = 120):
    """Wait for a primary input to be available."""
    return wait_for_input(page, input_type="primary", timeout_s=timeout_s)


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES (with underscore prefix)
# =============================================================================
# These maintain compatibility with existing code that uses the old names

_thinking_visible = thinking_visible
_dashboard_visible = dashboard_visible
_followup_input_enabled = followup_input_enabled
_find_enabled_followup_input = find_enabled_followup_input
_find_primary_input = find_primary_input
_find_primary_input_deep = find_primary_input_deep
_find_enabled_followup_input_deep = find_enabled_followup_input_deep
_query_selector_deep = query_selector_deep
_find_largest_input = find_largest_input
_focus_prompt_area = focus_prompt_area
_wait_agent_dashboard_done = wait_agent_dashboard_done
_wait_followup_input_enabled = wait_followup_input_enabled
_wait_for_primary_input = wait_for_primary_input

# New unified functions also available with underscore prefix
_find_input = find_input
_wait_for_input = wait_for_input
