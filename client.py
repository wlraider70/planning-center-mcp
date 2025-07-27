"""
Planning Center API Client

HTTP client for Planning Center API with authentication and rate limiting.
"""
import os
from typing import Any, Dict, Optional
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Planning Center API configuration
PLANNING_CENTER_CLIENT_ID = os.getenv("PLANNING_CENTER_CLIENT_ID")
PLANNING_CENTER_SECRET = os.getenv("PLANNING_CENTER_SECRET")
BASE_URL = "https://api.planningcenteronline.com/people/v2"

# Rate limiting (100 requests per minute)
RATE_LIMIT = 100
rate_limit_requests = []


class PlanningCenterClient:
    """HTTP client for Planning Center API with authentication and rate limiting."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            auth=(PLANNING_CENTER_CLIENT_ID or "demo", PLANNING_CENTER_SECRET or "demo"),
            timeout=30.0
        )
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        # Remove requests older than 1 minute
        global rate_limit_requests
        rate_limit_requests = [req_time for req_time in rate_limit_requests 
                             if (now - req_time).total_seconds() < 60]
        
        if len(rate_limit_requests) >= RATE_LIMIT:
            raise Exception("Rate limit exceeded. Planning Center allows 100 requests per minute.")
        
        rate_limit_requests.append(now)
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated GET request to Planning Center API."""
        await self._check_rate_limit()
        
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        response = await self.client.get(url, params=params or {})
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
pc_client = PlanningCenterClient()
