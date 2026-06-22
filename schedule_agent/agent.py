from dotenv import load_dotenv
load_dotenv()

import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

# Define path to schedule.json folder for filesystem access
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# mcp_servers configuration as requested by user
mcp_servers = {
    "google-calendar": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-google-calendar"]
    },
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    }
}

# Instantiate MCP toolsets
calendar_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=mcp_servers["google-calendar"]["command"],
        args=mcp_servers["google-calendar"]["args"]
    )
)

filesystem_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=mcp_servers["filesystem"]["command"],
        args=mcp_servers["filesystem"]["args"]
    )
)

# Create the Schedule Agent using MCP Toolsets
schedule_agent = Agent(
    name="schedule_agent",
    model="gemini-2.0-flash",
    description=(
        "Agent for managing personal schedule. Uses Google Calendar MCP server to manage real events, "
        "and filesystem MCP server to maintain a local backup in schedule.json."
    ),
    instruction="""
    You are the Schedule Agent for LifeOS. Your primary responsibility is to manage the user's schedule.
    
    You have tools from two MCP servers:
    1. google-calendar:
       - To view, schedule, update, or delete calendar events (e.g. using create_event, list_events, delete_event).
    2. filesystem:
       - To maintain a local backup of the events in `schedule.json` under your directory.
       
    Rules of engagement:
    1. Whenever the user schedules, views, or modifies an event, you MUST perform the action on the real Google Calendar using the google-calendar tools.
    2. Immediately after updating the calendar, you MUST write or update the event data in `schedule.json` locally as a backup.
       - Use read_file to check the backup.
       - Use write_file to save the backup array.
    3. Always confirm to the user after completing every action successfully.
    4. Be friendly, polite, clear, and structured in your responses.
    """,
    tools=[calendar_toolset, filesystem_toolset]
)
