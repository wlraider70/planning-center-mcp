# Planning Center MCP Server

A FastMCP server that provides tools for the Planning Center People API. This server implements MCP (Model Context Protocol) tools for querying and filtering people data from Planning Center using the JSON API specification 1.0.

## Features

The MCP server provides the following tools for querying Planning Center data:

- **list_people_with_approved_background_checks**: Get all people with approved background checks
- **list_people_with_role**: Find people with a specific role
- **list_people_by_age_range**: Filter people by age range
- **list_people_by_gender**: Filter people by gender
- **list_people_with_household**: Get people who belong to a household
- **list_people_in_family**: Find people with a specific family/last name
- **list_people_with_membership**: Get people with a specific membership type
- **search_people**: Search for people by name, email, or other identifying information
- **get_person_details**: Get detailed information about a specific person

## Setup

### 1. Install Dependencies

This project uses `uv` for dependency management:

```bash
uv sync
```

### 2. Configure Environment Variables

Copy the example environment file and add your Planning Center credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Planning Center API credentials:

```
PLANNING_CENTER_CLIENT_ID=your_client_id_here
PLANNING_CENTER_SECRET=your_secret_here
```

#### Getting Planning Center API Credentials

1. Go to https://api.planningcenteronline.com/oauth/applications
2. Create a new application
3. Copy the Client ID and Secret to your `.env` file

### 3. Run the MCP Server

```bash
uv run planning-center-mcp
```

Or directly with Python:

```bash
uv run python main.py
```

## Claude Desktop Integration

To use this MCP server with Claude Desktop, add the following configuration to your Claude Desktop config file:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "planning-center": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/eric.foster/projects/plan-cp",
        "planning-center-mcp"
      ]
    }
  }
}
```

Replace `/Users/eric.foster/projects/plan-cp` with the actual path to your project directory.

## Rate Limiting

Planning Center has a rate limit of 100 requests per minute. The MCP server automatically handles this by tracking requests and throwing an error if the limit is exceeded.

## API Compliance

This server is designed to work with Planning Center's JSON API specification 1.0, handling proper filtering, querying, and data formatting according to the spec.

## Development

### Project Structure

```
planning-center-mcp/
├── main.py              # Main MCP server implementation
├── pyproject.toml       # Project configuration and dependencies
├── .env.example         # Example environment variables
├── .env                 # Your environment variables (not in git)
├── .gitignore          # Git ignore file
└── README.md           # This file
```

### Testing

You can test the MCP server locally by running it and checking the logs. The server will use demo credentials if no real credentials are provided, but functionality will be limited.

## Troubleshooting

1. **Authentication Issues**: Make sure your Planning Center credentials are correctly set in the `.env` file
2. **Rate Limiting**: If you hit rate limits, wait a minute before making more requests
3. **Connection Issues**: Check your internet connection and Planning Center API status

## License

This project is open source. See the license file for details.
