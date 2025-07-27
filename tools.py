"""
Planning Center MCP Tools

MCP tools for querying and filtering people data from Planning Center.
"""
import logging
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from client import pc_client

# Configure logging
logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP):
    """Register all MCP tools with the FastMCP server."""
    
    @mcp.tool()
    async def list_people_with_approved_background_checks() -> List[Dict[str, Any]]:
        """
        List all people with approved background checks.
        
        Returns:
            List of people with approved background checks including their basic information.
        """
        try:
            # Get people with background checks
            response = await pc_client.get("background_checks", {
                "filter": "status:approved",
                "include": "person"
            })
            
            people = []
            for check in response.get("data", []):
                if check.get("relationships", {}).get("person", {}).get("data"):
                    person_id = check["relationships"]["person"]["data"]["id"]
                    # Get person details
                    person_response = await pc_client.get(f"people/{person_id}")
                    if person_response.get("data"):
                        people.append(person_response["data"])
            
            return people
        except Exception as e:
            logger.error(f"Error fetching people with approved background checks: {e}")
            return []

    @mcp.tool()
    async def list_people_with_role(role_name: str) -> List[Dict[str, Any]]:
        """
        List all people with a specific role.
        
        Args:
            role_name: The name of the role to search for
            
        Returns:
            List of people with the specified role.
        """
        try:
            # Search for the role first using JSON API 1.0 syntax
            roles_response = await pc_client.get("roles", {
                "where[name]": role_name
            })
            
            if not roles_response.get("data"):
                return []
            
            role_id = roles_response["data"][0]["id"]
            
            # Get people with this role using JSON API 1.0 syntax
            response = await pc_client.get("people", {
                "where[role_id]": role_id,
                "include": "roles"
            })
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching people with role {role_name}: {e}")
            return []

    @mcp.tool()
    async def list_people_by_age_range(min_age: Optional[int] = None, max_age: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all people within a specific age range.
        
        Args:
            min_age: Minimum age (optional)
            max_age: Maximum age (optional)
            
        Returns:
            List of people within the specified age range.
        """
        try:
            filters = []
            if min_age is not None:
                filters.append(f"age:>={min_age}")
            if max_age is not None:
                filters.append(f"age:<={max_age}")
            
            if not filters:
                # If no age filters, return all people
                response = await pc_client.get("people")
            else:
                response = await pc_client.get("people", {
                    "filter": ",".join(filters)
                })
            
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching people by age range {min_age}-{max_age}: {e}")
            return []

    @mcp.tool()
    async def list_people_by_gender(gender: str) -> List[Dict[str, Any]]:
        """
        List all people with a specific gender.
        
        Args:
            gender: The gender to filter by (e.g., "Male", "Female")
            
        Returns:
            List of people with the specified gender.
        """
        try:
            response = await pc_client.get("people", {
                "where[gender]": gender
            })
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching people by gender {gender}: {e}")
            return []

    @mcp.tool()
    async def list_people_with_household() -> List[Dict[str, Any]]:
        """
        List all people who belong to a household.
        
        Returns:
            List of people who are part of a household.
        """
        try:
            response = await pc_client.get("people", {
                "where[household_id]": "not_null",
                "include": "household"
            })
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching people with households: {e}")
            return []

    @mcp.tool()
    async def list_people_in_family(family_name: str) -> List[Dict[str, Any]]:
        """
        List all people with a specific family name.
        
        Args:
            family_name: The family/last name to search for
            
        Returns:
            List of people with the specified family name.
        """
        try:
            response = await pc_client.get("people", {
                "where[last_name]": family_name
            })
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching people in family {family_name}: {e}")
            return []

    @mcp.tool()
    async def list_people_with_membership(membership_type: str) -> List[Dict[str, Any]]:
        """
        List all people with a specific membership type.
        
        Args:
            membership_type: The membership type to search for
            
        Returns:
            List of people with the specified membership.
        """
        try:
            # Use correct JSON API 1.0 syntax: where[membership]=value
            logger.info(f"Searching for people with membership type: {membership_type}")
            
            response = await pc_client.get("people", {
                "where[membership]": membership_type,
                "include": "memberships"
            })
            
            results = response.get("data", [])
            logger.info(f"Found {len(results)} people with membership '{membership_type}'")
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching people with membership {membership_type}: {e}")
            return []

    @mcp.tool()
    async def search_people(query: str) -> List[Dict[str, Any]]:
        """
        Search for people by name, email, or other identifying information.
        
        Args:
            query: Search query string
            
        Returns:
            List of people matching the search query.
        """
        try:
            response = await pc_client.get("people", {
                "where[search_name]": query
            })
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Error searching people with query {query}: {e}")
            return []

    @mcp.tool()
    async def get_person_details(person_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific person.
        
        Args:
            person_id: The ID of the person to retrieve
            
        Returns:
            Detailed person information including relationships.
        """
        try:
            response = await pc_client.get(f"people/{person_id}", {
                "include": "household,roles,memberships,background_checks"
            })
            return response.get("data", {})
        except Exception as e:
            logger.error(f"Error fetching person details for {person_id}: {e}")
            return {}

    @mcp.tool()
    async def list_background_checks(
        status: Optional[str] = None,
        completed_after: Optional[str] = None,
        completed_before: Optional[str] = None,
        check_type: Optional[str] = None,
        include_person_details: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List background checks with flexible filtering options.
        
        Args:
            status: Filter by status (e.g., "approved", "pending", "denied", "expired")
            completed_after: Filter for checks completed after this date (YYYY-MM-DD format)
            completed_before: Filter for checks completed before this date (YYYY-MM-DD format)
            check_type: Filter by check type if available
            include_person_details: Whether to include detailed person information (default: True)
            
        Returns:
            List of background checks with optional person details.
            
        Examples:
            - List all approved background checks: status="approved"
            - List checks completed in last year: completed_after="2023-01-01"
            - List recent approved checks: status="approved", completed_after="2024-01-01"
        """
        try:
            # Build parameters using JSON API 1.0 syntax
            params = {}
            
            if status:
                params["where[status]"] = status
            
            if completed_after:
                params["where[completed_at]"] = f">{completed_after}"
                
            if completed_before:
                params["where[completed_at]"] = f"<{completed_before}"
                
            if check_type:
                params["where[check_type]"] = check_type
            
            if include_person_details:
                params["include"] = "person"
            
            # Get background checks
            response = await pc_client.get("background_checks", params)
            
            checks = response.get("data", [])
            
            # If person details are requested, enrich the data
            if include_person_details:
                enriched_checks = []
                for check in checks:
                    enriched_check = check.copy()
                    
                    # Get person details if relationship exists
                    if check.get("relationships", {}).get("person", {}).get("data"):
                        person_id = check["relationships"]["person"]["data"]["id"]
                        try:
                            person_response = await pc_client.get(f"people/{person_id}")
                            if person_response.get("data"):
                                enriched_check["person_details"] = person_response["data"]
                        except Exception as person_error:
                            logger.warning(f"Could not fetch person details for {person_id}: {person_error}")
                            enriched_check["person_details"] = None
                    
                    enriched_checks.append(enriched_check)
                
                return enriched_checks
            
            return checks
            
        except Exception as e:
            logger.error(f"Error fetching background checks with filters: {e}")
            return []
