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
from fallback_model import FallbackGemini
from security.telemetry import log_agent_call, make_before_callback, make_after_callback

# Instantiate filesystem MCP toolset mapped to the finance agent directory
filesystem_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    )
)

# Define budget_alert tool
async def budget_alert(target_date: str = None) -> str:
    """Check if the total spending for a given date has exceeded the daily budget limit.

    Args:
        target_date: The date to check in YYYY-MM-DD format. Defaults to today's date.

    Returns:
        A warning message if the budget is exceeded, or a status message.
    """
    import json
    from datetime import datetime
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
        
    try:
        budget_path = os.path.join(AGENT_DIR, "budget.json")
        expenses_path = os.path.join(AGENT_DIR, "expenses.json")
        
        # Read budget.json
        async def read_budget(session):
            return await session.call_tool("read_file", arguments={"path": budget_path})
            
        budget_res = await filesystem_toolset._execute_with_session(read_budget, "Failed to read budget.json via MCP")
        
        if getattr(budget_res, "isError", False):
            return "No budget configuration found."
            
        budget_content = budget_res.content[0].text if budget_res.content and hasattr(budget_res.content[0], "text") else "{}"
        try:
            budget_data = json.loads(budget_content)
        except Exception:
            budget_data = {}
            
        limit = budget_data.get("limit")
        period = budget_data.get("period")
        
        if limit is None or period != "daily":
            return f"No daily budget set. Current budget: {budget_data}"
            
        # Read expenses.json
        async def read_expenses(session):
            return await session.call_tool("read_file", arguments={"path": expenses_path})
            
        expenses_res = await filesystem_toolset._execute_with_session(read_expenses, "Failed to read expenses.json via MCP")
        
        if getattr(expenses_res, "isError", False):
            return "No expenses log found."
            
        expenses_content = expenses_res.content[0].text if expenses_res.content and hasattr(expenses_res.content[0], "text") else "[]"
        try:
            expenses_data = json.loads(expenses_content)
        except Exception:
            expenses_data = []
            
        # Sum daily expenses
        daily_total = 0.0
        for exp in expenses_data:
            if exp.get("date") == target_date:
                daily_total += float(exp.get("amount", 0))
                
        if daily_total > limit:
            warning = f"⚠️ BUDGET WARNING: Daily budget exceeded! Total spending of {daily_total:.2f} exceeds your daily budget limit of {limit:.2f} for {target_date}."
            return warning
            
        return f"Daily spending of {daily_total:.2f} is within the daily budget limit of {limit:.2f}."
    except Exception as e:
        return f"Error checking budget alert: {e}"


# Define log_expense tool
async def log_expense(amount: float, category: str, date: str = None) -> str:
    """Log a new expense to the database and check daily budget.

    Args:
        amount: The expense amount (number).
        category: The category of the expense (string).
        date: Optional date in YYYY-MM-DD format. Defaults to today's date.

    Returns:
        A confirmation string with details, including a budget warning if exceeded.
    """
    import json
    from datetime import datetime
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    try:
        expenses_path = os.path.join(AGENT_DIR, "expenses.json")
        
        # Read existing expenses
        async def read_expenses(session):
            return await session.call_tool("read_file", arguments={"path": expenses_path})
            
        res_read = await filesystem_toolset._execute_with_session(read_expenses, "Failed to read expenses.json via MCP")
        
        expenses_data = []
        if not getattr(res_read, "isError", False):
            content = res_read.content[0].text if res_read.content and hasattr(res_read.content[0], "text") else "[]"
            try:
                expenses_data = json.loads(content)
                if not isinstance(expenses_data, list):
                    expenses_data = []
            except Exception:
                expenses_data = []
                
        # Append new expense
        new_expense = {
            "amount": float(amount),
            "category": category.strip(),
            "date": date.strip()
        }
        expenses_data.append(new_expense)
        
        # Write back to expenses.json
        async def write_expenses(session):
            return await session.call_tool("write_file", arguments={
                "path": expenses_path,
                "content": json.dumps(expenses_data, indent=2)
            })
            
        res_write = await filesystem_toolset._execute_with_session(write_expenses, "Failed to write expenses.json via MCP")
        
        if getattr(res_write, "isError", False):
            err_msg = res_write.content[0].text if res_write.content and hasattr(res_write.content[0], "text") else str(res_write)
            raise Exception(f"Failed to write to expenses.json: {err_msg}")
            
        success_msg = f"Logged expense of {amount} in category '{category}' on {date} ✅"
        log_agent_call("finance_agent", f"log_expense(amount={amount}, category={category}, date={date})", success_msg)
        
        # Automatically call budget_alert to check if daily budget is exceeded
        alert_msg = await budget_alert(date)
        if "BUDGET WARNING" in alert_msg:
            # If exceeded, append the warning directly to the return message to alert the user immediately
            return f"{success_msg}\n{alert_msg}"
            
        return success_msg
    except Exception as e:
        err_msg = f"Error logging expense: {e}"
        log_agent_call("finance_agent", f"log_expense(amount={amount}, category={category}, date={date})", err_msg)
        return err_msg


# Define show_daily_total tool
async def show_daily_total(date: str = None) -> str:
    """Show itemized expenses and total for a target date, along with budget status.

    Args:
        date: Target date in YYYY-MM-DD format. Defaults to today's date.

    Returns:
        A formatted string listing itemized expenses, total spending, and budget status.
    """
    import json
    from datetime import datetime
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    try:
        budget_path = os.path.join(AGENT_DIR, "budget.json")
        expenses_path = os.path.join(AGENT_DIR, "expenses.json")
        
        # 1. Read expenses.json
        async def read_expenses(session):
            return await session.call_tool("read_file", arguments={"path": expenses_path})
            
        expenses_res = await filesystem_toolset._execute_with_session(read_expenses, "Failed to read expenses.json via MCP")
        
        expenses_data = []
        if not getattr(expenses_res, "isError", False):
            content = expenses_res.content[0].text if expenses_res.content and hasattr(expenses_res.content[0], "text") else "[]"
            try:
                expenses_data = json.loads(content)
            except Exception:
                expenses_data = []
                
        # 2. Filter expenses for target date
        target_expenses = [exp for exp in expenses_data if exp.get("date") == date]
        
        # Calculate daily total
        total_spending = 0.0
        itemized_lines = []
        for exp in target_expenses:
            amt = float(exp.get("amount", 0))
            cat = exp.get("category", "Uncategorized")
            total_spending += amt
            itemized_lines.append(f"- {cat}: ₹{amt:.0f}")
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        title_date = "Today's" if date == today_str else f"Expenses for {date}"
        
        output_lines = [f"📋 {title_date} Expenses:"]
        if itemized_lines:
            output_lines.extend(itemized_lines)
        else:
            output_lines.append("(No expenses logged)")
            
        output_lines.append(f"💰 Total: ₹{total_spending:.0f}")
        
        # 3. Read budget.json to check budget warning
        async def read_budget(session):
            return await session.call_tool("read_file", arguments={"path": budget_path})
            
        budget_res = await filesystem_toolset._execute_with_session(read_budget, "Failed to read budget.json via MCP")
        
        budget_data = {}
        if not getattr(budget_res, "isError", False):
            budget_content = budget_res.content[0].text if budget_res.content and hasattr(budget_res.content[0], "text") else "{}"
            try:
                budget_data = json.loads(budget_content)
            except Exception:
                budget_data = {}
                
        limit = budget_data.get("limit")
        period = budget_data.get("period")
        
        if limit is not None and period == "daily" and total_spending > limit:
            over_budget = total_spending - limit
            output_lines.append(f"⚠️ Over budget by ₹{over_budget:.0f}!")
            
        res = "\n".join(output_lines)
        log_agent_call("finance_agent", f"show_daily_total(date={date})", res)
        return res
    except Exception as e:
        err_msg = f"Error displaying daily total: {e}"
        log_agent_call("finance_agent", f"show_daily_total(date={date})", err_msg)
        return err_msg


# Define clear_expenses tool with approval gate and security comments
async def clear_expenses(confirm: str) -> str:
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
        
        async def call_write(session):
            return await session.call_tool("write_file", arguments={
                "path": expenses_path,
                "content": "[]"
            })
            
        res = await filesystem_toolset._execute_with_session(
            call_write,
            "Failed to write file via MCP"
        )
        
        if getattr(res, "isError", False):
            err_content = getattr(res, "content", [res])
            err_msg = err_content[0].text if err_content and hasattr(err_content[0], "text") else str(res)
            raise Exception(err_msg)
            
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
    model=FallbackGemini(),
    description="Agent for managing personal finances, tracking expenses, and budgeting through MCP filesystem storage.",
    instruction="""
    You are the Finance Agent for LifeOS. Your primary responsibility is to manage the user's finances and budget.
    
    You have tools from the filesystem MCP server available to you:
    - read_file: To read expenses.json and budget.json.
    - write_file: To write expenses.json and budget.json.
    
    You also have the custom tools:
    - log_expense: Log a new expense to the database. It automatically runs a budget check and warns the user if the daily budget is exceeded.
    - budget_alert: Check if total spending for a given date has exceeded the daily budget limit.
    - show_daily_total: Show itemized expenses and total for a target date, along with budget status.
    - clear_expenses: Clear all expenses from the database. Requires explicit confirmation.
    
    You must manage all finance data in `expenses.json` and `budget.json` under your directory using these filesystem MCP tools and custom tools.
    Do NOT write python code or perform direct file operations except through the provided tools.
    
    Rules for finance management:
    1. Modifying Expenses:
       - To log an expense: Always use the `log_expense` tool to save the new expense. It will automatically check the budget and warn the user if daily budget is exceeded.
       - To show daily total: Always use the `show_daily_total` tool to display an itemized list and total spending for a given date.
    2. Modifying Budget:
       - To set a budget: Save a budget configuration object with fields: limit (number), period (string: daily, weekly, or monthly) to `budget.json` using `write_file`.
       - To check budget alert: Use the `budget_alert` tool to check if the total spending for a date has exceeded the daily budget limit.
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
    tools=[log_expense, budget_alert, show_daily_total, clear_expenses, filesystem_toolset],
    before_agent_callback=make_before_callback("finance_agent"),
    after_agent_callback=make_after_callback("finance_agent")
)


