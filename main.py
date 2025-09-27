#!/usr/bin/env python3

import asyncio
import os
from typing import Any, Dict, List, Optional, Union
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import time

# Load environment variables
load_dotenv()

# Planning Center API configuration
PLANNING_CENTER_BASE_URL = "https://api.planningcenteronline.com/people/v2"
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

class PersonModel(BaseModel):
    id: str
    name: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone_numbers: Optional[List[Dict[str, Any]]] = None
    addresses: Optional[List[Dict[str, Any]]] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    membership: Optional[str] = None
    background_check_approved: Optional[bool] = None

async def make_api_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make authenticated request to Planning Center API with rate limiting"""
    if not rate_limiter.can_make_request():
        raise Exception("Rate limit exceeded. Planning Center allows 100 requests per minute.")
    
    rate_limiter.record_request()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PLANNING_CENTER_BASE_URL}{endpoint}",
            auth=(CLIENT_ID, SECRET),
            params=params or {},
            headers={"Accept": "application/vnd.api+json"}
        )
        response.raise_for_status()
        return response.json()

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
async def get_person_phone_numbers(person_id: str) -> List[Dict[str, Any]]:
    """
    Get phone numbers for a specific person by their ID.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        List of phone numbers with details
    """
    try:
        response = await make_api_request(f"/people/{person_id}/phone_numbers")
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
async def get_person_addresses(person_id: str) -> List[Dict[str, Any]]:
    """
    Get addresses for a specific person by their ID.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        List of addresses with details
    """
    try:
        response = await make_api_request(f"/people/{person_id}/addresses")
        addresses = []
        
        for address_data in response.get("data", []):
            attributes = address_data.get("attributes", {})
            addresses.append({
                "id": address_data["id"],
                "street": attributes.get("street"),
                "city": attributes.get("city"),
                "state": attributes.get("state"),
                "zip": attributes.get("zip"),
                "location": attributes.get("location"),
                "primary": attributes.get("primary", False),
                "created_at": attributes.get("created_at"),
                "updated_at": attributes.get("updated_at")
            })
        
        return addresses
    except Exception as e:
        return [{"error": f"Failed to get addresses: {str(e)}"}]

@mcp.tool()
async def get_person_emails(person_id: str) -> List[Dict[str, Any]]:
    """
    Get email addresses for a specific person by their ID.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        List of email addresses with details
    """
    try:
        response = await make_api_request(f"/people/{person_id}/emails")
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
async def get_person_complete_contact_info(person_id: str) -> Dict[str, Any]:
    """
    Get complete contact information for a person including phone numbers, addresses, and emails.
    
    Args:
        person_id: The Planning Center person ID
        
    Returns:
        Complete contact information for the person
    """
    try:
        # Get basic person info
        person_response = await make_api_request(f"/people/{person_id}")
        person_data = extract_person_data(person_response["data"])
        
        # Get contact details in parallel
        phone_numbers = await get_person_phone_numbers(person_id)
        addresses = await get_person_addresses(person_id)
        emails = await get_person_emails(person_id)
        
        person_data.update({
            "phone_numbers": phone_numbers,
            "addresses": addresses,
            "emails": emails
        })
        
        return person_data
    except Exception as e:
        return {"error": f"Failed to get complete contact info: {str(e)}"}

@mcp.tool()
async def search_people_with_contact_info(
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
        response = await make_api_request("/people", params)
        
        people = []
        for person_data in response.get("data", [])[:10]:  # Limit to 10 results
            person = extract_person_data(person_data)
            person_id = person["id"]
            
            # Add contact info if requested
            if include_phone:
                person["phone_numbers"] = await get_person_phone_numbers(person_id)
            if include_address:
                person["addresses"] = await get_person_addresses(person_id)
            if include_email:
                person["emails"] = await get_person_emails(person_id)
            
            people.append(person)
        
        return people
    except Exception as e:
        return [{"error": f"Failed to search people: {str(e)}"}]

@mcp.tool()
async def list_people_with_filters(
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    gender: Optional[str] = None,
    membership_type: Optional[str] = None,
    status: Optional[str] = "active",
    include_contact: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    List people with advanced filtering options.
    
    Args:
        min_age: Minimum age filter
        max_age: Maximum age filter  
        gender: Gender filter (e.g., "Male", "Female")
        membership_type: Membership type filter
        status: Status filter (default: "active")
        include_contact: Whether to include contact information
        limit: Maximum number of results (default: 50)
        
    Returns:
        List of people matching the filters
    """
    try:
        params = {"per_page": str(limit)}
        
        if status:
            params["where[status]"] = status
        if gender:
            params["where[gender]"] = gender
        if membership_type:
            params["where[membership]"] = membership_type
        
        response = await make_api_request("/people", params)
        
        people = []
        for person_data in response.get("data", []):
            person = extract_person_data(person_data)
            
            # Apply age filters
            if person.get("age"):
                if min_age and person["age"] < min_age:
                    continue
                if max_age and person["age"] > max_age:
                    continue
            
            if include_contact:
                person_id = person["id"]
                person["phone_numbers"] = await get_person_phone_numbers(person_id)
                person["addresses"] = await get_person_addresses(person_id)
                person["emails"] = await get_person_emails(person_id)
            
            people.append(person)
        
        return people
    except Exception as e:
        return [{"error": f"Failed to list people: {str(e)}"}]

# Keep existing functions from your original implementation
@mcp.tool()
async def list_people_with_approved_background_checks() -> List[Dict[str, Any]]:
    """List all people with approved background checks."""
    try:
        params = {"where[passed_background_check]": "true"}
        response = await make_api_request("/people", params)
        return [extract_person_data(person) for person in response.get("data", [])]
    except Exception as e:
        return [{"error": f"Failed to get people with approved background checks: {str(e)}"}]

@mcp.tool()
async def list_people_with_role(role_name: str) -> List[Dict[str, Any]]:
    """List all people with a specific role."""
    try:
        # Note: This might need adjustment based on actual API structure for roles
        params = {"where[role]": role_name}
        response = await make_api_request("/people", params)
        return [extract_person_data(person) for person in response.get("data", [])]
    except Exception as e:
        return [{"error": f"Failed to get people with role {role_name}: {str(e)}"}]

@mcp.tool()
async def list_people_by_age_range(min_age: Optional[int] = None, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
    """List all people within a specific age range."""
    return await list_people_with_filters(min_age=min_age, max_age=max_age)

@mcp.tool()
async def list_people_by_gender(gender: str) -> List[Dict[str, Any]]:
    """List all people with a specific gender."""
    return await list_people_with_filters(gender=gender)

@mcp.tool()
async def list_people_with_household() -> List[Dict[str, Any]]:
    """List all people who belong to a household."""
    try:
        response = await make_api_request("/people")
        # Filter for people with household information
        people_with_households = []
        for person_data in response.get("data", []):
            person = extract_person_data(person_data)
            # Check if person has household relationships
            if person_data.get("relationships", {}).get("households"):
                people_with_households.append(person)
        return people_with_households
    except Exception as e:
        return [{"error": f"Failed to get people with households: {str(e)}"}]

@mcp.tool()
async def list_people_in_family(family_name: str) -> List[Dict[str, Any]]:
    """List all people with a specific family name."""
    try:
        params = {"where[last_name]": family_name}
        response = await make_api_request("/people", params)
        return [extract_person_data(person) for person in response.get("data", [])]
    except Exception as e:
        return [{"error": f"Failed to get people in family {family_name}: {str(e)}"}]

@mcp.tool()
async def list_people_with_membership(membership_type: str) -> List[Dict[str, Any]]:
    """List all people with a specific membership type."""
    return await list_people_with_filters(membership_type=membership_type)

@mcp.tool()
async def search_people(query: str) -> List[Dict[str, Any]]:
    """Search for people by name, email, or other identifying information."""
    return await search_people_with_contact_info(query, include_phone=False)

@mcp.tool()
async def get_person_details(person_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific person."""
    try:
        response = await make_api_request(f"/people/{person_id}")
        return extract_person_data(response["data"])
    except Exception as e:
        return {"error": f"Failed to get person details: {str(e)}"}

@mcp.tool()
async def list_background_checks(
    status: Optional[str] = None,
    completed_after: Optional[str] = None,
    completed_before: Optional[str] = None,
    check_type: Optional[str] = None,
    include_person_details: bool = True
) -> List[Dict[str, Any]]:
    """List background checks with flexible filtering options."""
    try:
        params = {}
        if status:
            params["where[status]"] = status
        if completed_after:
            params["where[completed_at][gte]"] = completed_after
        if completed_before:
            params["where[completed_at][lte]"] = completed_before
        if check_type:
            params["where[check_type]"] = check_type
        
        response = await make_api_request("/background_checks", params)
        
        background_checks = []
        for check_data in response.get("data", []):
            attributes = check_data.get("attributes", {})
            check_info = {
                "id": check_data["id"],
                "status": attributes.get("status"),
                "completed_at": attributes.get("completed_at"),
                "check_type": attributes.get("check_type"),
                "created_at": attributes.get("created_at"),
                "updated_at": attributes.get("updated_at")
            }
            
            # Include person details if requested
            if include_person_details:
                person_id = check_data.get("relationships", {}).get("person", {}).get("data", {}).get("id")
                if person_id:
                    person_details = await get_person_details(person_id)
                    check_info["person"] = person_details
            
            background_checks.append(check_info)
        
        return background_checks
    except Exception as e:
        return [{"error": f"Failed to get background checks: {str(e)}"}]

if __name__ == "__main__":
    mcp.run()
