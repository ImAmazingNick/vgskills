"""
agent-browser wrapper for Video Generator.

Provides unified interface for AI-driven browser recording using
Vercel Labs agent-browser with reference-based element selection.

Usage:
    session = AgentBrowserSession("demo", run_dir)
    session.open("https://example.com")
    session.set_cookie("session_id", "abc123", ".example.com")
    session.record_start()
    
    # AI workflow: snapshot → identify refs → act
    result = session.snapshot(include_image=True)
    # Returns: {"refs": {"@e1": "button: Submit", "@e2": "input: Email"}, ...}
    
    session.click("@e1")
    session.fill("@e2", "test@example.com")
    session.marker("t_form_submitted")
    
    session.record_stop()
    session.close()
"""

import subprocess
import json
import time
import os
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


def _find_chrome_executable() -> Optional[str]:
    """Find Chrome executable on the system.
    
    Returns path to Chrome executable or None if not found.
    Checks common locations based on OS.
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
    elif system == "Linux":
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]
    elif system == "Windows":
        paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
    else:
        return None
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None


@dataclass
class AgentBrowserConfig:
    """Configuration for agent-browser session."""
    url: Optional[str] = None
    run_id: str = ""
    headed: bool = False
    auth_cookies: Optional[List[Dict[str, Any]]] = None
    auth_headers: Optional[Dict[str, str]] = None


class AgentBrowserSession:
    """Manages agent-browser session with video recording.
    
    Provides a higher-level interface that matches vg_session_simple.py
    patterns while using agent-browser's ref-based element selection.
    """
    
    def __init__(self, session_id: str, run_dir: Path, chrome_path: str = None):
        self.session_id = session_id
        self.run_dir = Path(run_dir)
        self.raw_dir = self.run_dir / "raw"
        self.recording_path = self.raw_dir / f"{session_id}.webm"
        self.timeline_markers: List[Dict[str, Any]] = []
        self.recording_started = False
        self.recording_start_time: Optional[float] = None  # None until recording starts
        self.browser_opened = False
        
        # Find Chrome executable - use provided path or auto-detect
        self.chrome_path = chrome_path or _find_chrome_executable()
        
    def _run_cmd(self, *args, json_output: bool = False, timeout: int = 30, 
                 global_opts: List[str] = None) -> Dict[str, Any]:
        """Execute agent-browser command.
        
        Args:
            *args: Command arguments (e.g., "open", "https://example.com")
            json_output: If True, parse output as JSON
            timeout: Command timeout in seconds
            global_opts: Additional global options (before command)
            
        Returns:
            Dict with success status and result/error
        """
        # Build command: agent-browser [global-options] <command> [args]
        cmd = ["agent-browser", "--session", self.session_id]
        
        # Use system Chrome if available (avoids need to download playwright chromium)
        if self.chrome_path:
            cmd.extend(["--executable-path", self.chrome_path])
        
        if global_opts:
            cmd.extend(global_opts)
        if json_output:
            cmd.append("--json")
        cmd.extend(str(a) for a in args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or result.stdout or f"Command failed with code {result.returncode}",
                    "code": "COMMAND_FAILED"
                }
            
            output = result.stdout.strip()
            
            if json_output and output:
                try:
                    parsed = json.loads(output)
                    return {"success": True, "data": parsed}
                except json.JSONDecodeError:
                    return {"success": True, "output": output}
            
            return {"success": True, "output": output}
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s",
                "code": "TIMEOUT"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "agent-browser not found. Install with: npm install -g agent-browser",
                "code": "NOT_INSTALLED"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "code": "UNKNOWN_ERROR"
            }
    
    def open(self, url: str, headed: bool = False) -> Dict[str, Any]:
        """Navigate to URL and start browser session.
        
        Args:
            url: URL to navigate to
            headed: If True, show browser window (for debugging)
            
        Returns:
            Result dict with success status
        """
        global_opts = ["--headed"] if headed else None
        result = self._run_cmd("open", url, json_output=True, global_opts=global_opts)
        
        if result.get("success"):
            self.browser_opened = True
            
        return result
    
    def set_cookie(self, name: str, value: str, domain: str = None, 
                   path: str = "/", url: str = None) -> Dict[str, Any]:
        """Set authentication cookie.
        
        Args:
            name: Cookie name
            value: Cookie value
            domain: Cookie domain (e.g., ".improvado.io")
            path: Cookie path (default: "/")
            url: Not used (kept for API compatibility)
            
        Returns:
            Result dict
        
        Note: Uses JavaScript document.cookie because agent-browser's 
        --domain/--path/--url flags are broken (ignored).
        """
        # Build cookie string for JavaScript
        cookie_parts = [f"{name}={value}", f"path={path}"]
        if domain:
            cookie_parts.append(f"domain={domain}")
        cookie_parts.append("secure")
        cookie_str = "; ".join(cookie_parts)
        
        # Use JavaScript to set cookie (agent-browser flags are broken)
        js_code = f'document.cookie = "{cookie_str}"'
        return self._run_cmd("eval", js_code, json_output=True)
    
    def set_cookies(self, cookies: List[Dict[str, Any]], target_url: str = None) -> Dict[str, Any]:
        """Set multiple cookies from list.
        
        Args:
            cookies: List of cookie dicts with name, value, domain, path keys
            target_url: Target URL for all cookies (preferred method)
            
        Returns:
            Result dict (last cookie result)
        """
        result = {"success": True}
        for cookie in cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            domain = cookie.get("domain", "")
            path = cookie.get("path", "/")
            url = cookie.get("url") or target_url
            if name and value:
                result = self.set_cookie(name, value, domain, path, url)
                if not result.get("success"):
                    return result
        return result
    
    def snapshot(self, include_image: bool = False) -> Dict[str, Any]:
        """Get page snapshot with element refs.
        
        This is the key method for AI-driven interaction. Returns an
        accessibility tree with refs (@e1, @e2, etc.) that can be used
        for subsequent actions.
        
        Args:
            include_image: If True, include screenshot in response (-i flag)
            
        Returns:
            Result with accessibility tree and element refs
        """
        args = ["snapshot"]
        if include_image:
            args.append("-i")
        
        result = self._run_cmd(*args, json_output=True, timeout=60)
        
        # Parse refs from snapshot for easier access
        if result.get("success") and result.get("data"):
            data = result["data"]
            # Extract refs into a simpler format
            refs = {}
            if "tree" in data:
                refs = self._extract_refs(data["tree"])
            result["refs"] = refs
            
        return result
    
    def _extract_refs(self, tree: Any, refs: Dict = None) -> Dict[str, str]:
        """Extract element refs from accessibility tree."""
        if refs is None:
            refs = {}
            
        if isinstance(tree, dict):
            ref = tree.get("ref")
            if ref:
                # Build description from role + name
                role = tree.get("role", "")
                name = tree.get("name", "")[:50]
                desc = f"{role}: {name}" if name else role
                refs[ref] = desc
            
            # Recurse into children
            for child in tree.get("children", []):
                self._extract_refs(child, refs)
                
        return refs
    
    def click(self, ref_or_selector: str) -> Dict[str, Any]:
        """Click element by @ref or CSS selector.
        
        Args:
            ref_or_selector: Element ref (e.g., "@e5") or CSS selector
            
        Returns:
            Result dict
        """
        return self._run_cmd("click", ref_or_selector, json_output=True)
    
    def fill(self, ref_or_selector: str, text: str) -> Dict[str, Any]:
        """Clear and fill input field.
        
        Args:
            ref_or_selector: Element ref or CSS selector
            text: Text to fill
            
        Returns:
            Result dict
        """
        return self._run_cmd("fill", ref_or_selector, text, json_output=True)
    
    def type(self, ref_or_selector: str, text: str, delay_ms: int = 45) -> Dict[str, Any]:
        """Type text with keystroke delay (human-like).
        
        Args:
            ref_or_selector: Element ref or CSS selector
            text: Text to type
            delay_ms: Delay between keystrokes in milliseconds
            
        Returns:
            Result dict
        """
        return self._run_cmd("type", ref_or_selector, text, 
                            f"--delay={delay_ms}", json_output=True)
    
    def press(self, key: str) -> Dict[str, Any]:
        """Press keyboard key.
        
        Args:
            key: Key to press (e.g., "Enter", "Tab", "Escape")
            
        Returns:
            Result dict
        """
        return self._run_cmd("press", key, json_output=True)
    
    def scroll(self, amount: int = 500, direction: str = "down") -> Dict[str, Any]:
        """Scroll page.
        
        Args:
            amount: Scroll amount in pixels
            direction: Scroll direction ("down" or "up")
            
        Returns:
            Result dict
        """
        scroll_amount = amount if direction == "down" else -amount
        return self._run_cmd("scroll", str(scroll_amount), json_output=True)
    
    def wait(self, seconds: float = None, condition: str = None, 
             timeout_ms: int = 30000) -> Dict[str, Any]:
        """Wait for time or condition.
        
        Args:
            seconds: Time to wait in seconds (if no condition)
            condition: Wait condition (e.g., "networkidle", selector)
            timeout_ms: Timeout for condition wait
            
        Returns:
            Result dict
        """
        if seconds and not condition:
            # Simple time wait
            time.sleep(seconds)
            return {"success": True, "output": f"Waited {seconds}s"}
        
        args = ["wait"]
        if condition:
            args.extend(["--for", condition])
        args.extend(["--timeout", str(timeout_ms)])
        return self._run_cmd(*args, json_output=True, timeout=int(timeout_ms/1000) + 5)
    
    def screenshot(self, output_path: str = None) -> Dict[str, Any]:
        """Take screenshot.
        
        Args:
            output_path: Output file path (optional)
            
        Returns:
            Result dict with screenshot path
        """
        args = ["screenshot"]
        if output_path:
            args.append(output_path)
        return self._run_cmd(*args, json_output=True)
    
    def get_text(self, ref_or_selector: str) -> Dict[str, Any]:
        """Get text content of element.
        
        Args:
            ref_or_selector: Element ref or CSS selector
            
        Returns:
            Result with text content
        """
        return self._run_cmd("get", "text", ref_or_selector, json_output=True)
    
    def record_start(self) -> Dict[str, Any]:
        """Start video recording.
        
        Records browser session to WebM format, compatible with
        existing video-generator pipeline.
        
        Returns:
            Result dict
        """
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        result = self._run_cmd("record", "start", str(self.recording_path))
        
        if result.get("success"):
            self.recording_started = True
            self.recording_start_time = time.time()
            self._add_marker("t_start_recording")
            
        return result
    
    def record_stop(self) -> Dict[str, Any]:
        """Stop video recording.
        
        Finalizes recording and saves timeline markers.
        
        Returns:
            Result dict with video path and duration
        """
        result = self._run_cmd("record", "stop")
        
        if result.get("success") or self.recording_started:
            self.recording_started = False
            self._add_marker("t_end")
            self._save_timeline()
            
            duration = time.time() - self.recording_start_time if self.recording_start_time else 0
            
            result = {
                "success": True,
                "video": str(self.recording_path),
                "duration": f"{duration:.1f}s",
                "timeline": str(self.run_dir / "timeline.md")
            }
            
        return result
    
    def marker(self, name: str) -> Dict[str, Any]:
        """Add timeline marker at current time.
        
        Markers are used for audio synchronization in composition phase.
        
        Args:
            name: Marker name (e.g., "t_prompt_submitted", "t_result_shown")
            
        Returns:
            Result dict with marker info
        """
        marker_time = self._add_marker(name)
        return {
            "success": True,
            "marker": name,
            "time": f"{marker_time:.2f}s"
        }
    
    def _add_marker(self, name: str) -> float:
        """Internal: add marker with timestamp relative to recording start."""
        if self.recording_start_time is None:
            print(f"⚠️  Warning: Marker '{name}' added before recording started - time will be 0.0s")
            marker_time = 0.0
        else:
            marker_time = time.time() - self.recording_start_time
            
        self.timeline_markers.append({
            "name": name,
            "time": marker_time,
            "index": len(self.timeline_markers)
        })
        return marker_time
    
    def _save_timeline(self):
        """Save timeline markers to markdown file.
        
        Creates timeline.md compatible with existing vg pipeline.
        """
        timeline_path = self.run_dir / "timeline.md"
        
        if not self.timeline_markers:
            return
        
        lines = ["| Marker | Time (s) |", "|--------|----------|"]
        for m in sorted(self.timeline_markers, key=lambda x: x["time"]):
            lines.append(f"| {m['name']} | {m['time']:.2f} |")
        
        timeline_path.write_text("\n".join(lines))
    
    def close(self) -> Dict[str, Any]:
        """Close browser session.
        
        Stops recording if still active and closes browser.
        
        Returns:
            Result dict
        """
        if self.recording_started:
            self.record_stop()
            
        result = self._run_cmd("close")
        self.browser_opened = False
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get session status.
        
        Returns:
            Status dict with recording state and markers
        """
        return {
            "success": True,
            "session_id": self.session_id,
            "browser_opened": self.browser_opened,
            "recording_started": self.recording_started,
            "markers_count": len(self.timeline_markers),
            "run_dir": str(self.run_dir)
        }


# Session registry for CLI commands
_sessions: Dict[str, AgentBrowserSession] = {}


def get_or_create_session(run_id: str, run_dir: Path = None) -> AgentBrowserSession:
    """Get existing session or create new one.
    
    Args:
        run_id: Session/run ID
        run_dir: Run directory (required for new sessions)
        
    Returns:
        AgentBrowserSession instance
    """
    if run_id not in _sessions:
        if run_dir is None:
            from project_paths import run_paths
            run_dir = run_paths(run_id).run_dir
        _sessions[run_id] = AgentBrowserSession(run_id, run_dir)
    return _sessions[run_id]


def remove_session(run_id: str):
    """Remove session from registry."""
    if run_id in _sessions:
        del _sessions[run_id]


def check_agent_browser_installed() -> Dict[str, Any]:
    """Check if agent-browser CLI is installed.
    
    Returns:
        Dict with installed status and version
    """
    try:
        result = subprocess.run(
            ["agent-browser", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return {
                "installed": True,
                "version": version
            }
        return {
            "installed": False,
            "error": "agent-browser found but returned error"
        }
    except FileNotFoundError:
        return {
            "installed": False,
            "error": "agent-browser not found. Install with: npm install -g agent-browser"
        }
    except Exception as e:
        return {
            "installed": False,
            "error": str(e)
        }
