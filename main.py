"""Planning Center MCP Server

A FastMCP server that provides tools for the Planning Center People API.
This server implements MCP (Model Context Protocol) tools for querying and filtering
people data from Planning Center using the JSON API specification 1.0.

Usage:
    python main.py
"""
# Handle nested event loops FIRST - before any other imports
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    print("Warning: nest_asyncio not available. Install with: pip install nest-asyncio")

import asyncio
import logging
import os
from fastmcp import FastMCP
from dotenv import load_dotenv

# Import our modules
from client import pc_client, PLANNING_CENTER_CLIENT_ID, PLANNING_CENTER_SECRET
from tools import register_tools

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Planning Center MCP Server")

# Register all tools
register_tools(mcp)

async def main():
    """Run the MCP server."""
    try:
        logger.info("🚀 Starting Planning Center MCP Server...")
        
        # Validate environment variables
        if not PLANNING_CENTER_CLIENT_ID or not PLANNING_CENTER_SECRET:
            logger.warning("⚠️  Planning Center credentials not found. Using demo credentials.")
            logger.info("Set PLANNING_CENTER_CLIENT_ID and PLANNING_CENTER_SECRET environment variables.")
        
        # Check if we should run HTTP server (for API testing) or STDIO (for MCP clients)
        transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
        
        if transport == "http":
            port = int(os.getenv("MCP_PORT", "8000"))
            host = os.getenv("MCP_HOST", "localhost")
            logger.info(f"🌐 Starting HTTP server on {host}:{port}")
            logger.info(f"📖 OpenAPI docs will be available at: http://{host}:{port}/mcp/docs")
            logger.info(f"🔧 Interactive API at: http://{host}:{port}/mcp/redoc")
            logger.info(f"🔍 API endpoints at: http://{host}:{port}/mcp/tools/")
            
            # Run the MCP server with HTTP transport
            await mcp.run_async(
                transport="http", 
                port=port,
                host=host,
                path="/mcp",
                log_level="info"
            )
        else:
            logger.info("📡 Starting STDIO transport for MCP clients")
            # Run the MCP server with STDIO transport (default)
            await mcp.run_async(transport="stdio")
            
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    finally:
        await pc_client.close()

def run_main():
    """Run the main function with proper event loop handling."""
    try:
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # If we get here, there's already a running loop
            logger.info("Detected running event loop, scheduling main() as a task...")
            task = asyncio.create_task(main())
            return task
        except RuntimeError:
            # No running loop, we can create one
            logger.info("No running event loop detected, creating new one...")
            return asyncio.run(main())
    except Exception as e:
        logger.error(f"Error in event loop handling: {e}")
        # Fallback: try the old method
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(main())
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise

if __name__ == "__main__":
    run_main()
