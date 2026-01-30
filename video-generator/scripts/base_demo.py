"""
Base Demo Framework for Product Demo Video Automation

This module provides the foundational classes and utilities for creating
automated product demo videos using Playwright browser automation.
"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
import time
import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoConfig:
    """Configuration class for demo settings"""

    def __init__(self, config_file: str = "config/demo_config.json"):
        self.config_file = config_file
        # Always anchor to repo root so recordings land in /videos/runs
        from project_paths import project_root
        self.base_dir = project_root()
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "video": {
                "width": 1920,
                "height": 1080,
                "fps": 30
            },
            "timing": {
                "slow_mo": 1000,  # milliseconds
                "action_delay": 2.0,  # seconds
                "page_load_timeout": 30000  # milliseconds
            },
            "directories": {
                "raw_videos": "videos/raw",
                "processed_videos": "videos/processed"
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


class DemoRecorder:
    """Main class for recording demo videos"""

    def __init__(self, config: Optional[DemoConfig] = None):
        self.config = config or DemoConfig()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._recording_started_at: Optional[float] = None
        self.current_video_path: Optional[Path] = None
        self.run_id: Optional[str] = None
        self.run_dir: Optional[Path] = None

    def __enter__(self):
        """Context manager entry"""
        self.start_recording()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_recording()

    def start_recording(
        self,
        headless: bool = False,
        incognito: bool = False,
        cookies: Optional[List[Dict[str, str]]] = None,
        demo_effects: bool = False,
        video_prefix: str = "ai_agent_demo",
        use_prefix_as_run_id: bool = False,
    ) -> None:
        """Initialize Playwright and start video recording

        Args:
            headless: Run browser in headless mode
            incognito: Use incognito/private browsing mode (default context isolation)
            cookies: List of cookie dictionaries to set before navigation
            demo_effects: Enable visual demo effects
            video_prefix: Prefix for video files and run_id
            use_prefix_as_run_id: If True, use video_prefix exactly as run_id without adding timestamp
        """
        logger.info("Starting demo recording session")

        self.playwright = sync_playwright().start()
        self._recording_started_at = time.time()

        # Per-run directory structure:
        # videos/runs/<run_id>/raw + videos/runs/<run_id>/processed
        # 
        # When use_prefix_as_run_id=True (e.g., from session commands), use prefix exactly.
        # Otherwise, check for existing timestamp or add one.
        import re
        timestamp_pattern = r'_\d{8}_\d{6}$'
        if use_prefix_as_run_id or re.search(timestamp_pattern, video_prefix):
            # Use prefix as-is (session commands provide exact run_id)
            self.run_id = video_prefix
        else:
            # No timestamp - add one (original behavior for non-session usage)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.run_id = f"{video_prefix}_{timestamp}"

        # Launch browser with slow motion for better demo pacing
        slow_mo = self.config.get('timing.slow_mo') if not headless else 0
        video_size = {
            "width": self.config.get('video.width'),
            "height": self.config.get('video.height')
        }
        window_size_arg = f"--window-size={video_size['width']},{video_size['height']}"
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--start-maximized',
                window_size_arg
            ]
        )

        # Create context with video recording
        base_raw_dir = Path(self.config.get('directories.raw_videos'))
        if not base_raw_dir.is_absolute():
            base_raw_dir = (self.config.base_dir / base_raw_dir).resolve()

        # Keep legacy raw dir as-is, but write new recordings under videos/runs/<run_id>/raw.
        # If config points somewhere else, we still create a sibling "runs" folder under it.
        video_dir = base_raw_dir.parent / "runs" / self.run_id / "raw"
        # run_dir should be the per-run folder (videos/runs/<run_id>)
        self.run_dir = video_dir.parent
        os.makedirs(video_dir, exist_ok=True)

        # Create context with video recording (Playwright records WebM)
        context_options = {
            "record_video_dir": video_dir,
            "record_video_size": video_size,
            "viewport": video_size,
            "screen": video_size
        }

        if incognito:
            logger.info("Using incognito/private browsing mode")
            # Incognito mode is the default for new_context() - no additional flags needed
            # Each context is isolated like incognito tabs
            context_options.update({
                # Additional privacy settings can be added here if needed
                "bypass_csp": False,  # Respect content security policy
            })

        self.context = self.browser.new_context(**context_options)

        # Inject demo video effects BEFORE any page loads
        if demo_effects:
            self._enable_demo_effects()

        # Set cookies if provided
        if cookies:
            self._set_cookies(cookies)

        self.page = self.context.new_page()

        # Set default timeouts
        self.page.set_default_timeout(self.config.get('timing.page_load_timeout'))

        logger.info(f"Recording started. Videos will be saved to: {video_dir}")

    def _enable_demo_effects(self) -> None:
        """Inject demo-style cursor + click highlight/ripple effects.

        This is captured directly in Playwright video recordings because it renders in-page.
        """
        if not self.context:
            raise Exception("Context not initialized yet")

        enhancements_script = r"""
(() => {
  if (window.__demoEnhancementsAdded) return;
  window.__demoEnhancementsAdded = true;

  // Hide default cursor
  document.documentElement.style.cursor = 'none';

  // Big cursor overlay
  const cursor = document.createElement('div');
  cursor.id = '__demo_cursor';
  Object.assign(cursor.style, {
    position: 'fixed',
    width: '42px',
    height: '42px',
    border: '4px solid #FFD400',
    borderRadius: '50%',
    background: 'rgba(255, 212, 0, 0.18)',
    pointerEvents: 'none',
    zIndex: '2147483647',
    left: '0px',
    top: '0px',
    transform: 'translate(-50%, -50%)',
    boxShadow: '0 0 18px rgba(255, 212, 0, 0.85)',
    transition: 'transform 0.05s linear'
  });
  const arrow = document.createElement('div');
  arrow.textContent = '➤';
  Object.assign(arrow.style, {
    position: 'absolute',
    left: '9px',
    top: '-6px',
    fontSize: '34px',
    color: '#FFD400',
    textShadow: '0 0 10px rgba(255, 212, 0, 0.9)',
    transform: 'rotate(10deg)'
  });
  cursor.appendChild(arrow);
  const mountCursor = () => {
    if (cursor.isConnected) return;
    (document.body || document.documentElement).appendChild(cursor);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountCursor, { once: true });
  } else {
    mountCursor();
  }

  // CSS animations
  const style = document.createElement('style');
  style.textContent = `
    @keyframes __demo_ripple {
      to { transform: translate(-50%, -50%) scale(4); opacity: 0; }
    }
    .__demo_ripple {
      position: fixed;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: rgba(255, 212, 0, 0.55);
      pointer-events: none;
      z-index: 2147483646;
      animation: __demo_ripple 0.65s ease-out;
    }
    @keyframes __demo_glow {
      0% { outline: 0px solid rgba(255, 212, 0, 0.0); box-shadow: 0 0 0 rgba(255, 212, 0, 0.0); transform: scale(1); }
      45% { outline: 4px solid rgba(255, 212, 0, 0.95); box-shadow: 0 0 26px rgba(255, 212, 0, 0.75); transform: scale(1.03); }
      100% { outline: 0px solid rgba(255, 212, 0, 0.0); box-shadow: 0 0 0 rgba(255, 212, 0, 0.0); transform: scale(1); }
    }
    .__demo_click_glow {
      animation: __demo_glow 0.65s ease-in-out;
    }
  `;
  const mountStyle = () => {
    if (style.isConnected) return;
    (document.head || document.documentElement).appendChild(style);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountStyle, { once: true });
  } else {
    mountStyle();
  }

  // Track cursor
  // Initialize cursor to center so it isn't stuck at (0,0) if no mousemove yet.
  const initX = Math.round(window.innerWidth / 2);
  const initY = Math.round(window.innerHeight / 2);
  cursor.style.left = `${initX}px`;
  cursor.style.top = `${initY}px`;

  document.addEventListener('mousemove', (e) => {
    if (!cursor.isConnected) return;
    cursor.style.left = `${e.clientX}px`;
    cursor.style.top = `${e.clientY}px`;
  }, { passive: true });

  function pickTarget(el) {
    return el.closest('button,a,[role="button"],input,textarea,select,[data-testid]') || el;
  }

  // Ripple + glow on click
  document.addEventListener('click', (e) => {
    if (!document.body) return;
    const ripple = document.createElement('div');
    ripple.className = '__demo_ripple';
    ripple.style.left = `${e.clientX}px`;
    ripple.style.top = `${e.clientY}px`;
    document.body.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);

    const target = pickTarget(e.target);
    target.classList.add('__demo_click_glow');
    setTimeout(() => target.classList.remove('__demo_click_glow'), 700);
  }, true);
})();
"""

        # Run on every new document
        self.context.add_init_script(enhancements_script)

    def stop_recording(self) -> None:
        """Stop recording and cleanup resources"""
        logger.info("Stopping demo recording session")

        # Close page first to flush video
        if self.page:
            try:
                self.page.close()
            except Exception:
                pass

        if self.context:
            try:
                self.context.close()
            except Exception:
                pass

        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass

        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass

        # Rename latest video file to timestamp format (after close so file exists)
        self._rename_latest_video_to_timestamp(wait_seconds=10)

        # Verify video was created and is valid
        if self.current_video_path and self.current_video_path.exists():
            video_size = self.current_video_path.stat().st_size
            if video_size > 1000:  # At least 1KB indicates valid video
                logger.info(f"✅ Video successfully created: {self.current_video_path.name} ({video_size} bytes)")
            else:
                logger.warning(f"⚠️  Video file created but very small: {self.current_video_path.name} ({video_size} bytes)")
        else:
            logger.error("❌ Video file was not created")

        logger.info("Recording session ended")

    def get_video_path(self) -> Optional[Path]:
        """Get the path of the current video recording"""
        return self.current_video_path

    def _rename_latest_video_to_timestamp(self, wait_seconds: int = 10) -> None:
        """Rename the latest recorded .webm video to a timestamped name.

        Playwright decides the actual filename. We rename after closing the context,
        when the .webm has been fully written to disk.
        """
        try:
            if not self.run_id:
                return

            base_raw_dir = Path(self.config.get("directories.raw_videos"))
            if not base_raw_dir.is_absolute():
                base_raw_dir = (self.config.base_dir / base_raw_dir).resolve()

            # We record into the per-run raw dir.
            video_dir = base_raw_dir.parent / "runs" / self.run_id / "raw"

            start = time.time()
            candidate: Optional[Path] = None

            # Wait for the newest .webm file created after recording started.
            while time.time() - start < wait_seconds:
                webm_files = list(video_dir.glob("*.webm"))
                if webm_files:
                    # Prefer files newer than the start time if available
                    if self._recording_started_at is not None:
                        newer = [f for f in webm_files if f.stat().st_mtime >= self._recording_started_at - 1]
                        candidate = max(newer, key=lambda f: f.stat().st_mtime) if newer else None
                    if candidate is None:
                        candidate = max(webm_files, key=lambda f: f.stat().st_mtime)

                    # Ensure size is stable for a moment (video finished writing)
                    s1 = candidate.stat().st_size
                    time.sleep(0.5)
                    s2 = candidate.stat().st_size
                    if s2 == s1 and s2 > 0:
                        break

                time.sleep(0.5)

            if candidate is None or not candidate.exists():
                return

            new_name = f"{self.run_id}.webm"
            new_path = candidate.parent / new_name

            # Avoid overwriting
            if new_path.exists():
                new_name = f"{self.run_id}_{int(time.time())}.webm"
                new_path = candidate.parent / new_name

            candidate.rename(new_path)
            self.current_video_path = new_path
            logger.info(f"📹 Video renamed to: {new_name}")
        except Exception as e:
            logger.warning(f"⚠️  Could not rename video file: {e}")

    def is_video_ready(self) -> bool:
        """Check if the video file exists and has content"""
        video_path = self.get_video_path()
        if video_path and video_path.exists():
            return video_path.stat().st_size > 1000  # At least 1KB
        return False

    def set_cookies(self, cookies: List[Dict[str, str]]) -> None:
        """Set cookies in the current browser context

        Args:
            cookies: List of cookie dictionaries with keys: name, value, domain, path
        """
        if not self.context:
            raise Exception("Browser context not initialized. Call start_recording() first.")

        self._set_cookies(cookies)

    def navigate_to(self, url: str, wait_for_load: bool = True, timeout: int = 60000) -> None:
        """Navigate to a URL with optional load waiting"""
        logger.info(f"Navigating to: {url}")
        self.page.goto(url, timeout=timeout)

        if wait_for_load:
            try:
                # Try networkidle first, but fall back to domcontentloaded if it takes too long
                self.page.wait_for_load_state('networkidle', timeout=30000)
            except:
                logger.warning("Network idle state not reached, waiting for DOM content loaded")
                self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            self._add_delay()

    def click_element(self, selector: str, description: str = "") -> None:
        """Click an element with logging and delay"""
        logger.info(f"Clicking element: {selector}" + (f" ({description})" if description else ""))

        # Wait for element to be visible
        self.page.wait_for_selector(selector, state='visible')

        # Move mouse to the element (for visible cursor effects), then click
        try:
            el = self.page.query_selector(selector)
            if el:
                bb = el.bounding_box()
                if bb:
                    self.page.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        except Exception:
            pass

        self.page.click(selector)
        self._add_delay()

    def fill_input(self, selector: str, value: str, description: str = "") -> None:
        """Fill an input field with logging and delay"""
        logger.info(f"Filling input {selector} with value: {value}" + (f" ({description})" if description else ""))

        self.page.wait_for_selector(selector, state='visible')
        # Move mouse for demo cursor visibility
        try:
            el = self.page.query_selector(selector)
            if el:
                bb = el.bounding_box()
                if bb:
                    self.page.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        except Exception:
            pass
        self.page.click(selector)
        self.page.fill(selector, value)
        self._add_delay()

    def wait_for_url(self, url_pattern: str, timeout: int = 10000) -> None:
        """Wait for URL to match pattern"""
        logger.info(f"Waiting for URL pattern: {url_pattern}")
        self.page.wait_for_url(url_pattern, timeout=timeout)
        self._add_delay()

    def take_screenshot(self, name: str) -> str:
        """Take a screenshot for debugging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        base_raw_dir = Path(self.config.get('directories.raw_videos'))
        if not base_raw_dir.is_absolute():
            base_raw_dir = (self.config.base_dir / base_raw_dir).resolve()

        if self.run_id:
            screenshot_dir = base_raw_dir.parent / "runs" / self.run_id / "raw" / "screenshots"
        else:
            screenshot_dir = base_raw_dir / "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)

        filepath = screenshot_dir / filename
        self.page.screenshot(path=str(filepath))
        logger.info(f"Screenshot saved: {filepath}")
        return filepath

    def wait_for_ai_processing(self, timeout: int = 60000, indicator_selector: str = None) -> None:
        """Wait for AI processing to complete

        Args:
            timeout: Maximum time to wait in milliseconds (default: 60 seconds)
            indicator_selector: Optional selector for processing indicator to disappear
        """
        logger.info("Waiting for AI processing to complete...")

        # First wait for network to be idle (no ongoing requests)
        self.page.wait_for_load_state('networkidle', timeout=timeout)

        # If a processing indicator selector is provided, wait for it to disappear
        if indicator_selector:
            try:
                self.page.wait_for_selector(indicator_selector, state='hidden', timeout=timeout)
                logger.info("Processing indicator disappeared - AI processing likely complete")
            except Exception as e:
                logger.warning(f"Processing indicator didn't disappear: {e}")

        # Wait for any dynamic content to stabilize
        try:
            self.page.wait_for_function(
                "() => !document.querySelector('[data-loading], .loading, .spinner, .processing')",
                timeout=10000
            )
            logger.info("No loading indicators found - content appears stable")
        except Exception as e:
            logger.info(f"Loading indicators still present or timed out: {e}")

        self._add_delay()
        logger.info("AI processing wait completed")

    def wait_for_dashboard_generation(self, timeout: int = 90000) -> None:
        """Wait for dashboard content to be generated and rendered"""
        logger.info("Waiting for dashboard generation...")

        # Do NOT rely on networkidle (SSE/WebSockets can prevent it).
        # Instead, wait for dashboard-like DOM elements to appear.

        # Look for common dashboard elements
        dashboard_selectors = [
            '[data-testid*="dashboard"]',
            '.dashboard',
            '[class*="dashboard"]',
            'canvas',  # Charts/graphs
            '[data-testid*="chart"]',
            '[data-testid*="widget"]',
            '.chart-container',
            '.widget'
        ]

        found_selector = None
        start = time.time()
        while (time.time() - start) * 1000 < timeout:
            for selector in dashboard_selectors:
                try:
                    if self.page.locator(selector).first.is_visible():
                        found_selector = selector
                        logger.info(f"Found dashboard element: {selector}")
                        break
                except Exception:
                    continue
            if found_selector:
                break
            self.page.wait_for_timeout(1000)

        if not found_selector:
            logger.warning("No standard dashboard elements found - waiting for any significant content change")

            # Alternative: wait for significant DOM changes or new content
            try:
                self.page.wait_for_function(
                    "() => document.body.innerText.length > 100",  # Wait for substantial content
                    timeout=timeout
                )
                logger.info("Significant content loaded")
            except Exception as e:
                logger.warning(f"Content loading detection failed: {e}")

        # Give extra time for animations and rendering to complete
        time.sleep(2)
        logger.info("Dashboard generation wait completed")

    def wait_for_element_and_interact(self, selector: str, action: str = "click",
                                    timeout: int = 30000, description: str = "") -> None:
        """Wait for an element to be ready and perform an action

        Args:
            selector: CSS selector for the element
            action: Action to perform ('click', 'visible', 'enabled')
            timeout: Timeout in milliseconds
            description: Description for logging
        """
        logger.info(f"Waiting for element and performing {action}: {selector}" +
                   (f" ({description})" if description else ""))

        if action == "click":
            # Wait for element to be visible and enabled
            self.page.wait_for_selector(selector, state='visible', timeout=timeout)

            # Additional check for enabled state if it's a button/input
            if self.page.locator(selector).get_attribute('disabled') is None:
                self.page.click(selector)
            else:
                raise Exception(f"Element {selector} is disabled")

        elif action == "visible":
            self.page.wait_for_selector(selector, state='visible', timeout=timeout)

        elif action == "enabled":
            self.page.wait_for_selector(selector, state='visible', timeout=timeout)
            self.page.wait_for_function(
                f"() => !document.querySelector('{selector}').disabled",
                timeout=timeout
            )

        self._add_delay()

    def _set_cookies(self, cookies: List[Dict[str, str]]) -> None:
        """Set cookies in the browser context

        Args:
            cookies: List of cookie dictionaries with keys: name, value, domain, path
        """
        logger.info(f"Setting {len(cookies)} cookies in browser context")

        for cookie in cookies:
            try:
                # Ensure required fields are present
                if not all(key in cookie for key in ['name', 'value']):
                    logger.warning(f"Skipping invalid cookie: {cookie}")
                    continue

                # Domain is required for cookies - warn if missing
                domain = cookie.get('domain')
                if not domain:
                    logger.warning(f"Cookie '{cookie['name']}' missing domain - may not work correctly")

                # Set default values for optional fields
                cookie_data = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': domain,  # No default - should be provided
                    'path': cookie.get('path', '/'),
                    'httpOnly': cookie.get('httpOnly', False),
                    'secure': cookie.get('secure', True)
                }

                self.context.add_cookies([cookie_data])
                logger.info(f"Set cookie: {cookie['name']}")

            except Exception as e:
                logger.error(f"Failed to set cookie {cookie.get('name', 'unknown')}: {e}")

    def _add_delay(self) -> None:
        """Add configured delay between actions"""
        delay = self.config.get('timing.action_delay')
        if delay > 0:
            time.sleep(delay)

    def execute_action(self, action: Dict[str, Any]) -> None:
        """Execute a predefined action from configuration"""
        action_type = action.get('type')

        if action_type == 'navigate':
            self.navigate_to(action['url'])
        elif action_type == 'type_with_delay':
            selector = action['selector']
            value = action['value']
            delay_ms = int(action.get('delay_ms', 45))
            logger.info(f"Typing with delay into {selector}: {value}")
            timeout_ms = int(action.get('timeout', 30000))
            start = time.time()

            # Find a visible AND enabled element among the selector list.
            el = None
            while (time.time() - start) * 1000 < timeout_ms:
                try:
                    candidates = self.page.query_selector_all(selector)
                    for c in candidates:
                        try:
                            if not c.is_visible():
                                continue
                            # Enabled: no disabled attribute (for inputs/textarea/buttons)
                            if c.get_attribute("disabled") is not None:
                                continue
                            el = c
                            break
                        except Exception:
                            continue
                    if el:
                        break
                except Exception:
                    pass
                self.page.wait_for_timeout(250)

            if not el:
                raise Exception(f"Timeout waiting for enabled element: {selector}")

            # Use real mouse move/click so the in-page cursor/ripple effects appear in video.
            try:
                bb = el.bounding_box()
                if bb:
                    self.page.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
                    self.page.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
                else:
                    el.click()
            except Exception:
                el.click()

            el.fill("")
            el.type(value, delay=delay_ms)
            self._add_delay()
        elif action_type == 'submit_from_input':
            selector = action['selector']
            logger.info(f"Submitting from input bounding box: {selector}")
            self.page.wait_for_selector(selector, state='visible', timeout=action.get('timeout', 30000))
            input_el = self.page.query_selector(selector)
            if not input_el:
                raise Exception(f"Input element not found for selector: {selector}")
            bb = input_el.bounding_box()
            if not bb:
                raise Exception("Could not get input bounding box")
            target_x = bb["x"] + bb["width"]
            target_y = bb["y"] + bb["height"] / 2

            def _try_wait_thinking(ms: int = 8000) -> bool:
                try:
                    self.page.wait_for_selector("text=/Thinking/i", timeout=ms)
                    return True
                except Exception:
                    return False

            # 1) Prefer a nearby icon submit button (arrow) near the input.
            clicked = False
            try:
                candidates = []
                for btn in self.page.query_selector_all('button, [role="button"]'):
                    try:
                        if not btn.is_visible():
                            continue
                        bbb = btn.bounding_box()
                        if not bbb:
                            continue

                        # Must be to the right of (or overlapping) input's right edge and aligned vertically.
                        cx = bbb["x"] + bbb["width"] / 2
                        cy = bbb["y"] + bbb["height"] / 2
                        if cx < (target_x - 10):
                            continue
                        if cy < (bb["y"] - 80) or cy > (bb["y"] + bb["height"] + 80):
                            continue

                        # Prefer icon buttons (svg) and avoid labeled chips/buttons.
                        has_svg = btn.query_selector("svg") is not None
                        text = (btn.inner_text() or "").strip()
                        score = 0.0
                        if text:
                            score += 1000.0
                        if has_svg:
                            score -= 100.0
                        score += abs(cx - (target_x + 40)) + abs(cy - target_y)
                        candidates.append((score, btn))
                    except Exception:
                        continue

                candidates.sort(key=lambda x: x[0])
                if candidates:
                    btn = candidates[0][1]
                    bbb = btn.bounding_box()
                    if bbb:
                        self.page.mouse.move(bbb["x"] + bbb["width"] / 2, bbb["y"] + bbb["height"] / 2)
                        self.page.mouse.click(bbb["x"] + bbb["width"] / 2, bbb["y"] + bbb["height"] / 2)
                    else:
                        btn.click()
                    clicked = True
            except Exception:
                clicked = False

            if clicked and _try_wait_thinking():
                self._add_delay()
                return

            # 2) Coordinate fallback: click around where the arrow usually is (slightly right of input).
            for dx in (40, 60, 90, 120, 150, 20, 10, -10):
                try:
                    self.page.mouse.move(target_x + dx, target_y)
                    self.page.mouse.click(target_x + dx, target_y)
                    if _try_wait_thinking(4000):
                        self._add_delay()
                        return
                except Exception:
                    continue

            # 3) Keyboard fallback(s): Enter, then Ctrl/Cmd+Enter.
            try:
                self.page.click(selector)
            except Exception:
                pass

            for key in ("Enter", "Control+Enter", "Meta+Enter"):
                try:
                    self.page.keyboard.press(key)
                    if _try_wait_thinking(6000):
                        self._add_delay()
                        return
                except Exception:
                    continue

            # If we got here, submission didn't start.
            raise Exception("Could not submit prompt (arrow click/keyboard submit failed)")
            self._add_delay()
        elif action_type == 'wait_agent_done':
            timeout = int(action.get('timeout', 300000))
            chat_selector = action.get(
                'chat_selector',
                'textarea[placeholder*="Ask" i], input[placeholder*="Ask" i], textarea[placeholder*="anything" i], input[placeholder*="anything" i]',
            )
            require_dashboard = bool(action.get('require_dashboard', False))
            logger.info("Waiting for AI agent processing to complete...")
            start = time.time()
            # Best-effort: wait for processing to start
            try:
                self.page.wait_for_selector("text=/Thinking/i", timeout=min(30000, timeout))
            except Exception:
                pass
            while (time.time() - start) * 1000 < timeout:
                try:
                    t = self.page.locator("text=/Thinking/i")
                    thinking_visible = t.count() > 0 and t.first.is_visible()
                except Exception:
                    thinking_visible = False

                # We only consider the agent "done" when the follow-up chat input is ENABLED.
                chat_enabled = False
                try:
                    chat_el = self.page.locator(chat_selector).first
                    if chat_el.count() > 0:
                        disabled_attr = chat_el.get_attribute("disabled")
                        chat_enabled = disabled_attr is None
                except Exception:
                    chat_enabled = False

                # Dashboard heuristics (right-side panel). We require this for the first prompt,
                # so the video shows chat on the left and dashboard on the right.
                dashboard_visible = False
                try:
                    dashboard_visible = (
                        self.page.locator("canvas").count() > 0
                        or self.page.locator('[data-testid*="dashboard"]').count() > 0
                        or self.page.locator('[data-testid*="widget"]').count() > 0
                        or self.page.locator('[class*="dashboard"]').count() > 0
                        or self.page.locator("text=/Dashboard/i").count() > 0
                    )
                except Exception:
                    dashboard_visible = False

                if chat_enabled and (dashboard_visible or not require_dashboard) and not thinking_visible:
                    self._add_delay()
                    return
                self.page.wait_for_timeout(1000)
            raise Exception(f"Timed out waiting for agent to finish within {timeout}ms")
        elif action_type == 'click':
            self.click_element(action['selector'], action.get('description', ''))
        elif action_type == 'fill':
            self.fill_input(action['selector'], action['value'], action.get('description', ''))
        elif action_type == 'wait_url':
            self.wait_for_url(action['pattern'], action.get('timeout', 10000))
        elif action_type == 'delay':
            time.sleep(action.get('seconds', 1.0))
        elif action_type == 'screenshot':
            self.take_screenshot(action.get('name', 'step'))
        elif action_type == 'wait_ai_processing':
            self.wait_for_ai_processing(
                timeout=action.get('timeout', 60000),
                indicator_selector=action.get('indicator_selector')
            )
        elif action_type == 'wait_dashboard':
            self.wait_for_dashboard_generation(timeout=action.get('timeout', 90000))
        elif action_type == 'wait_and_click':
            self.wait_for_element_and_interact(
                action['selector'],
                'click',
                action.get('timeout', 30000),
                action.get('description', '')
            )
        elif action_type == 'wait_and_fill':
            # Wait for element and then fill it
            self.wait_for_element_and_interact(
                action['selector'],
                'visible',
                action.get('timeout', 30000),
                action.get('description', '')
            )
            self.fill_input(action['selector'], action['value'], action.get('description', ''))
        else:
            logger.warning(f"Unknown action type: {action_type}")


class DemoScenario:
    """Class to define and run demo scenarios"""

    def __init__(
        self,
        name: str,
        actions: List[Dict[str, Any]],
        config: Optional[DemoConfig] = None,
        cookies: Optional[List[Dict[str, str]]] = None,
        incognito: bool = True,
        demo_effects: bool = False,
    ):
        self.name = name
        self.actions = actions
        self.config = config or DemoConfig()
        self.cookies = cookies or []
        self.incognito = incognito
        self.demo_effects = demo_effects

    def run(self, recorder: DemoRecorder) -> None:
        """Run the demo scenario"""
        logger.info(f"Starting demo scenario: {self.name}")

        for i, action in enumerate(self.actions, 1):
            logger.info(f"Executing step {i}/{len(self.actions)}")
            try:
                recorder.execute_action(action)
            except Exception as e:
                logger.error(f"Error in step {i}: {e}")
                # Take screenshot for debugging
                recorder.take_screenshot(f"error_step_{i}")
                raise

        logger.info(f"Demo scenario '{self.name}' completed successfully")


def create_demo_context(playwright, headless: bool = False, config: Optional[DemoConfig] = None) -> DemoRecorder:
    """Factory function to create a demo recording context"""
    config = config or DemoConfig()
    recorder = DemoRecorder(config)
    recorder.start_recording(headless=headless)
    return recorder


def load_scenario_from_config(scenario_name: str, config_file: str = "config/demo_config.json") -> Optional[DemoScenario]:
    """Load a scenario from configuration file"""
    config = DemoConfig(config_file)
    scenarios = config.get('scenarios', {})

    if scenario_name not in scenarios:
        logger.error(f"Scenario '{scenario_name}' not found in config")
        return None

    scenario_data = scenarios[scenario_name]
    actions = scenario_data.get('actions', [])
    cookies = scenario_data.get('cookies', [])
    incognito = bool(scenario_data.get('incognito', True))
    demo_effects = bool(scenario_data.get('demo_effects', False))
    return DemoScenario(
        scenario_name,
        actions,
        config,
        cookies=cookies,
        incognito=incognito,
        demo_effects=demo_effects,
    )