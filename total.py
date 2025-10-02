import os
import httpx
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Config
load_dotenv()
PLANNING_CENTER_CHECKINS_BASE_URL = "https://api.planningcenteronline.com/check-ins/v2"
CLIENT_ID = os.getenv("PLANNING_CENTER_CLIENT_ID", "demo_client_id")
SECRET = os.getenv("PLANNING_CENTER_SECRET", "demo_secret")
EVENT_ID = "701347"  # Change as appropriate

SERVICES = [
    'EH 10:15am',
    'EH 12:15pm',
    'EH 8:15am',
    'EW 11:00am',
    'EW 9:00am',
]

def get_event_period_id(event_id, date_str):
    url = f"{PLANNING_CENTER_CHECKINS_BASE_URL}/events/{event_id}/event_periods"
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    start = dt.date().isoformat()
    end = (dt + timedelta(days=1)).date().isoformat()
    params = {
        "where[starts_at][gte]": start,
        "where[starts_at][lt]": end,
        "order": "starts_at",
        "per_page": 5
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, auth=(CLIENT_ID, SECRET), params=params, headers={"Accept": "application/vnd.api+json"})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return data[0]["id"]
        return None

def fetch_event_times_with_headcounts(event_id, period_id):
    url = f"{PLANNING_CENTER_CHECKINS_BASE_URL}/events/{event_id}/event_periods/{period_id}/event_times"
    params = {
        "per_page": 100,
        "include": "headcounts,headcounts.attendance_type"
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, auth=(CLIENT_ID, SECRET), params=params, headers={"Accept": "application/vnd.api+json"})
        resp.raise_for_status()
        return resp.json()

def main():
    import sys, json
    # Step 1: Enter date
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        date = input("Enter date (YYYY-MM-DD): ").strip()
    print(f"[Step 1] Date Selected: {date}\n")

    # Step 2: Get event period ID for selected date
    period_id = get_event_period_id(EVENT_ID, date)
    print(f"[Step 2] Event Period ID for Date: {period_id}\n")
    if period_id is None:
        print("No event period found for this date!")
        return

    # Step 3: Fetch all event_times for the event_period (with included headcounts & attendance_types)
    response = fetch_event_times_with_headcounts(EVENT_ID, period_id)
    event_times = response.get("data", [])
    included = response.get("included", [])
    print(f"[Step 3] Event Times and Included Objects Fetched\nEvent Times: {len(event_times)}\nIncluded: {len(included)}\n")

    # Step 4: Build mapping for attendance types
    attendance_types = {item["id"]: item["attributes"]["name"]
                        for item in included if item["type"] == "AttendanceType"}
    headcounts = [item for item in included if item["type"] == "Headcount"]

    # Step 5: For each service, find event_time(s) and headcounts matching that attendance type
    counted_by_name = {}
    grand_total = 0
    print("[Step 4] Per-Service Breakdown [debug]:")
    for service_name in SERVICES:
        max_total = 0
        for hc in headcounts:
            relationships = hc.get("relationships", {})
            atid = None
            if "attendance_type" in relationships and relationships["attendance_type"]["data"]:
                atid = relationships["attendance_type"]["data"]["id"]
            att_name = attendance_types.get(str(atid), None)
            total = hc.get("attributes", {}).get("total", 0)
            if att_name == service_name and total > max_total:
                max_total = total
        counted_by_name[service_name] = max_total
        grand_total += max_total
        print(f"  {service_name:<12}: {max_total}")
    print(f"{'GRAND TOTAL':<12}: {grand_total}")

if __name__ == "__main__":
    main()
