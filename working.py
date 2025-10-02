#!/usr/bin/env python3

import os
from datetime import datetime, timedelta
import asyncio
import time
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from typing import Any, Dict, List, Optional

# Added import for typing and tool improvement

# Load environment variables
load_dotenv()

# ---
# Updated: Get headcount titles by category for a specific date
async def get_total_attendance_by_category_for_date(httpx_client, base_url, token, category_name: str, date: str):
    # Query all headcounts for the given date
    url = f"{base_url}/headcounts?filter[created_at][eq]={date}"
    headers = {'Authorization': f'Bearer {token}'}
    resp = await httpx_client.get(url, headers=headers)
    data = resp.json()
    result = []
    for headcount in data.get('data', []):
        title = None
        # Adapt for your schema (PCO headcounts reference a category/type object)
        if 'relationships' in headcount and 'headcount_category' in headcount['relationships']:
            cat_obj = headcount['relationships']['headcount_category']
            if cat_obj and 'data' in cat_obj and 'id' in cat_obj['data']:
                title = cat_obj['data'].get('id')
        if not title and 'attributes' in headcount and 'name' in headcount['attributes']:
            title = headcount['attributes']['name']
        result.append({
            'id': headcount['id'],
            'total': headcount.get('total', 0),
            'title': title
        })
    # Filter only the headcounts whose title matches the requested category_name
    filtered = [x for x in result if x['title'] and category_name.upper() in x['title'].upper()]
    total = sum(x['total'] for x in filtered)
    return {'date': date, 'category': category_name, 'filtered_headcounts': filtered, 'total_attendance': total}

# Usage example for last Sunday:
# result = await get_total_attendance_by_category_for_date(client, BASE_URL, TOKEN, '*TOTAL ATTENDANCE', '2025-09-21')

# ---
# In your weekly attendance logic, call get_headcount_titles_for_week instead of just raw headcounts
# Then filter like: [h for h in headcounts if h['title'] and 'TOTAL ATTENDANCE' in h['title'].upper()]

# Uncomment in your tool logic for weekly attendance summary:
'''
async def get_attendance_this_week_with_titles(httpx_client, base_url, token, week_start, week_end):
    a = await get_headcount_titles_for_week(httpx_client, base_url, token, week_start, week_end)
    total = sum([x["total"] for x in a if x["title"] and "TOTAL ATTENDANCE" in x["title"].upper()])
    return {"week_start": week_start, "week_end": week_end, "total_attendance": total, "headcounts": a}
'''

# Rest of the existing code...
# Planning Center API configuration
PLANNING_CENTER_BASE_URL = "https://api.planningcenteronline.com/people/v2"
PLANNING_CENTER_CHECKINS_BASE_URL = "https://api.planningcenteronline.com/check-ins/v2"
CLIENT_ID = os.getenv("PLANNING_CENTER_CLIENT_ID", "demo_client_id")
SECRET = os.getenv("PLANNING_CENTER_SECRET", "demo_secret")

# Rate limiting
class RateLimiter:
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        now = time.time()
        # Remove requests older than time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        self.requests.append(time.time())

rate_limiter = RateLimiter()

# Initialize MCP server
mcp = FastMCP("Planning Center MCP Server")

def make_sync_request(endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3, base_url: str = None) -> Dict[str, Any]:
    """Make authenticated request to Planning Center API with rate limiting and retry logic"""
    if not rate_limiter.can_make_request():
        raise Exception("Rate limit exceeded. Planning Center allows 100 requests per minute.")
    
    rate_limiter.record_request()
    
    # Use provided base_url or default to People API
    api_base_url = base_url or PLANNING_CENTER_BASE_URL
    
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{api_base_url}{endpoint}",
                    auth=(CLIENT_ID, SECRET),
                    params=params or {},
                    headers={"Accept": "application/vnd.api+json"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            if attempt == max_retries - 1:
                raise Exception(f"Request timed out after {max_retries} attempts: {str(e)}")
            time.sleep(1 * (attempt + 1))  # Exponential backoff
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                if attempt == max_retries - 1:
                    raise Exception(f"Rate limited after {max_retries} attempts")
                time.sleep(2 * (attempt + 1))  # Longer wait for rate limits
            elif e.response.status_code >= 500:  # Server error
                if attempt == max_retries - 1:
                    raise Exception(f"Server error after {max_retries} attempts: {e.response.status_code}")
                time.sleep(1 * (attempt + 1))
            else:
                # Client error (4xx), don't retry
                raise Exception(f"Client error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Request failed after {max_retries} attempts: {str(e)}")
            time.sleep(1 * (attempt + 1))
    
    raise Exception(f"Request failed after {max_retries} attempts")

def extract_person_data(person_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and format person data from API response"""
    attributes = person_data.get("attributes", {})
    
    # Calculate age from birthdate if available
    age = None
    if attributes.get("birthdate"):
        try:
            birthdate = datetime.fromisoformat(attributes["birthdate"].replace("Z", "+00:00"))
            today = datetime.now()
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        except:
            pass
    
    return {
        "id": person_data["id"],
        "name": attributes.get("name", ""),
        "first_name": attributes.get("first_name", ""),
        "last_name": attributes.get("last_name", ""),
        "email": attributes.get("login_identifier"),
        "age": age,
        "gender": attributes.get("gender"),
        "membership": attributes.get("membership"),
        "background_check_approved": attributes.get("passed_background_check"),
        "birthdate": attributes.get("birthdate"),
        "anniversary": attributes.get("anniversary"),
        "status": attributes.get("status"),
        "medical_notes": attributes.get("medical_notes"),
        "directory_status": attributes.get("directory_status")
    }

@mcp.tool()
def get_person_phone_numbers(person_id: str) -> List[Dict[str, Any]]:
    """
    Get phone numbers for a specific person by their ID.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        List of phone numbers with details
    """
    try:
        response = make_sync_request(f"/people/{person_id}/phone_numbers")
        phone_numbers = []
        
        for phone_data in response.get("data", []):
            attributes = phone_data.get("attributes", {})
            phone_numbers.append({
                "id": phone_data["id"],
                "number": attributes.get("number"),
                "carrier": attributes.get("carrier"),
                "location": attributes.get("location"),
                "primary": attributes.get("primary", False),
                "created_at": attributes.get("created_at"),
                "updated_at": attributes.get("updated_at")
            })
        
        return phone_numbers
    except Exception as e:
        return [{"error": f"Failed to get phone numbers: {str(e)}"}]

@mcp.tool()
def get_person_addresses(person_id: str) -> List[Dict[str, Any]]:
    """
    Get addresses for a specific person by their ID.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        List of addresses with details
    """
    try:
        response = make_sync_request(f"/people/{person_id}/addresses")
        addresses = []
        
        for address_data in response.get("data", []):
            attributes = address_data.get("attributes", {})
            addresses.append({
                "id": address_data["id"],
                "street": attributes.get("street"),
                "city": attributes.get("city") or attributes.get("locality"),
                "state": attributes.get("state") or attributes.get("region"),
                "zip": attributes.get("zip") or attributes.get("postal_code"),
                "location": attributes.get("location"),
                "primary": attributes.get("primary", False),
                "created_at": attributes.get("created_at"),
                "updated_at": attributes.get("updated_at"),
                "raw_attributes": attributes
            })
        
        return addresses
    except Exception as e:
        return [{"error": f"Failed to get addresses: {str(e)}"}]

@mcp.tool()
def get_person_emails(person_id: str) -> List[Dict[str, Any]]:
    """
    Get email addresses for a specific person by their ID.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        List of email addresses with details
    """
    try:
        response = make_sync_request(f"/people/{person_id}/emails")
        emails = []
        
        for email_data in response.get("data", []):
            attributes = email_data.get("attributes", {})
            emails.append({
                "id": email_data["id"],
                "address": attributes.get("address"),
                "location": attributes.get("location"),
                "primary": attributes.get("primary", False),
                "blocked": attributes.get("blocked", False),
                "created_at": attributes.get("created_at"),
                "updated_at": attributes.get("updated_at")
            })
        
        return emails
    except Exception as e:
        return [{"error": f"Failed to get emails: {str(e)}"}]

@mcp.tool()
def get_person_complete_contact_info(person_id: str) -> Dict[str, Any]:
    """
    Get complete contact information for a person including phone numbers, addresses, and emails.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        Complete contact information for the person
    """
    try:
        # Get basic person info first
        person_response = make_sync_request(f"/people/{person_id}")
        person_data = extract_person_data(person_response["data"])
        
        # Initialize contact data containers
        phone_numbers = []
        addresses = []
        emails = []
        
        # Get contact details with individual error handling
        try:
            phone_response = make_sync_request(f"/people/{person_id}/phone_numbers")
            for phone_data in phone_response.get("data", []):
                attributes = phone_data.get("attributes", {})
                phone_numbers.append({
                    "id": phone_data["id"],
                    "number": attributes.get("number"),
                    "carrier": attributes.get("carrier"),
                    "location": attributes.get("location"),
                    "primary": attributes.get("primary", False)
                })
        except Exception as e:
            phone_numbers = [{"error": f"Failed to get phone numbers: {str(e)}"}]
        
        try:
            address_response = make_sync_request(f"/people/{person_id}/addresses")
            for address_data in address_response.get("data", []):
                attributes = address_data.get("attributes", {})
                addresses.append({
                    "id": address_data["id"],
                    "street": attributes.get("street_line_1") or attributes.get("street"),
                    "city": attributes.get("city") or attributes.get("locality"),
                    "state": attributes.get("state") or attributes.get("region"),
                    "zip": attributes.get("zip") or attributes.get("postal_code"),
                    "location": attributes.get("location"),
                    "primary": attributes.get("primary", False)
                })
        except Exception as e:
            addresses = [{"error": f"Failed to get addresses: {str(e)}"}]
        
        try:
            email_response = make_sync_request(f"/people/{person_id}/emails")
            for email_data in email_response.get("data", []):
                attributes = email_data.get("attributes", {})
                emails.append({
                    "id": email_data["id"],
                    "address": attributes.get("address"),
                    "location": attributes.get("location"),
                    "primary": attributes.get("primary", False)
                })
        except Exception as e:
            emails = [{"error": f"Failed to get emails: {str(e)}"}]
        
        person_data.update({
            "phone_numbers": phone_numbers,
            "addresses": addresses,
            "emails": emails
        })
        
        return person_data
        
    except Exception as e:
        return {"error": f"Failed to get person details: {str(e)}"}

@mcp.tool()
def get_person_complete_contact_info_safe(person_id: str) -> Dict[str, Any]:
    """
    Get complete contact information with extra safety checks and detailed error reporting.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        Complete contact information for the person with detailed status
    """
    result = {
        "person_id": person_id,
        "basic_info": None,
        "phone_numbers": None,
        "addresses": None,
        "emails": None,
        "errors": [],
        "success_count": 0,
        "total_requests": 4
    }
    
    # Get basic person info
    try:
        person_response = make_sync_request(f"/people/{person_id}")
        result["basic_info"] = extract_person_data(person_response["data"])
        result["success_count"] += 1
    except Exception as e:
        result["errors"].append(f"Basic info failed: {str(e)}")
    
    # Get phone numbers
    try:
        result["phone_numbers"] = get_person_phone_numbers(person_id)
        if not any("error" in item for item in result["phone_numbers"]):
            result["success_count"] += 1
        else:
            result["errors"].append("Phone numbers had errors")
    except Exception as e:
        result["errors"].append(f"Phone numbers failed: {str(e)}")
    
    # Get addresses
    try:
        result["addresses"] = get_person_addresses(person_id)
        if not any("error" in item for item in result["addresses"]):
            result["success_count"] += 1
        else:
            result["errors"].append("Addresses had errors")
    except Exception as e:
        result["errors"].append(f"Addresses failed: {str(e)}")
    
    # Get emails
    try:
        result["emails"] = get_person_emails(person_id)
        if not any("error" in item for item in result["emails"]):
            result["success_count"] += 1
        else:
            result["errors"].append("Emails had errors")
    except Exception as e:
        result["errors"].append(f"Emails failed: {str(e)}")
    
    return result@mcp.tool()
def search_people_with_contact_info(
    query: str,
    include_phone: bool = True,
    include_address: bool = False,
    include_email: bool = False
) -> List[Dict[str, Any]]:
    """
    Search for people and optionally include their contact information.
    
    Args:
        query: Search query string
        include_phone: Whether to include phone numbers (default: True)
        include_address: Whether to include addresses (default: False)  
        include_email: Whether to include email addresses (default: False)
        
    Returns:
        List of people with requested contact information
    """
    try:
        # Search for people
        params = {"where[search_name_or_email]": query}
        response = make_sync_request("/people", params)
        
        people = []
        for person_data in response.get("data", [])[:5]:  # Limit to 5 results
            person = extract_person_data(person_data)
            person_id = person["id"]
            
            # Add contact info if requested
            if include_phone:
                person["phone_numbers"] = get_person_phone_numbers(person_id)
            if include_address:
                person["addresses"] = get_person_addresses(person_id)
            if include_email:
                person["emails"] = get_person_emails(person_id)
            
            people.append(person)
        
        return people
    except Exception as e:
        return [{"error": f"Failed to search people: {str(e)}"}]

@mcp.tool()
def debug_person_address_raw(person_id: str) -> Dict[str, Any]:
    """
    Get raw address data for debugging API field names.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        Raw API response for addresses
    """
    try:
        response = make_sync_request(f"/people/{person_id}/addresses")
        return response
    except Exception as e:
        return {"error": f"Failed to get raw address data: {str(e)}"}

# Keep existing functions from your original implementation
@mcp.tool()
def search_people(query: str) -> List[Dict[str, Any]]:
    """Search for people by name, email, or other identifying information."""
    try:
        params = {"where[search_name_or_email]": query}
        response = make_sync_request("/people", params)
        return [extract_person_data(person) for person in response.get("data", [])]
    except Exception as e:
        return [{"error": f"Failed to search people: {str(e)}"}]

@mcp.tool()
def get_person_details(person_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific person."""
    try:
        response = make_sync_request(f"/people/{person_id}")
        return extract_person_data(response["data"])
    except Exception as e:
        return {"error": f"Failed to get person details: {str(e)}"}

@mcp.tool()
def list_people_with_approved_background_checks() -> List[Dict[str, Any]]:
    """List all people with approved background checks."""
    try:
        params = {"where[passed_background_check]": "true"}
        response = make_sync_request("/people", params)
        return [extract_person_data(person) for person in response.get("data", [])]
    except Exception as e:
        return [{"error": f"Failed to get people with approved background checks: {str(e)}"}]

# ===== ATTENDANCE / HEADCOUNT FUNCTIONS =====


# ===== HARD-CODED SERVICE NAMES FOR ATTENDANCE =====
SERVICE_NAMES = [
    'EH 10:15am',
    'EH 12:15pm',
    'EH 8:15am',
    'EW 11:00am',
    'EW 9:00am',
]
EVENT_ID_FOR_TOTALS = "701347"               # the fixed Check-Ins Event ID

@mcp.tool()
def get_total_attendance_details_for_date(date: str) -> Dict[str, Any]:
    """
    Return attendance details for the hard-coded service names (EH 8:15am, EH 10:15am, etc.)
    for a single Check-Ins EVENT (hard-coded via EVENT_ID_FOR_TOTALS) on a given date.

    Args:
        date: ISO date (YYYY-MM-DD), e.g., "2025-09-21"

    Returns:
        {
          "date": "YYYY-MM-DD",
          "services": [
            {
              "service_name": "EH 8:15am",
              "total": int
            }, ...
          ],
          "grand_total": int
        }
        or {"error": "..."} on failure.
    """
    try:
        # 1) Find the event_period (session) for the given date
        try:
            start_dt = datetime.strptime(date, "%Y-%m-%d").date()
        except Exception:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}

        next_dt = start_dt + timedelta(days=1)
        period_params = {
            "where[starts_at][gte]": start_dt.isoformat(),
            "where[starts_at][lt]": next_dt.isoformat(),
            "order": "starts_at",
            "per_page": 100,
        }
        periods_page = make_sync_request(
            f"/events/{EVENT_ID_FOR_TOTALS}/event_periods",
            period_params,
            base_url=PLANNING_CENTER_CHECKINS_BASE_URL
        )
        periods = periods_page.get("data", [])
        if not periods:
            return {
                "date": date,
                "error": f"No event_period (session) found for {date}."
            }
        period_id = periods[0].get("id")

        # 2) Fetch event_times with headcounts & attendance_types
        endpoint = f"/events/{EVENT_ID_FOR_TOTALS}/event_periods/{period_id}/event_times"
        params = {
            "per_page": 100,
            "include": "headcounts,headcounts.attendance_type"
        }
        page = make_sync_request(endpoint, params, base_url=PLANNING_CENTER_CHECKINS_BASE_URL)
        included = page.get("included", [])

        # 3) Build mapping for attendance types
        attendance_types: Dict[str, str] = {
            item["id"]: item["attributes"]["name"]
            for item in included
            if item.get("type") == "AttendanceType"
        }
        headcounts = [item for item in included if item.get("type") == "Headcount"]

        # 4) For each service, find max headcount matching that attendance type
        counted_by_name: Dict[str, int] = {}
        grand_total = 0
        
        for service_name in SERVICE_NAMES:
            max_total = 0
            for hc in headcounts:
                relationships = hc.get("relationships", {})
                atid = None
                if "attendance_type" in relationships and relationships["attendance_type"].get("data"):
                    atid = relationships["attendance_type"]["data"].get("id")
                att_name = attendance_types.get(str(atid)) if atid else None
                total = hc.get("attributes", {}).get("total", 0) or 0
                if att_name == service_name and total > max_total:
                    max_total = total
            counted_by_name[service_name] = max_total
            grand_total += max_total

        # 5) Format response
        services = [
            {"service_name": name, "total": total}
            for name, total in counted_by_name.items()
        ]

        return {
            "date": date,
            "services": services,
            "grand_total": grand_total
        }

    except Exception as e:
        return {"error": f"Failed to get attendance for {date}: {str(e)}"}



@mcp.tool()
def list_event_times_for_event(event_id: str) -> List[Dict[str, Any]]:
    """
    List all event times for a specific event.
    
    Args:
        event_id: The ID of the event
        
    Returns:
        List of event times for the specified event (e.g., "9:00 AM", "11:00 AM").
    """
    try:
        params = {"where[event_id]": event_id}
        response = make_sync_request("/event_times", params, base_url=PLANNING_CENTER_CHECKINS_BASE_URL)
        return response.get("data", [])
    except Exception as e:
        return [{"error": f"Failed to get event times for event: {str(e)}"}]

if __name__ == "__main__":
    mcp.run()