from dotenv import load_dotenv
load_dotenv()

import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

# Define path to task_agent directory
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

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
    tools=[filesystem_toolset]
)
