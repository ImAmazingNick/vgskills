"""
Authentication helpers for vg recording commands.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Import from core utils to avoid circular import with vg_commands.request
from vg_core_utils import parse_request_file


def _resolve_env_value(value: str) -> Optional[str]:
    if not value:
        return value
    # ${VAR} substitution
    def repl(match):
        env_key = match.group(1)
        return os.getenv(env_key, "")
    value = re.sub(r"\$\{(\w+)\}", repl, value)

    # If value mentions environment variable `VAR`
    env_match = re.search(r"`(\w+)`", value)
    if "environment variable" in value.lower() and env_match:
        return os.getenv(env_match.group(1))

    return value


def _normalize_cookie(cookie: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": cookie.get("name"),
        "value": cookie.get("value"),
        "domain": cookie.get("domain"),
        "path": cookie.get("path", "/"),
        "secure": bool(cookie.get("secure", True)),
        "httpOnly": bool(cookie.get("httpOnly", False)),
    }


def _auth_from_request_data(request_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, str], Optional[str]]:
    auth = request_data.get("authentication", {}) or {}
    cookies: List[Dict[str, Any]] = []
    headers: Dict[str, str] = {}

    auth_type = (auth.get("type") or "").strip().lower()
    cookie_name = auth.get("cookie_name")
    cookie_value = auth.get("cookie_value")
    cookie_domain = auth.get("cookie_domain")
    cookie_path = auth.get("cookie_path") or "/"
    cookie_secure = auth.get("cookie_secure", True)
    cookie_http_only = auth.get("cookie_http_only", False)

    header_name = auth.get("header_name")
    header_value = auth.get("header_value")

    if auth_type in ("cookie", "") and cookie_name and cookie_value:
        resolved_value = _resolve_env_value(cookie_value)
        if resolved_value is None:
            return [], {}, "Missing environment variable for cookie value"
        cookies.append(_normalize_cookie({
            "name": cookie_name,
            "value": resolved_value,
            "domain": cookie_domain,
            "path": cookie_path,
            "secure": cookie_secure,
            "httpOnly": cookie_http_only,
        }))
    if auth_type in ("header", "headers") and header_name and header_value:
        resolved_value = _resolve_env_value(header_value)
        if resolved_value is None:
            return [], {}, "Missing environment variable for header value"
        headers[header_name] = resolved_value

    # Allow both cookies and headers if present
    if cookie_name and cookie_value and not cookies:
        resolved_value = _resolve_env_value(cookie_value)
        if resolved_value is None:
            return [], {}, "Missing environment variable for cookie value"
        cookies.append(_normalize_cookie({
            "name": cookie_name,
            "value": resolved_value,
            "domain": cookie_domain,
            "path": cookie_path,
            "secure": cookie_secure,
            "httpOnly": cookie_http_only,
        }))
    if header_name and header_value and not headers:
        resolved_value = _resolve_env_value(header_value)
        if resolved_value is None:
            return [], {}, "Missing environment variable for header value"
        headers[header_name] = resolved_value

    return cookies, headers, None


def load_auth_config(auth_path: Optional[str]) -> Tuple[List[Dict[str, Any]], Dict[str, str], Optional[str]]:
    if not auth_path:
        return [], {}, None
    path = Path(auth_path)
    if not path.exists():
        return [], {}, f"Auth config file not found: {auth_path}"

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        cookies = [_normalize_cookie(c) for c in data.get("cookies", [])]
        headers = data.get("headers", {}) or {}
        return cookies, headers, None

    if path.suffix.lower() in (".md", ".markdown"):
        request_data = parse_request_file(str(path))
        return _auth_from_request_data(request_data)

    return [], {}, f"Unsupported auth config format: {path.suffix}"


def load_auth_from_request(request_path: Optional[str]) -> Tuple[List[Dict[str, Any]], Dict[str, str], Optional[str]]:
    if not request_path:
        return [], {}, None
    from pathlib import Path
    request_data = parse_request_file(Path(request_path))
    return _auth_from_request_data(request_data)
