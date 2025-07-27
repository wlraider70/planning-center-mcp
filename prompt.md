I want to create an MCP Server using Python and fastMCP.

The MCP server should be a tools for the Planning Center People API.  The Planning Center APIs are written to conform to JSON API specification 1.0.  The MCP server should be able to handle the JSON API specification 1.0. that it uses to query, filter, and returns.

All MCP requests should be authenticated using a Planning Center API Key which should be set as an environment variable, it can be in an .env file in this repo (also make sure to gitignore the .env file and document how to create one locally and supply your own key)  The variables will be:
PLANNING_CENTER_CLIENT_ID
PLANNING_CENTER_SECRET

Also note Planning Center has a rate limit of 100 requests per minute, so the MCP server should be able to handle that.

All dates and times conform to the ISO 8601 standard.

Here is the documentation for all the Planning Center People API endpoints:
https://developer.planning.center/docs/#/apps/people/2025-07-17

Look at these and deduce some obvious searches that people might want to do such as:
- List all people with approved background checks
- List all people with a specific role
- List all people with a specific 
- list all people within an age range, or over an age range
- list all people with a specific gender
- list all people with a household
- list all people with a specific family
- list all people with a specific membership

Also, I want to make sure this is as easily testable locally as possible.

Provide me the mcpServers config for claude desktop app so I can tell it how to start this app and use it.