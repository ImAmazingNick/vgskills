"""
Cost tracking and estimation for vg CLI.

Tracks API usage costs for ElevenLabs TTS and FAL talking heads.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent
COST_LOG_FILE = PROJECT_ROOT / "cost_tracking.json"

# Cost rates (per unit)
COST_RATES = {
    "elevenlabs_tts": {
        "rate_per_character": 0.00015,  # ~$15 per 100k characters
        "currency": "USD"
    },
    "fal_talking_head": {
        "rate_per_generation": 0.05,  # ~$0.05 per generation (estimate)
        "currency": "USD"
    }
}

def load_cost_log() -> dict:
    """Load cost tracking data."""
    if not COST_LOG_FILE.exists():
        return {"entries": [], "total_cost": 0.0, "currency": "USD"}

    try:
        return json.loads(COST_LOG_FILE.read_text())
    except Exception:
        return {"entries": [], "total_cost": 0.0, "currency": "USD"}

def save_cost_log(data: dict):
    """Save cost tracking data."""
    COST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    COST_LOG_FILE.write_text(json.dumps(data, indent=2, default=str))

def estimate_tts_cost(text: str, voice_id: str = "alloy") -> dict:
    """
    Estimate cost for TTS generation.
    """
    rate_info = COST_RATES["elevenlabs_tts"]
    character_count = len(text.strip())

    estimated_cost = character_count * rate_info["rate_per_character"]

    return {
        "service": "elevenlabs_tts",
        "estimated_cost": round(estimated_cost, 4),
        "currency": rate_info["currency"],
        "characters": character_count,
        "voice_id": voice_id,
        "rate_per_character": rate_info["rate_per_character"]
    }

def estimate_talking_head_cost(model: str = "omnihuman") -> dict:
    """
    Estimate cost for talking head generation.
    """
    rate_info = COST_RATES["fal_talking_head"]

    return {
        "service": "fal_talking_head",
        "estimated_cost": rate_info["rate_per_generation"],
        "currency": rate_info["currency"],
        "model": model,
        "rate_per_generation": rate_info["rate_per_generation"]
    }

def log_cost_entry(service: str, cost: float, metadata: dict = None):
    """
    Log a cost entry.
    """
    cost_data = load_cost_log()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "cost": cost,
        "currency": COST_RATES.get(service, {}).get("currency", "USD"),
        **(metadata or {})
    }

    cost_data["entries"].append(entry)
    cost_data["total_cost"] = round(cost_data.get("total_cost", 0.0) + cost, 4)

    save_cost_log(cost_data)

def get_cost_history(days: int = 7) -> dict:
    """
    Get cost history for the specified period.
    """
    cost_data = load_cost_log()
    entries = cost_data.get("entries", [])

    # Filter by date
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_entries = [
        entry for entry in entries
        if datetime.fromisoformat(entry["timestamp"]) > cutoff_date
    ]

    # Summarize by service
    service_totals = {}
    total_cost = 0.0

    for entry in recent_entries:
        service = entry["service"]
        cost = entry["cost"]
        service_totals[service] = service_totals.get(service, 0.0) + cost
        total_cost += cost

    return {
        "period_days": days,
        "total_cost": round(total_cost, 4),
        "currency": cost_data.get("currency", "USD"),
        "by_service": {k: round(v, 4) for k, v in service_totals.items()},
        "entry_count": len(recent_entries),
        "entries": recent_entries[-10:]  # Last 10 entries
    }

def get_cost_summary() -> dict:
    """
    Get overall cost summary.
    """
    cost_data = load_cost_log()
    entries = cost_data.get("entries", [])

    # Summarize by service
    service_totals = {}
    total_cost = cost_data.get("total_cost", 0.0)

    for entry in entries:
        service = entry["service"]
        cost = entry["cost"]
        service_totals[service] = service_totals.get(service, 0.0) + cost

    return {
        "total_cost": round(total_cost, 4),
        "currency": cost_data.get("currency", "USD"),
        "by_service": {k: round(v, 4) for k, v in service_totals.items()},
        "total_entries": len(entries),
        "first_entry": entries[0]["timestamp"] if entries else None,
        "last_entry": entries[-1]["timestamp"] if entries else None
    }

def check_budget_limit(budget_limit: float) -> dict:
    """
    Check if current spending is within budget.
    """
    summary = get_cost_summary()
    total_cost = summary["total_cost"]

    return {
        "current_spending": total_cost,
        "budget_limit": budget_limit,
        "remaining_budget": max(0, budget_limit - total_cost),
        "within_budget": total_cost <= budget_limit,
        "usage_percent": round((total_cost / budget_limit) * 100, 1) if budget_limit > 0 else 0
    }