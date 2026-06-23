# Load environment variables from the .env file
from dotenv import load_dotenv
load_dotenv()

import os
import json
from datetime import date
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

# Define directories
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(AGENT_DIR)

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

# Instantiate filesystem MCP server mapped to the notify agent directory
filesystem_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    )
)

def daily_brief() -> str:
    """Read all 4 agents' databases and combine the results into one morning summary.

    Returns:
        A beautifully formatted morning brief containing pending tasks, schedule, expenses, and health data.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    
    # 1. Read Pending Tasks
    tasks_path = os.path.join(PROJECT_ROOT, "task_agent", "tasks.json")
    pending_tasks_list = []
    if os.path.exists(tasks_path):
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
                pending_tasks_list = [t for t in tasks if t.get("status") == "pending"]
        except Exception:
            pass
            
    # 2. Read Today's Schedule
    schedule_path = os.path.join(PROJECT_ROOT, "schedule_agent", "schedule.json")
    today_events = []
    if os.path.exists(schedule_path):
        try:
            with open(schedule_path, "r", encoding="utf-8") as f:
                events = json.load(f)
                today_events = [e for e in events if e.get("date") == today_str]
        except Exception:
            pass
            
    # 3. Read Today's Expenses
    expenses_path = os.path.join(PROJECT_ROOT, "finance_agent", "expenses.json")
    today_expenses = []
    if os.path.exists(expenses_path):
        try:
            with open(expenses_path, "r", encoding="utf-8") as f:
                expenses = json.load(f)
                today_expenses = [exp for exp in expenses if exp.get("date") == today_str]
        except Exception:
            pass
            
    # 4. Read Today's Health Data
    health_path = os.path.join(PROJECT_ROOT, "health_agent", "health.json")
    meals = []
    workouts = []
    if os.path.exists(health_path):
        try:
            with open(health_path, "r", encoding="utf-8") as f:
                health_data = json.load(f)
                # Handle both list and {"records": [...]} dictionary format
                records = []
                if isinstance(health_data, dict):
                    records = health_data.get("records", [])
                elif isinstance(health_data, list):
                    records = health_data
                
                today_records = [r for r in records if r.get("date") == today_str]
                meals = [r for r in today_records if r.get("type") == "meal"]
                workouts = [r for r in today_records if r.get("type") == "workout"]
        except Exception:
            pass

    # Format the Brief
    brief = f"🌅 Good morning! Here is your daily brief for {today_str}:\n"
    
    # Format Tasks
    brief += "\n📋 Pending Tasks:\n"
    if pending_tasks_list:
        for t in pending_tasks_list:
            brief += f"- [{t.get('id', ' ')}] {t.get('title')} (Priority: {t.get('priority', 'normal')})\n"
    else:
        brief += "- No pending tasks! 🎉\n"
        
    # Format Schedule
    brief += "\n📅 Today's Schedule:\n"
    if today_events:
        for e in today_events:
            brief += f"- {e.get('title')} at {e.get('time')}\n"
    else:
        brief += "- No events scheduled for today.\n"
        
    # Format Expenses
    brief += "\n💰 Today's Expenses:\n"
    if today_expenses:
        total_exp = sum(exp.get("amount", 0.0) for exp in today_expenses)
        for exp in today_expenses:
            brief += f"- {exp.get('category')}: {exp.get('amount')}\n"
        brief += f"Total Spending: {total_exp}\n"
    else:
        brief += "- No expenses logged today. Daily total: 0.\n"
        
    # Format Health
    brief += "\n🍎 Health & Fitness:\n"
    if meals or workouts:
        if meals:
            total_cal = sum(m.get("calories", 0) for m in meals)
            brief += f"- Calories Intake: {total_cal} kcal ("
            brief += ", ".join(m.get("name") for m in meals)
            brief += ")\n"
        else:
            brief += "- No meals logged today.\n"
            
        if workouts:
            total_active = sum(w.get("duration", 0) for w in workouts)
            brief += f"- Workouts: {total_active} min active time ("
            brief += ", ".join(w.get("workout_type") for w in workouts)
            brief += ")\n"
        else:
            brief += "- No workouts logged today.\n"
    else:
        brief += "- No health records logged today.\n"
        
    res = brief.strip()
    log_agent_call("notify_agent", "daily_brief", "Generated successfully")
    return res

# Create the Notify Agent
notify_agent = Agent(
    name="notify_agent",
    model=FallbackGemini(),
    description="Agent for providing daily briefs and combining status reports from other agents.",
    instruction="""
    You are the Notify Agent for LifeOS. Your primary responsibility is to provide consolidated summaries and daily briefs.
    
    You have 1 custom tool:
    - daily_brief: Consolidate task, schedule, finance, and health summaries into a morning brief.
    
    You also have access to the filesystem MCP server tools (read_file, write_file) to inspect files in your directory.
    
    Follow these rules:
    1. Whenever you perform an action using a tool, make sure the tool successfully returns a confirmation, and pass that confirmation back to the user.
    2. Be polite, clear, and structured in your responses.
    """,
    tools=[daily_brief, filesystem_toolset],
    before_agent_callback=make_before_callback("notify_agent"),
    after_agent_callback=make_after_callback("notify_agent")
)

