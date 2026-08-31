import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from history_store import (
    get_event_page,
    history_summary,
    latest_event,
    recent_events,
    search_events,
    sync_journals,
)

DEFAULT_ELITE_DIR = Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous"
ELITE_DIR = Path(os.environ.get("ELITE_JOURNAL_DIR", str(DEFAULT_ELITE_DIR))).expanduser()

mcp = FastMCP("Elite Dangerous Full Context", stateless_http=True, json_response=True)


def read_json_file(name):
    path = ELITE_DIR / name
    if not path.exists() or not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_live_json():
    try:
        return sorted(p.name for p in ELITE_DIR.glob("*.json") if p.is_file())
    except Exception:
        return []


def build_current_state():
    sync_journals()
    loadout = latest_event("Loadout")
    location = latest_event("Location") or latest_event("FSDJump") or latest_event("CarrierJump")
    status = read_json_file("Status.json")
    navroute = read_json_file("NavRoute.json")
    events = recent_events(250)

    return {
        "location_event": location,
        "loadout": loadout,
        "status": status,
        "navroute": navroute,
        "history_summary": history_summary(),
        "recent_events": events,
        "live_json_files": list_live_json(),
    }


@mcp.tool()
def get_elite_state() -> dict:
    """Get rich current Elite Dangerous context: current location/loadout, live files, recent events, and history summary."""
    return build_current_state()


@mcp.tool()
def get_full_loadout() -> dict:
    """Get the most recent complete Loadout journal event, including modules and engineering."""
    return latest_event("Loadout") or {}


@mcp.tool()
def get_navroute() -> dict:
    """Get the currently plotted Elite Dangerous route."""
    return read_json_file("NavRoute.json") or {}


@mcp.tool()
def get_status() -> dict:
    """Get the latest Status.json data."""
    return read_json_file("Status.json") or {}


@mcp.tool()
def list_elite_live_files() -> list:
    """List every current JSON state file exposed by Elite Dangerous in the journal directory."""
    return list_live_json()


@mcp.tool()
def get_elite_live_file(filename: str) -> dict:
    """Read any Elite Dangerous JSON state file by filename."""
    if not filename.lower().endswith(".json"):
        filename += ".json"
    safe = Path(filename).name
    value = read_json_file(safe)
    return {"filename": safe, "data": value}


@mcp.tool()
def get_recent_events(count: int = 250) -> list:
    """Get recent raw journal events. Timestamps and all original journal fields are preserved."""
    return recent_events(max(1, min(count, 5000)))


@mcp.tool()
def search_journal(
    query: str = "",
    event: str = "",
    start_time: str = "",
    end_time: str = "",
    limit: int = 200,
) -> list:
    """Search ALL indexed current and historical Elite journals."""
    return search_events(query, event, start_time, end_time, limit)


@mcp.tool()
def get_latest_journal_event(event: str) -> dict:
    """Get the newest historical event of an exact Elite journal event type."""
    return latest_event(event) or {}


@mcp.tool()
def get_history_summary() -> dict:
    """Get statistics about the complete local journal-history index."""
    return history_summary()


@mcp.tool()
def get_raw_history_page(before_id: int = 0, limit: int = 500) -> dict:
    """Page through every raw journal event, newest first."""
    return get_event_page(None if before_id <= 0 else before_id, limit)


if __name__ == "__main__":
    sync_journals()
    mcp.run(transport="streamable-http")
