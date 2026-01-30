"""
vg utility commands

Utility operations (list, info, cleanup, status).
"""

import argparse
from vg_core_utils import validate_timeline_completeness, validate_request_file
from vg_utils import list_assets, get_asset_info, cleanup_assets, get_system_status, cache_clear, cache_status  # Import from the old vg_utils.py
from vg_cost import estimate_tts_cost, estimate_talking_head_cost, get_cost_history, get_cost_summary, check_budget_limit

def register(subparsers):
    """Register utility commands."""

    # vg list
    list_parser = subparsers.add_parser('list', help='List assets')
    list_parser.add_argument('--type', choices=['video', 'audio', 'timeline'], help='Asset type filter')
    list_parser.add_argument('--recent', type=int, help='Show N most recent')
    list_parser.set_defaults(func=cmd_list)

    # vg info
    info_parser = subparsers.add_parser('info', help='Get file information')
    info_parser.add_argument('--file', required=True, help='File path')
    info_parser.set_defaults(func=cmd_info)

    # vg cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup temporary files')
    cleanup_parser.add_argument('--older-than', type=int, help='Remove files older than N days')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # vg status
    status_parser = subparsers.add_parser('status', help='Show current session state')
    status_parser.set_defaults(func=cmd_status)

    # vg cache
    cache_parser = subparsers.add_parser('cache', help='Cache management')
    cache_sub = cache_parser.add_subparsers(dest='cache_command')

    # vg cache clear
    clear_parser = cache_sub.add_parser('clear', help='Clear cache entries')
    clear_parser.add_argument('--type', choices=['tts', 'talking_head'], help='Cache type to clear')
    clear_parser.add_argument('--older-than', type=int, help='Clear entries older than N hours')
    clear_parser.set_defaults(func=cmd_cache_clear)

    # vg cache status
    cache_status_parser = cache_sub.add_parser('status', help='Show cache status')
    cache_status_parser.set_defaults(func=cmd_cache_status)

    # vg cost
    cost_parser = subparsers.add_parser('cost', help='Cost tracking and estimation')
    cost_sub = cost_parser.add_subparsers(dest='cost_command')

    # vg cost estimate
    estimate_parser = cost_sub.add_parser('estimate', help='Estimate cost for operations')
    estimate_parser.add_argument('--tts-text', help='Text for TTS cost estimation')
    estimate_parser.add_argument('--tts-voice', default='alloy', help='Voice ID for TTS')
    estimate_parser.add_argument('--talking-head-model', choices=['omnihuman', 'sadtalker'], help='Model for talking head cost')
    estimate_parser.set_defaults(func=cmd_cost_estimate)

    # vg cost history
    history_parser = cost_sub.add_parser('history', help='Show cost history')
    history_parser.add_argument('--days', type=int, default=7, help='Days to look back')
    history_parser.set_defaults(func=cmd_cost_history)

    # vg cost summary
    summary_parser = cost_sub.add_parser('summary', help='Show cost summary')
    summary_parser.set_defaults(func=cmd_cost_summary)

    # vg cost budget
    budget_parser = cost_sub.add_parser('budget', help='Check budget status')
    budget_parser.add_argument('--limit', type=float, required=True, help='Budget limit in USD')
    budget_parser.set_defaults(func=cmd_cost_budget)

    # vg validate
    validate_parser = subparsers.add_parser('validate', help='Validate files and configurations')
    validate_sub = validate_parser.add_subparsers(dest='validate_command')

    # vg validate timeline
    timeline_parser = validate_sub.add_parser('timeline', help='Validate timeline completeness')
    timeline_parser.add_argument('--timeline', required=True, help='Timeline JSON file path')
    timeline_parser.add_argument('--required-markers', nargs='+', help='List of required marker names')
    timeline_parser.set_defaults(func=cmd_validate_timeline)

    # vg validate request
    request_parser = validate_sub.add_parser('request', help='Validate request file')
    request_parser.add_argument('--request', required=True, help='Request file path')
    request_parser.set_defaults(func=cmd_validate_request)

def cmd_list(args) -> dict:
    """Handle vg list command."""
    return list_assets(asset_type=args.type, recent_count=args.recent)

def cmd_info(args) -> dict:
    """Handle vg info command."""
    return get_asset_info(args.file)

def cmd_cleanup(args) -> dict:
    """Handle vg cleanup command."""
    return cleanup_assets(older_than_days=args.older_than, dry_run=args.dry_run)

def cmd_status(args) -> dict:
    """Handle vg status command."""
    return get_system_status()

def cmd_cache_clear(args) -> dict:
    """Handle vg cache clear command."""
    return cache_clear(cache_type=args.type, older_than_hours=args.older_than)

def cmd_cache_status(args) -> dict:
    """Handle vg cache status command."""
    return cache_status()

def cmd_cost_estimate(args) -> dict:
    """Handle vg cost estimate command."""
    estimates = {}

    if args.tts_text:
        estimates["tts"] = estimate_tts_cost(args.tts_text, args.tts_voice)

    if args.talking_head_model:
        estimates["talking_head"] = estimate_talking_head_cost(args.talking_head_model)

    if not estimates:
        return {
            "success": False,
            "error": "No estimation parameters provided",
            "code": "VALIDATION"
        }

    return {
        "success": True,
        "estimates": estimates
    }

def cmd_cost_history(args) -> dict:
    """Handle vg cost history command."""
    return get_cost_history(days=args.days)

def cmd_cost_summary(args) -> dict:
    """Handle vg cost summary command."""
    return get_cost_summary()

def cmd_cost_budget(args) -> dict:
    """Handle vg cost budget command."""
    return check_budget_limit(args.limit)

def cmd_validate_timeline(args) -> dict:
    """Handle vg validate timeline command."""
    from pathlib import Path

    timeline_path = Path(args.timeline)
    required_markers = args.required_markers or []

    result = validate_timeline_completeness(required_markers, timeline_path)
    result["command"] = "validate_timeline"

    return result

def cmd_validate_request(args) -> dict:
    """Handle vg validate request command."""
    from pathlib import Path

    request_path = Path(args.request)

    result = validate_request_file(request_path)
    result["command"] = "validate_request"

    return result