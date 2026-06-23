from dotenv import load_dotenv
load_dotenv()

import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

# Define path to schedule.json folder for filesystem access
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define custom SecurityError class
class SecurityError(Exception):
    """Raised when security or data locality checks fail."""
    pass

# =====================================================================
# ZERO-TRUST SECURITY & LOCALITY VERIFICATION
# =====================================================================
# Security Comment: Under zero-trust architecture, we must ensure that
# all data operations, database files, and model context protocol (MCP)
# environments remain restricted to the local machine. Personal user
# data (tasks, finances, schedule, health logs) must not be transmitted
# to unauthorized external cloud databases or third-party networks.
# Note: Google Calendar API access through the MCP server is authorized
# exclusively for official schedule synchronization, while local database
# storage must remain fully isolated on disk.
# =====================================================================
def verify_local_data_isolation(agent_dir: str):
    """Verify that all files are stored strictly on the local filesystem
    and no remote database configurations exist.
    """
    abs_dir = os.path.abspath(agent_dir)
    # Check for UNC path (e.g. \\remote-server) or remote URL schema
    if abs_dir.startswith("\\\\") or any(abs_dir.startswith(s) for s in ["http://", "https://", "ftp://"]):
        raise SecurityError("Critical Security Alert: Remote storage detected. Data must remain local.")
    
    # Check for unauthorized environment variables attempting to leak data or redirect to external hosts
    for env_var in ["DB_HOST", "DATABASE_URL", "CLOUD_SQL_CONNECTION_NAME"]:
        val = os.getenv(env_var)
        if val and not any(local in val.lower() for local in ["localhost", "127.0.0.1", "::1", "local"]):
            raise SecurityError(f"Critical Security Alert: External database target detected in {env_var}: {val}")

# Run local data isolation verification
verify_local_data_isolation(AGENT_DIR)


import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security.telemetry import make_before_callback, make_after_callback

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
    model="gemini-1.5-flash",
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
    tools=[calendar_toolset, filesystem_toolset],
    before_agent_callback=make_before_callback("schedule_agent"),
    after_agent_callback=make_after_callback("schedule_agent")
)

