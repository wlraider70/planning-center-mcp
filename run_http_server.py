#!/usr/bin/env python3
"""
Run the Planning Center MCP Server in HTTP mode for API testing.

This script starts the server with HTTP transport, exposing:
- OpenAPI documentation at /docs
- ReDoc interactive documentation at /redoc
- REST API endpoints for all MCP tools

Usage:
    python run_http_server.py [--port PORT]
"""
import os
import sys
import argparse

def main():
    """Run the MCP server in HTTP mode."""
    parser = argparse.ArgumentParser(description="Run Planning Center MCP Server in HTTP mode")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port to run the server on (default: 8000)")
    
    args = parser.parse_args()
    
    # Set environment variables for HTTP transport
    os.environ["MCP_TRANSPORT"] = "http"
    os.environ["MCP_PORT"] = str(args.port)
    
    print(f"🚀 Starting Planning Center MCP Server in HTTP mode on port {args.port}")
    print(f"📖 OpenAPI docs: http://localhost:{args.port}/docs")
    print(f"🔧 ReDoc docs: http://localhost:{args.port}/redoc")
    print("Press Ctrl+C to stop the server")
    print()
    
    # Import and run the main function
    try:
        from main import run_main
        run_main()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
