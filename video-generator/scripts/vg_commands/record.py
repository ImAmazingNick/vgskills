"""
vg record commands

Record browser sessions with timeline markers.
"""

import argparse
import re
import os
from pathlib import Path

from vg_recording import RecordingConfig, record_demo
from vg_session_simple import SessionConfig, run_session, send_command, _session_md_path, _read_session_status
from vg_agent_browser import (
    AgentBrowserSession, 
    get_or_create_session as get_agent_session,
    remove_session as remove_agent_session,
    check_agent_browser_installed
)
from vg_auth import load_auth_config, load_auth_from_request
from vg_common import validate_env_for_command, get_file_info

def register(subparsers):
    """Register record commands."""
    record_parser = subparsers.add_parser('record', help='Record browser sessions and screenshots')
    record_parser.add_argument('--url', help='URL to record (not needed for screenshot)')
    record_parser.add_argument('--scenario', default='ai-agent',
                              choices=['ai-agent', 'simple-dashboard', 'custom', 'auto'],
                              help='Recording scenario (default: ai-agent)')
    record_parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    record_parser.add_argument('--session-cookie', help='Session cookie for authentication')
    record_parser.add_argument('--auth', help='Auth config file (.json or .md request)')
    record_parser.add_argument('--request', help='Request file (.md) with authentication and platform details')
    record_parser.add_argument('--run-id', help='Custom run ID (auto-generated if not provided)')
    record_parser.set_defaults(func=cmd_record)

    # vg record screenshot
    record_subparsers = record_parser.add_subparsers(dest='record_command')
    screenshot_parser = record_subparsers.add_parser('screenshot', help='Take screenshot of web page')
    screenshot_parser.add_argument('--url', required=True, help='URL to screenshot')
    screenshot_parser.add_argument('--output', '-o', required=True, help='Output screenshot path')
    screenshot_parser.add_argument('--selector', help='CSS selector to wait for before screenshot')
    screenshot_parser.add_argument('--full-page', action='store_true', help='Capture full page (default: viewport only)')
    screenshot_parser.add_argument('--session-cookie', help='Session cookie for authentication')
    screenshot_parser.add_argument('--auth', help='Auth config file (.json or .md request)')
    screenshot_parser.set_defaults(func=cmd_screenshot)

    # vg record session
    session_parser = record_subparsers.add_parser('session', help='Start/operate a live recording session')
    session_sub = session_parser.add_subparsers(dest='session_command', required=True)

    session_start = session_sub.add_parser('start', help='Start a live recording session')
    session_start.add_argument('--url', help='URL to record')
    session_start.add_argument('--run-id', help='Custom run ID (auto-generated if not provided)')
    session_start.add_argument('--headless', action='store_true', help='Run in headless mode')
    session_start.add_argument('--auth', help='Auth config file (.json or .md request)')
    session_start.add_argument('--request', help='Request file (.md) to load auth and URL')
    session_start.add_argument('--cookie', help='Session cookie in format NAME=VALUE (e.g., session_id=abc123)')
    session_start.add_argument('--cookie-domain', help='Cookie domain (e.g., .example.com). Auto-detected from URL if not provided.')
    session_start.add_argument('--demo-effects', action='store_true', help='Enable demo cursor effects')
    session_start.set_defaults(func=cmd_session_start)

    session_do = session_sub.add_parser('do', help='Send action to live session')
    session_do.add_argument('--run-id', required=True, help='Run ID of the session')
    session_do.add_argument('--action', required=True, help='Action type (click, type, fill, wait, snapshot, etc.)')
    session_do.add_argument('--selector', help='CSS selector for the action')
    session_do.add_argument('--value', help='Value for the action (text, url, etc.)')
    session_do.add_argument('--marker', help='Timeline marker to record')
    session_do.add_argument('--name', help='Name for screenshot or marker')
    session_do.add_argument('--delay-ms', type=int, help='Typing delay in ms')
    session_do.add_argument('--timeout-ms', type=int, help='Timeout in ms')
    session_do.add_argument('--wait-s', type=float, help='Wait time in seconds')
    session_do.add_argument('--full-page', action='store_true', help='Full page screenshot')
    session_do.add_argument('--include-screenshot', action='store_true', help='Include screenshot with snapshot (for AI visual understanding)')
    session_do.add_argument('--no-wait', action='store_true', help='Do not wait for response')
    session_do.add_argument('--response-timeout', type=int, default=30, help='Response timeout in seconds')
    session_do.set_defaults(func=cmd_session_do)

    session_stop = session_sub.add_parser('stop', help='Stop a live recording session')
    session_stop.add_argument('--run-id', required=True, help='Run ID of the session')
    session_stop.add_argument('--response-timeout', type=int, default=60, help='Response timeout in seconds')
    session_stop.set_defaults(func=cmd_session_stop)

    session_status = session_sub.add_parser('status', help='Get session status')
    session_status.add_argument('--run-id', required=True, help='Run ID of the session')
    session_status.set_defaults(func=cmd_session_status)

    # --- agent-browser session commands ---
    # vg record session agent-start
    agent_start = session_sub.add_parser('agent-start', 
        help='Start agent-browser recording session (ref-based element selection)')
    agent_start.add_argument('--url', help='URL to record')
    agent_start.add_argument('--run-id', help='Run ID (auto-generated if not provided)')
    agent_start.add_argument('--headed', action='store_true', help='Show browser window')
    agent_start.add_argument('--request', help='Request file to load auth and URL')
    agent_start.add_argument('--cookie', help='Cookie NAME=VALUE')
    agent_start.add_argument('--cookie-domain', help='Cookie domain (e.g., .example.com)')
    agent_start.set_defaults(func=cmd_agent_session_start)

    # vg record session agent-do
    agent_do = session_sub.add_parser('agent-do',
        help='Send action to agent-browser session')
    agent_do.add_argument('--run-id', required=True, help='Run ID of the session')
    agent_do.add_argument('--action', required=True,
        help='Action: snapshot, click, fill, type, press, wait, scroll, marker, screenshot')
    agent_do.add_argument('--ref', help='Element ref from snapshot (@e1, @e2...)')
    agent_do.add_argument('--selector', help='CSS selector (fallback if no ref)')
    agent_do.add_argument('--value', help='Value for action (text, key, marker name, etc.)')
    agent_do.add_argument('--delay-ms', type=int, default=45, help='Typing delay in ms')
    agent_do.add_argument('--wait-s', type=float, help='Wait time in seconds')
    agent_do.add_argument('--include-screenshot', '-i', action='store_true',
        help='Include screenshot with snapshot')
    agent_do.add_argument('--timeout', type=int, default=30, help='Command timeout in seconds')
    agent_do.set_defaults(func=cmd_agent_session_do)

    # vg record session agent-stop
    agent_stop = session_sub.add_parser('agent-stop',
        help='Stop agent-browser session and save recording')
    agent_stop.add_argument('--run-id', required=True, help='Run ID of the session')
    agent_stop.set_defaults(func=cmd_agent_session_stop)

    # vg record session agent-status
    agent_status = session_sub.add_parser('agent-status',
        help='Get agent-browser session status')
    agent_status.add_argument('--run-id', required=True, help='Run ID of the session')
    agent_status.set_defaults(func=cmd_agent_session_status)


def _extract_domain_from_url(url: str) -> str:
    """Extract domain from URL for cookie settings."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None
        parts = hostname.split('.')
        if len(parts) >= 2:
            return '.' + '.'.join(parts[-2:])
        return '.' + hostname
    except Exception:
        return None


def _resolve_auth_sources(auth_path, request_path, session_cookie, url=None):
    """Resolve authentication from various sources.
    
    Priority:
    1. auth_path - explicit auth config file
    2. request_path - request file with authentication section
    3. session_cookie - simple cookie value (requires URL for domain)
    
    Args:
        auth_path: Path to auth config file (.json or .md)
        request_path: Path to request file with authentication
        session_cookie: Simple session cookie value or "name=value"
        url: Target URL (used to extract domain for session_cookie)
    """
    cookies = []
    headers = {}
    
    if auth_path:
        cookies, headers, err = load_auth_config(auth_path)
        if err:
            return [], {}, err
    elif request_path:
        cookies, headers, err = load_auth_from_request(request_path)
        if err:
            return [], {}, err

    # Handle session_cookie if no cookies from auth config
    if session_cookie and not cookies:
        domain = _extract_domain_from_url(url) if url else None
        
        # Parse session_cookie - can be "name=value" or just "value"
        if '=' in session_cookie and not session_cookie.startswith('='):
            # Format: "name=value"
            parts = session_cookie.split('=', 1)
            cookie_name = parts[0].strip()
            cookie_value = parts[1].strip()
        else:
            # Format: just "value" - use generic name
            cookie_name = 'session'
            cookie_value = session_cookie
        
        cookies.append({
            "name": cookie_name,
            "value": cookie_value,
            "domain": domain,
            "path": "/",
            "secure": True,
            "httpOnly": False,
        })
        
        if not domain:
            print(f"   ⚠️  Cookie domain not set - provide URL or use auth config file")

    return cookies, headers, None

def cmd_record(args) -> dict:
    """Handle vg record command."""
    # Check if this is a subcommand
    if hasattr(args, 'record_command') and args.record_command:
        # This will be handled by the specific subcommand function
        return args.func(args)

    from datetime import datetime
    from project_paths import run_paths

    # If request file is provided, read authentication and URL from it
    auth_cookie = args.session_cookie
    actions = None
    if args.request:
        try:
            from vg_commands.request import parse_request_file
            request_data = parse_request_file(args.request)
            auth_info = request_data.get("authentication", {})
            actions = request_data.get("actions") or None
            scenario_prompts = request_data.get("scenario_prompts") or []
            voiceover_prompts = request_data.get("voiceover_prompts") or []
            success_criteria = request_data.get("success_criteria") or []

            if not args.url:
                req_url = request_data.get("platform", {}).get("url")
                if req_url:
                    args.url = req_url

            # Use authentication from request file if available
            if auth_info.get("cookie_name") and auth_info.get("cookie_value"):
                cookie_name = auth_info["cookie_name"]
                cookie_value = auth_info["cookie_value"]

                # If cookie value references environment variable, resolve it
                if "environment variable" in cookie_value.lower():
                    env_var_match = re.search(r'`(\w+)`', cookie_value)
                    if env_var_match:
                        env_var = env_var_match.group(1)
                        actual_value = os.getenv(env_var)
                        if actual_value:
                            auth_cookie = f"{cookie_name}={actual_value}"
                        else:
                            return {
                                "success": False,
                                "error": f"Environment variable {env_var} not set for authentication",
                                "code": "MISSING_AUTH",
                                "suggestion": f"Set {env_var} environment variable or provide --session-cookie directly"
                            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse request file: {e}",
                "code": "PARSE_ERROR"
            }

    auth_cookies, auth_headers, auth_error = _resolve_auth_sources(args.auth, args.request, args.session_cookie, url=args.url)
    if auth_error:
        return {
            "success": False,
            "error": auth_error,
            "code": "AUTH_ERROR"
        }

    # Generate run_id if not provided
    if not args.run_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.run_id = f"{args.scenario}_{timestamp}"

    # Create proper directory structure per plans
    run_paths_obj = run_paths(args.run_id)
    run_paths_obj.raw_dir.mkdir(parents=True, exist_ok=True)

    # Create configuration with proper output directory (use run_dir for consistency)
    prompts = scenario_prompts or voiceover_prompts
    scenario = "custom" if actions else ("auto" if prompts else args.scenario)
    config = RecordingConfig(
        url=args.url,
        scenario=scenario,
        headless=args.headless,
        session_cookie=auth_cookie,
        auth_cookies=auth_cookies or None,
        auth_headers=auth_headers or None,
        output_dir=run_paths_obj.run_dir,
        actions=actions,
        auto_prompts=prompts,
        run_id=args.run_id,
        validation_checks=success_criteria,
        prompts=prompts if scenario == "ai-agent" else None
    )

    # Execute recording
    result = record_demo(config)

    # Update result with proper paths
    if result.get("success"):
        result.update({
            "run_id": args.run_id,
            "run_dir": str(run_paths_obj.run_dir),
            "raw_video": str(run_paths_obj.raw_dir / f"{args.run_id}.webm"),
            "timeline": str(run_paths_obj.run_dir / "timeline.md"),
            "audio_dir": str(run_paths_obj.run_dir / "audio"),
            "video_dir": str(run_paths_obj.run_dir),
            "final_dir": str(run_paths_obj.run_dir)
        })

    return result

def cmd_screenshot(args) -> dict:
    """Handle vg record screenshot command."""
    try:
        from playwright.sync_api import sync_playwright

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cookies, headers, auth_error = _resolve_auth_sources(args.auth, None, args.session_cookie, url=args.url)
        if auth_error:
            return {
                "success": False,
                "error": auth_error,
                "code": "AUTH_ERROR"
            }

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()

            if headers:
                context.set_extra_http_headers(headers)
            if cookies:
                context.add_cookies(cookies)

            page = context.new_page()
            page.goto(args.url)

            # Wait for selector if specified
            if args.selector:
                page.wait_for_selector(args.selector)

            # Take screenshot
            screenshot_options = {'path': str(output_path)}
            if args.full_page:
                screenshot_options['full_page'] = True

            page.screenshot(**screenshot_options)

            browser.close()

        # Get file info
        file_info = get_file_info(output_path)

        return {
            "success": True,
            "screenshot": str(output_path),
            "size": file_info.get("size", 0),
            "url": args.url,
            "full_page": args.full_page,
            "selector": args.selector
        }

    except Exception as e:
        from vg_common import classify_error, get_suggestion
        error_code = classify_error(e)
        return {
            "success": False,
            "error": str(e),
            "code": error_code,
            "suggestion": get_suggestion(e)
        }


def cmd_session_start(args) -> dict:
    from datetime import datetime
    from vg_commands.request import parse_request_file

    url = args.url
    if args.request and not url:
        try:
            request_data = parse_request_file(args.request)
            url = request_data.get("platform", {}).get("url") or url
        except Exception:
            pass

    if not args.run_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.run_id = f"session_{timestamp}"

    # Handle direct --cookie argument
    direct_cookie = None
    if getattr(args, 'cookie', None):
        cookie_str = args.cookie
        if '=' in cookie_str:
            name, value = cookie_str.split('=', 1)
            domain = getattr(args, 'cookie_domain', None) or _extract_domain_from_url(url)
            direct_cookie = [{
                'name': name.strip(),
                'value': value.strip(),
                'domain': domain,
                'path': '/'
            }]

    cookies, headers, auth_error = _resolve_auth_sources(args.auth, args.request, None, url=url)
    if auth_error:
        return {
            "success": False,
            "error": auth_error,
            "code": "AUTH_ERROR"
        }

    # Merge direct cookie with auth cookies
    if direct_cookie:
        cookies = (cookies or []) + direct_cookie

    return run_session(
        config=SessionConfig(
            url=url,
            run_id=args.run_id,
            headless=args.headless,
            auth_cookies=cookies or None,
            auth_headers=headers or None,
        )
    )


def cmd_session_do(args) -> dict:
    # Build args string from command parameters
    action = args.action
    action_args = ""
    
    if action == "click" and args.selector:
        action_args = args.selector
    elif action == "type" and args.selector:
        action_args = f"{args.selector} {args.value or ''}"
    elif action == "fill" and args.selector:
        action_args = f"{args.selector} {args.value or ''}"
    elif action == "press":
        action_args = args.value or "Enter"
    elif action == "wait":
        action_args = str(args.wait_s or 1)
    elif action == "scroll":
        action_args = args.value or "500"
    elif action == "marker":
        action_args = args.value or args.marker or args.name or ""
    
    # Get timeout (default 30s, can be increased for long AI operations)
    timeout = getattr(args, 'response_timeout', 30)
    
    result = send_command(args.run_id, action, action_args, timeout=timeout)
    
    if result.startswith("ERROR"):
        return {"success": False, "error": result}
    return {"success": True, "result": result}


def cmd_session_stop(args) -> dict:
    result = send_command(args.run_id, "stop")
    
    if result.startswith("ERROR"):
        return {"success": False, "error": result}
    return {"success": True, "result": result}


def cmd_session_status(args) -> dict:
    md_path = _session_md_path(args.run_id)
    if not md_path.exists():
        return {"success": False, "error": "Session not found", "code": "SESSION_NOT_FOUND"}
    
    status = _read_session_status(md_path)
    return {"success": True, "status": status, "session_file": str(md_path)}


# --- agent-browser session command handlers ---

def cmd_agent_session_start(args) -> dict:
    """Start agent-browser recording session."""
    from datetime import datetime
    from project_paths import run_paths
    
    # Check agent-browser is installed
    install_check = check_agent_browser_installed()
    if not install_check.get("installed"):
        return {
            "success": False,
            "error": install_check.get("error", "agent-browser not installed"),
            "code": "NOT_INSTALLED",
            "suggestion": "Install with: npm install -g agent-browser"
        }
    
    # Get URL from args or request file
    url = args.url
    cookies = []
    
    if args.request and not url:
        try:
            from vg_commands.request import parse_request_file
            request_data = parse_request_file(args.request)
            url = request_data.get("platform", {}).get("url") or url
            
            # Load auth from request
            auth_cookies, _, auth_error = _resolve_auth_sources(None, args.request, None, url=url)
            if not auth_error and auth_cookies:
                cookies = auth_cookies
        except Exception as e:
            return {"success": False, "error": f"Failed to parse request: {e}", "code": "PARSE_ERROR"}
    
    if not url:
        return {
            "success": False,
            "error": "URL required. Provide --url or --request with URL",
            "code": "MISSING_URL"
        }
    
    # Generate run_id if not provided
    if not args.run_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.run_id = f"agent_{timestamp}"
    
    # Handle direct --cookie argument
    if getattr(args, 'cookie', None):
        cookie_str = args.cookie
        if '=' in cookie_str:
            name, value = cookie_str.split('=', 1)
            domain = getattr(args, 'cookie_domain', None) or _extract_domain_from_url(url)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': domain,
                'path': '/'
            })
    
    # Create run directory
    paths = run_paths(args.run_id)
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and configure session
    session = get_agent_session(args.run_id, paths.run_dir)
    
    # Open browser
    headed = getattr(args, 'headed', False)
    result = session.open(url, headed=headed)
    
    if not result.get("success"):
        return result
    
    # Set cookies if any
    if cookies:
        cookie_result = session.set_cookies(cookies)
        if not cookie_result.get("success"):
            return cookie_result
        # Reload page after setting cookies
        session._run_cmd("reload")
    
    # Start recording
    record_result = session.record_start()
    if not record_result.get("success"):
        return record_result
    
    # Add page loaded marker
    session.marker("t_page_loaded")
    
    return {
        "success": True,
        "run_id": args.run_id,
        "url": url,
        "run_dir": str(paths.run_dir),
        "driver": "agent-browser",
        "message": "Session started. Use 'vg record session agent-do --action snapshot' to see page state."
    }


def cmd_agent_session_do(args) -> dict:
    """Execute action in agent-browser session."""
    run_id = args.run_id
    action = args.action.lower()
    
    # Get session
    try:
        session = get_agent_session(run_id)
    except Exception:
        return {"success": False, "error": "Session not found", "code": "SESSION_NOT_FOUND"}
    
    # Determine target (ref or selector)
    target = args.ref or args.selector or ""
    value = args.value or ""
    
    try:
        if action == "snapshot":
            include_image = getattr(args, 'include_screenshot', False)
            result = session.snapshot(include_image=include_image)
            
            # Format refs for AI readability
            if result.get("success") and result.get("refs"):
                refs = result["refs"]
                # Limit to first 30 refs for readability
                ref_list = list(refs.items())[:30]
                formatted = "\n".join([f"  {ref}: {desc}" for ref, desc in ref_list])
                result["formatted_refs"] = formatted
                if len(refs) > 30:
                    result["note"] = f"Showing 30 of {len(refs)} elements. Use refs to interact."
            
            return result
        
        elif action == "click":
            if not target:
                return {"success": False, "error": "click requires --ref or --selector"}
            return session.click(target)
        
        elif action == "fill":
            if not target:
                return {"success": False, "error": "fill requires --ref or --selector"}
            return session.fill(target, value)
        
        elif action == "type":
            if not target:
                return {"success": False, "error": "type requires --ref or --selector"}
            delay = getattr(args, 'delay_ms', 45)
            return session.type(target, value, delay_ms=delay)
        
        elif action == "press":
            key = value or "Enter"
            return session.press(key)
        
        elif action == "wait":
            wait_s = getattr(args, 'wait_s', None) or (float(value) if value else 1.0)
            return session.wait(seconds=wait_s)
        
        elif action == "scroll":
            amount = int(value) if value else 500
            return session.scroll(amount=amount)
        
        elif action == "marker":
            marker_name = value or f"t_marker_{len(session.timeline_markers)}"
            return session.marker(marker_name)
        
        elif action == "screenshot":
            output_path = value if value else None
            return session.screenshot(output_path)
        
        elif action == "get-text":
            if not target:
                return {"success": False, "error": "get-text requires --ref or --selector"}
            return session.get_text(target)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "valid_actions": ["snapshot", "click", "fill", "type", "press", "wait", "scroll", "marker", "screenshot", "get-text"]
            }
    
    except Exception as e:
        return {"success": False, "error": str(e), "code": "ACTION_ERROR"}


def cmd_agent_session_stop(args) -> dict:
    """Stop agent-browser session and save recording."""
    run_id = args.run_id
    
    try:
        session = get_agent_session(run_id)
    except Exception:
        return {"success": False, "error": "Session not found", "code": "SESSION_NOT_FOUND"}
    
    # Stop recording
    result = session.record_stop()
    
    # Close browser
    session.close()
    
    # Clean up session
    remove_agent_session(run_id)
    
    if result.get("success"):
        result["markers"] = [
            {"name": m["name"], "time": f"{m['time']:.2f}s"} 
            for m in session.timeline_markers
        ]
    
    return result


def cmd_agent_session_status(args) -> dict:
    """Get agent-browser session status."""
    run_id = args.run_id
    
    try:
        session = get_agent_session(run_id)
        return session.get_status()
    except Exception:
        return {"success": False, "error": "Session not found", "code": "SESSION_NOT_FOUND"}