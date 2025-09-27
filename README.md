# Planning Center MCP Server

A FastMCP server that provides comprehensive tools for the Planning Center People API. This server implements MCP (Model Context Protocol) tools for querying, filtering, and retrieving detailed contact information from Planning Center using the JSON API specification 1.0.

## ✨ Features

### Core People Management
- **Search and Filter**: Advanced people search with multiple filter options
- **Background Checks**: List and filter background check information
- **Demographics**: Filter by age, gender, membership type, and more

### 🆕 Enhanced Contact Information
- **Phone Numbers**: Retrieve complete phone number details with carrier info
- **Email Addresses**: Get all email addresses with primary/secondary designations  
- **Physical Addresses**: Access full address information including location types
- **Complete Contact Profiles**: Get all contact info in a single request

### Advanced Search & Filtering
- **Multi-criteria Filtering**: Combine age ranges, gender, membership, and status
- **Contact-Aware Search**: Search with automatic contact information inclusion
- **Background Check Integration**: Filter by background check status and dates

## 🔧 Available Tools

### Basic People Operations
- `search_people`: Search for people by name, email, or other identifying information
- `get_person_details`: Get detailed information about a specific person
- `list_people_with_approved_background_checks`: Get all people with approved background checks

### Contact Information Tools
- `get_person_phone_numbers`: Get phone numbers for a specific person
- `get_person_addresses`: Get addresses for a specific person  
- `get_person_emails`: Get email addresses for a specific person
- `get_person_complete_contact_info`: Get all contact information in one call
- `search_people_with_contact_info`: Search with optional contact information inclusion

### Advanced Filtering
- `list_people_with_filters`: Advanced filtering by multiple criteria
- `list_people_by_age_range`: Filter people by age range
- `list_people_by_gender`: Filter people by gender
- `list_people_in_family`: Find people with a specific family/last name
- `list_people_with_membership`: Get people with a specific membership type
- `list_people_with_household`: Get people who belong to a household

### Background Checks
- `list_background_checks`: List background checks with flexible filtering options

## 🚀 Installation

This project uses `uv` for dependency management:

```bash
uv sync
```

## 📝 Configuration

Copy the example environment file and add your Planning Center credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Planning Center API credentials:

```env
PLANNING_CENTER_CLIENT_ID=your_client_id_here
PLANNING_CENTER_SECRET=your_secret_here
```

### Getting API Credentials

1. Go to [https://api.planningcenteronline.com/oauth/applications](https://api.planningcenteronline.com/oauth/applications)
2. Create a new application
3. Copy the Client ID and Secret to your `.env` file

## 🎯 Usage

### Running the Server

```bash
uv run planning-center-mcp
```

Or directly with Python:

```bash
uv run python main.py
```

### Claude Desktop Integration

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
        "/path/to/your/planning-center-mcp",
        "planning-center-mcp"
      ]
    }
  }
}
```

Replace `/path/to/your/planning-center-mcp` with the actual path to your project directory.

## 📋 Usage Examples

### Get Complete Contact Information
```python
# Get all contact details for Nick Werhle
contact_info = await get_person_complete_contact_info("46578589")
```

### Search with Phone Numbers
```python  
# Search for people and include their phone numbers
results = await search_people_with_contact_info(
    "Nick Werhle", 
    include_phone=True, 
    include_email=True
)
```

### Advanced Filtering
```python
# Find all active male members aged 18-65 with contact info
people = await list_people_with_filters(
    min_age=18,
    max_age=65, 
    gender="Male",
    status="active",
    include_contact=True
)
```

### Background Check Filtering
```python
# Get recent approved background checks
checks = await list_background_checks(
    status="approved",
    completed_after="2024-01-01",
    include_person_details=True
)
```

## 🚦 Rate Limiting

Planning Center has a rate limit of 100 requests per minute. The MCP server automatically handles this by:

- Tracking requests per minute
- Throwing an error if the limit is exceeded
- Providing clear error messages for rate limit issues

## 📊 API Compliance

This server is designed to work with Planning Center's JSON API specification 1.0, handling:

- Proper filtering and querying
- JSONAPI relationship traversal
- Error handling and response formatting
- Rate limit compliance

## 📁 Project Structure

```
planning-center-mcp/
├── main.py              # Enhanced MCP server implementation
├── pyproject.toml       # Project configuration and dependencies  
├── .env.example         # Example environment variables
├── .env                 # Your environment variables (not in git)
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## 🧪 Testing

You can test the MCP server locally by running it and checking the logs. The server will use demo credentials if no real credentials are provided, but functionality will be limited.

## 🐛 Troubleshooting

### Common Issues

- **Authentication Issues**: Make sure your Planning Center credentials are correctly set in the `.env` file
- **Rate Limiting**: If you hit rate limits, wait a minute before making more requests  
- **Connection Issues**: Check your internet connection and Planning Center API status
- **Permission Issues**: Ensure your Planning Center account has appropriate permissions for the data you're requesting

### Contact Information Not Appearing

If contact information isn't showing up:

1. Verify the person exists and has the contact info in Planning Center
2. Check that your API credentials have permission to access contact information
3. Ensure the person's privacy settings allow API access to their contact details

## 📄 License

This project is open source. See the license file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
