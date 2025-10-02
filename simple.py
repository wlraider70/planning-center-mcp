#!/usr/bin/env python3
"""
event_details.py

Return ALL details for a single Check-Ins EVENT (hard-coded: 701347) for a given DATE (only variable).

- Credentials come from environment or .env:
    PLANNING_CENTER_CLIENT_ID
    PLANNING_CENTER_SECRET
- Usage:
    python event_details.py --date 2025-09-30
    # (Date is optional; defaults to today's date in UTC)

Output: a single JSON object printed to stdout containing:
  {
    "event": {...},
    "date": "YYYY-MM-DD",
    "event_period": {...},
    "event_times": [
      { "id": "...", "attributes": {...}, "headcounts": [ {...}, ... ] },
      ...
    ],
    "totals": {
      "by_service_time": [ {"event_time_id": "...", "starts_at": "...", "total": N}, ... ],
      "by_attendance_type": [ {"attendance_type_id": "...", "name": "...", "total": N}, ... ],
      "TOTAL ATTENDANCE": N
    }
  }

Notes:
- We scope by related endpoints, which is the recommended way to filter Check-Ins by event/period/time
  and include related data efficiently.
"""

import os
import json
import time
import base64
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional

# -------------------------
# Settings (ONLY VARIABLE IS DATE; Event is fixed)
# -------------------------
EVENT_ID = "701347"  # hard-coded event id per request
BASE_URL = "https://api.planningcenteronline.com/check-ins/v2/"

# -------------------------
# Minimal .env loader (no external dependency)
# -------------------------
def _load_dotenv_if_present(path: str = ".env") -> None:
    try:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

_load_dotenv_if_present()

CLIENT_ID = os.environ.get("PLANNING_CENTER_CLIENT_ID")
SECRET    = os.environ.get("PLANNING_CENTER_SECRET")

if not CLIENT_ID or not SECRET:
    raise RuntimeError(
        "Missing credentials. Set PLANNING_CENTER_CLIENT_ID and PLANNING_CENTER_SECRET "
        "in your environment or in a .env file."
    )

def _request(endpoint: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Basic GET with Basic Auth, pagination helper uses links.next in callers."""
    auth_string = f"{CLIENT_ID}:{SECRET}"
    headers = {
        "Authorization": f"Basic {base64.b64encode(auth_string.encode()).decode()}",
        "Accept": "application/json",
    }
    url = endpoint if endpoint.startswith("http") else BASE_URL + endpoint.lstrip("/")
    retries = 3
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, params=params)
            # Debug lines; comment out if you want quieter output
            print(f"Request URL: {resp.url}")
            print(f"Response status code: {resp.status_code}")

            if resp.status_code == 429:
                print("Rate limit hit. Sleeping 10s...")
                time.sleep(10)
                continue

            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2)
    raise RuntimeError("Unreachable")

def fetch_event(event_id: str) -> Dict[str, Any]:
    return _request(f"/events/{event_id}")

def fetch_event_period_for_date(event_id: str, date_iso: str) -> Optional[Dict[str, Any]]:
    """Find the event_period (session) for the given date using [gte, lt) range."""
    dt = datetime.strptime(date_iso, "%Y-%m-%d").date()
    next_dt = dt + timedelta(days=1)
    params = {
        "where[starts_at][gte]": dt.isoformat(),
        "where[starts_at][lt]":  next_dt.isoformat(),
        "order": "starts_at",
        "per_page": 100,
    }
    data = _request(f"/events/{event_id}/event_periods", params)
    periods = data.get("data", [])
    if not periods:
        return None
    # If multiple for the same date, pick the first
    return periods[0]

def fetch_event_times_with_headcounts(event_id: str, period_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch event_times for a given event_period and include headcounts + attendance_type.
    This keeps calls scoped to the single event+session.
    """
    params = {
        "per_page": 100,
        "include": "headcounts,headcounts.attendance_type",
    }
    all_times: List[Dict[str, Any]] = []
    included: List[Dict[str, Any]] = []
    url = f"/events/{event_id}/event_periods/{period_id}/event_times"

    while url:
        page = _request(url, params)
        all_times.extend(page.get("data", []))
        if "included" in page:
            included.extend(page["included"])
        url = page.get("links", {}).get("next", "")
        params = {}  # next is fully-qualified

    return all_times, included

def build_output(event_id: str, date_iso: str) -> Dict[str, Any]:
    # 1) Event
    event_resp = fetch_event(event_id)
    event_obj = event_resp.get("data", {})

    # 2) Event period for date
    period = fetch_event_period_for_date(event_id, date_iso)
    if not period:
        return {
            "event": event_obj,
            "date": date_iso,
            "error": f"No event_period (session) found for {date_iso}."
        }

    period_id = period["id"]

    # 3) Event times + headcounts (+ attendance_type via include)
    event_times, included = fetch_event_times_with_headcounts(event_id, period_id)

    # Index attendance types
    attendance_types: Dict[str, Dict[str, Any]] = {
        item["id"]: item.get("attributes", {}) or {}
        for item in included
        if item.get("type") == "AttendanceType"
    }

    # Group headcounts by event_time
    headcounts_by_event_time: Dict[str, List[Dict[str, Any]]] = {}
    headcounts_all: List[Dict[str, Any]] = []

    for inc in included:
        if inc.get("type") != "Headcount":
            continue
        attrs = inc.get("attributes", {}) or {}
        rels  = inc.get("relationships", {}) or {}
        et_id = ((rels.get("event_time", {}) or {}).get("data", {}) or {}).get("id")
        at_id = ((rels.get("attendance_type", {}) or {}).get("data", {}) or {}).get("id")
        at_name = attendance_types.get(at_id, {}).get("name", "") if at_id else ""

        hc_obj = {
            "id": inc.get("id"),
            "total": attrs.get("total", 0),
            "attendance_type_id": at_id,
            "attendance_type_name": at_name,
            "event_time_id": et_id
        }
        headcounts_all.append(hc_obj)
        if et_id:
            headcounts_by_event_time.setdefault(et_id, []).append(hc_obj)

    # Attach headcounts to each event_time record
    event_times_full: List[Dict[str, Any]] = []
    for et in event_times:
        et_id = et.get("id")
        et_attrs = et.get("attributes", {}) or {}
        event_times_full.append({
            "id": et_id,
            "attributes": et_attrs,
            "headcounts": headcounts_by_event_time.get(et_id, [])
        })

    # Build totals
    totals_by_service_time: List[Dict[str, Any]] = []
    for et in event_times_full:
        starts_at = (et.get("attributes", {}) or {}).get("starts_at", "")
        subtotal = sum(hc["total"] for hc in et["headcounts"])
        totals_by_service_time.append({
            "event_time_id": et["id"],
            "starts_at": starts_at,
            "total": subtotal
        })

    # By attendance type
    by_attendance: Dict[str, int] = {}
    for hc in headcounts_all:
        key = hc.get("attendance_type_id") or "unknown"
        by_attendance[key] = by_attendance.get(key, 0) + (hc.get("total", 0) or 0)

    totals_by_attendance_type: List[Dict[str, Any]] = []
    for at_id, tot in by_attendance.items():
        name = attendance_types.get(at_id, {}).get("name", "") if at_id != "unknown" else ""
        totals_by_attendance_type.append({
            "attendance_type_id": at_id if at_id != "unknown" else None,
            "name": name,
            "total": tot
        })

    grand_total = sum(item["total"] for item in headcounts_all)

    return {
        "event": event_obj,
        "date": date_iso,
        "event_period": period,
        "event_times": event_times_full,
        "totals": {
            "by_service_time": totals_by_service_time,
            "by_attendance_type": totals_by_attendance_type,
            "TOTAL ATTENDANCE": grand_total
        }
    }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Return ALL details for event 701347 for a given date.")
    parser.add_argument(
        "--date",
        help="Session date (YYYY-MM-DD). Defaults to today's date (UTC).",
        default=datetime.now(timezone.utc).date().isoformat(),
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args()

    result = build_output(EVENT_ID, args.date)
    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=False))
    else:
        print(json.dumps(result))