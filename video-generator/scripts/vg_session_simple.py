"""
Simple session - one MD file, no JSON, no transformations.

session.md contains:
- Status (running/stopped)
- Commands & responses (appended in real-time)
- Markers (extracted at end)
"""

import os
import re
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from project_paths import run_paths
from base_demo import DemoRecorder


@dataclass
class SessionConfig:
    url: Optional[str]
    run_id: str
    headless: bool = False
    auth_cookies: Optional[List[Dict[str, Any]]] = None
    auth_headers: Optional[Dict[str, str]] = None


def _session_md_path(run_id: str) -> Path:
    return run_paths(run_id).run_dir / "session.md"


def _read_session_status(path: Path) -> str:
    """Read session status from MD file."""
    if not path.exists():
        return "not_found"
    content = path.read_text()
    match = re.search(r'^status:\s*(\w+)', content, re.MULTILINE)
    return match.group(1) if match else "unknown"


def _read_pending_command(path: Path) -> Optional[Dict[str, Any]]:
    """Read the last pending command (no response yet)."""
    if not path.exists():
        return None
    content = path.read_text()
    
    # Find last command block without a response
    # Pattern: ### CMD: id\naction: ...\n(no RESPONSE yet)
    pattern = r'### CMD: (\w+)\naction: (\w+)(?:\nargs: (.+?))?(?=\n###|\n## |$)'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    if not matches:
        return None
    
    last = matches[-1]
    cmd_id = last.group(1)
    
    # Check if this command has a response
    response_pattern = f'### RESP: {cmd_id}'
    if response_pattern in content:
        return None  # Already responded
    
    return {
        "id": cmd_id,
        "action": last.group(2),
        "args": last.group(3).strip() if last.group(3) else ""
    }


def _append_response(path: Path, cmd_id: str, result: str):
    """Append response to session MD."""
    with open(path, "a") as f:
        f.write(f"\n### RESP: {cmd_id}\n{result}\n")


class SimpleSession:
    """Recording session with MD-only storage."""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self.recorder: Optional[DemoRecorder] = None
        self.t0: float = 0
        self.markers: Dict[str, float] = {}
        self.md_path = _session_md_path(config.run_id)
    
    def start(self):
        """Start browser and recording."""
        self.md_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize session.md
        with open(self.md_path, "w") as f:
            f.write(f"# Session: {self.config.run_id}\n\n")
            f.write(f"status: running\n")
            f.write(f"pid: {os.getpid()}\n")
            f.write(f"started: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"url: {self.config.url}\n\n")
            f.write("## Log\n\n")
        
        # Start recording
        self.recorder = DemoRecorder()
        self.recorder.start_recording(
            headless=self.config.headless,
            incognito=True,
            cookies=self.config.auth_cookies,
            video_prefix=self.config.run_id,
            use_prefix_as_run_id=True,
        )
        self.t0 = time.time()
        self.markers["t_start"] = 0.0
        
        if self.config.url:
            self.recorder.page.goto(self.config.url, timeout=60000)
            self.recorder.page.wait_for_timeout(1500)
            self.markers["t_page_loaded"] = time.time() - self.t0
        
        return "OK\nrecording started"
    
    def do_action(self, action: str, args: str = "") -> str:
        """Execute action, return plain text result."""
        if not self.recorder:
            return "ERROR: session not started"
        
        page = self.recorder.page
        ts = datetime.utcnow().strftime("%H:%M:%S")
        
        try:
            if action == "snapshot":
                text = page.inner_text("body")[:600] if page.query_selector("body") else ""
                elements = []
                for btn in page.query_selector_all("button")[:8]:
                    try:
                        t = btn.inner_text().strip()[:30]
                        if t:
                            elements.append(f"  button: {t}")
                    except:
                        pass
                for inp in page.query_selector_all("input, textarea")[:4]:
                    try:
                        label = inp.get_attribute("placeholder") or inp.get_attribute("aria-label") or "input"
                        elements.append(f"  input: {label[:30]}")
                    except:
                        pass
                
                result = f"OK at {ts}\n"
                result += f"url: {page.url}\n"
                result += f"title: {page.title()}\n"
                if elements:
                    result += "elements:\n" + "\n".join(elements) + "\n"
                result += f"text: {text[:400]}..."
                return result
            
            elif action == "click":
                page.click(args, timeout=10000)
                return f"OK at {ts}"
            
            elif action == "type":
                parts = args.split(" ", 1)
                selector = parts[0]
                text = parts[1] if len(parts) > 1 else ""
                page.type(selector, text, delay=45)
                return f"OK at {ts}"
            
            elif action == "fill":
                parts = args.split(" ", 1)
                selector = parts[0]
                text = parts[1] if len(parts) > 1 else ""
                page.fill(selector, text)
                return f"OK at {ts}"
            
            elif action == "press":
                page.keyboard.press(args or "Enter")
                return f"OK at {ts}"
            
            elif action == "wait":
                secs = float(args) if args else 1
                page.wait_for_timeout(int(secs * 1000))
                return f"OK waited {secs}s"
            
            elif action == "scroll":
                amount = int(args) if args else 500
                page.mouse.wheel(0, amount)
                return f"OK scrolled {amount}"
            
            elif action == "marker":
                name = args or f"t_{len(self.markers)}"
                t = time.time() - self.t0
                self.markers[name] = t
                return f"OK marker {name} at {t:.2f}s"
            
            else:
                return f"ERROR: unknown action: {action}"
        
        except Exception as e:
            return f"ERROR: {e}"
    
    def stop(self) -> str:
        """Stop recording, finalize session.md."""
        if not self.recorder:
            return "ERROR: not started"
        
        self.markers["t_end"] = time.time() - self.t0
        self.recorder.stop_recording()
        
        # Update session.md with final status and markers
        content = self.md_path.read_text()
        content = content.replace("status: running", "status: stopped")
        
        # Add markers section
        markers_md = "\n## Markers\n\n| Marker | Time |\n|--------|------|\n"
        for name, t in sorted(self.markers.items(), key=lambda x: x[1]):
            markers_md += f"| {name} | {t:.2f}s |\n"
        
        content += markers_md
        self.md_path.write_text(content)
        
        video = self.recorder.current_video_path
        duration = self.markers["t_end"]
        
        result = f"OK stopped\n"
        result += f"video: {video}\n"
        result += f"session: {self.md_path}\n"
        result += f"duration: {duration:.1f}s\n"
        result += "markers:\n"
        for name, t in sorted(self.markers.items(), key=lambda x: x[1]):
            result += f"  {name}: {t:.2f}s\n"
        
        return result


def run_session(config: SessionConfig) -> Dict[str, Any]:
    """Run session, reading commands from session.md, writing responses there."""
    session = SimpleSession(config)
    start_result = session.start()
    print(start_result, flush=True)
    
    md_path = session.md_path
    final_result = None
    
    while True:
        cmd = _read_pending_command(md_path)
        if cmd:
            action = cmd["action"]
            args = cmd["args"]
            
            if action == "stop":
                result = session.stop()
                _append_response(md_path, cmd["id"], result)
                print(result, flush=True)
                final_result = result
                break
            else:
                result = session.do_action(action, args)
                _append_response(md_path, cmd["id"], result)
                print(result, flush=True)
        else:
            time.sleep(0.2)
    
    # Return dict for CLI output
    if final_result and "video:" in final_result:
        lines = final_result.split("\n")
        video = next((l.split(": ", 1)[1] for l in lines if l.startswith("video:")), None)
        duration = next((l.split(": ", 1)[1] for l in lines if l.startswith("duration:")), None)
        return {
            "success": True,
            "video": video,
            "duration": duration,
            "session_file": str(md_path),
        }
    return {"success": True, "session_file": str(md_path)}


def send_command(run_id: str, action: str, args: str = "", timeout: int = 30) -> str:
    """Send command to session by appending to session.md.
    
    Args:
        run_id: Session run ID
        action: Action type (click, type, wait, etc.)
        args: Action arguments
        timeout: Response timeout in seconds (default 30, use higher for long AI operations)
    """
    md_path = _session_md_path(run_id)
    if not md_path.exists():
        return "ERROR: session not found"
    
    if _read_session_status(md_path) != "running":
        return "ERROR: session not running"
    
    cmd_id = uuid.uuid4().hex[:8]
    
    with open(md_path, "a") as f:
        f.write(f"\n### CMD: {cmd_id}\n")
        f.write(f"action: {action}\n")
        if args:
            f.write(f"args: {args}\n")
    
    # Wait for response
    start = time.time()
    while time.time() - start < timeout:
        content = md_path.read_text()
        match = re.search(f'### RESP: {cmd_id}\n(.+?)(?=\n### |$)', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        time.sleep(0.2)
    
    return "ERROR: timeout waiting for response"
