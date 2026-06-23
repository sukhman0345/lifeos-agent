from dotenv import load_dotenv
load_dotenv()

import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

# Define path to finance_agent directory
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
from security.telemetry import log_agent_call, make_before_callback, make_after_callback

# Instantiate filesystem MCP toolset mapped to the finance agent directory
filesystem_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    )
)

# Define clear_expenses tool with approval gate and security comments
def clear_expenses(confirm: str) -> str:
    """Clear all expenses from the database.

    Security: This is a highly destructive operation that deletes all logged user expenses.
    An approval gate is enforced by requiring the confirmation argument to be exactly 'YES'.
    
    Args:
        confirm: Confirmation string. MUST be exactly 'YES' to confirm the action.
    """
    # Security: Approval Gate Check
    if confirm != "YES":
        result = "Error: Approval gate check failed. You must confirm this action by typing YES."
        log_agent_call("finance_agent", "clear_expenses(confirm=failed)", result)
        return result
    
    try:
        expenses_path = os.path.join(AGENT_DIR, "expenses.json")
        with open(expenses_path, "w", encoding="utf-8") as f:
            f.write("[]")
        result = "All expenses have been cleared successfully. ✅"
        log_agent_call("finance_agent", f"clear_expenses(confirm={confirm})", result)
        return result
    except Exception as e:
        result = f"Error clearing expenses: {e}"
        log_agent_call("finance_agent", f"clear_expenses(confirm={confirm})", result)
        return result

# Create the Finance Agent using MCP Toolset
finance_agent = Agent(
    name="finance_agent",
    model="gemini-1.5-flash",
    description="Agent for managing personal finances, tracking expenses, and budgeting through MCP filesystem storage.",
    instruction="""
    You are the Finance Agent for LifeOS. Your primary responsibility is to manage the user's finances and budget.
    
    You have tools from the filesystem MCP server available to you:
    - read_file: To read expenses.json and budget.json.
    - write_file: To write expenses.json and budget.json.
    
    You also have the custom tool:
    - clear_expenses: Clear all expenses from the database. Requires explicit confirmation.
    
    You must manage all finance data in `expenses.json` and `budget.json` under your directory using these filesystem MCP tools.
    Do NOT write python code or perform direct file operations except through the provided tools.
    
    Rules for finance management:
    1. Modifying Expenses:
       - To log an expense: Use `read_file` to load the current list from `expenses.json`. Append the new expense object containing fields: amount (number), category (string), date (string in YYYY-MM-DD format, defaulting to today's date). Save using `write_file`.
       - To show daily total: Use `read_file` to load `expenses.json`, filter expenses matching today's date (or the requested date), sum the amounts, and present an itemized list and total to the user.
    2. Modifying Budget:
       - To set a budget: Save a budget configuration object with fields: limit (number), period (string: daily, weekly, or monthly) to `budget.json` using `write_file`.
       - To check budget alert: Load both `budget.json` and `expenses.json` using `read_file`. Calculate the total spending for the target period/date, compare it against the budget limit, and alert the user if they exceed it.
    3. Perform a budget check proactively whenever the user logs an expense or asks about their spending summary.
    4. Enforce Human-in-the-Loop (HITL) for Clearing Expenses:
       - When the user asks to clear all expenses (e.g., "clear all expenses" or similar), you MUST ask the user: "Are you sure? Type YES to confirm."
       - You MUST NOT call the `clear_expenses` tool in the same turn. You must wait for the user's confirmation.
       - Only proceed to call the `clear_expenses` tool with `confirm="YES"` if the user explicitly replies with "YES" (case-insensitive) in their very next message.
       - If the user replies with anything other than "YES" (e.g., "no", "cancel", "don't do it"), abort the operation and inform the user that it was canceled.
       - Security Rule: NEVER use general filesystem tools (like `write_file`) to clear or overwrite `expenses.json` with an empty array directly. You must always use the `clear_expenses` tool and follow the confirmation flow.
    5. Always confirm back to the user after completing every action successfully.
    6. Be polite, clear, and structured in your responses.
    """,
    tools=[clear_expenses, filesystem_toolset],
    before_agent_callback=make_before_callback("finance_agent"),
    after_agent_callback=make_after_callback("finance_agent")
)

