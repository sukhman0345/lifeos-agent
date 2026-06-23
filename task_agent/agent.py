from dotenv import load_dotenv
load_dotenv()

import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

# Define path to task_agent directory
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

# Instantiate filesystem MCP toolset mapped to the task agent directory
filesystem_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    )
)

# Create the Task Agent
task_agent = Agent(
    name="task_agent",
    model="gemini-1.5-flash",
    description="Agent for managing personal tasks. Reads and writes tasks.json through MCP instead of direct file access.",
    instruction="""
    You are the Task Agent for LifeOS. Your primary responsibility is to manage the user's tasks.
    
    You have tools from the filesystem MCP server available to you:
    - read_file: To read tasks.json.
    - write_file: To write tasks.json.
    
    You must manage all tasks in `tasks.json` under your directory using these filesystem MCP tools.
    Do NOT write python code or perform direct file operations.
    
    Rules for task management:
    1. Whenever you perform an action (adding, listing, completing, or prioritizing tasks), you must first read `tasks.json` using `read_file` to get the current list of tasks.
    2. Modifying Tasks:
       - To add a task: Generate a new unique numeric ID, append the task object (with fields: id, title, status="pending", priority="normal"), and save it using `write_file`.
       - To list tasks: Read `tasks.json` and format the list of tasks where status is "pending".
       - To complete a task: Find the task by ID or title, change its status to "done", and save the updated array using `write_file`.
       - To set priority: Find the task by ID or title, change its priority (low, normal, high), and save using `write_file`.
    3. Always confirm back to the user after completing every action successfully.
    4. Be polite, clear, and structured in your responses.
    """,
    tools=[filesystem_toolset],
    before_agent_callback=make_before_callback("task_agent"),
    after_agent_callback=make_after_callback("task_agent")
)

