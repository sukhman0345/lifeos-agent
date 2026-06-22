from dotenv import load_dotenv
load_dotenv()

import sys
import os
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Define path to orchestrator directory
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

# Ensure the root project directory is in the python path for module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.telemetry import make_before_callback, make_after_callback

# Import task_agent
from task_agent.agent import task_agent
from schedule_agent.agent import schedule_agent
from finance_agent.agent import finance_agent

from health_agent.agent import health_agent
from notify_agent.agent import notify_agent

# Master Orchestrator — delegates to sub-agents based on user input
root_agent = Agent(
    name="lifeos_orchestrator",
    model="gemini-2.0-flash",
    description="""
    You are LifeOS — an intelligent personal life manager.
    You listen to the user and delegate to the correct specialist agent.
    """,
    instruction="""
    You are LifeOS — an intelligent personal life manager.
    You listen to the user and delegate to the correct specialist agent.
    
    Delegation rules:
    - Tasks (add, list, complete, priority) → task_agent
    - Schedule (meetings, events, reminders) → schedule_agent
    - Finance (expenses, budget, spending) → finance_agent
    - Health (meals, workouts, fitness) → health_agent
    - Daily brief or summary → notify_agent
    
    Important rules:
    1. ALWAYS confirm to the user which agent you are calling (e.g., "I'm calling the Task Agent to check your tasks..." or "I will pass this to the Health Agent to log your workout...").
    2. Always reply in a friendly, helpful, and polite tone.
    """,
    sub_agents=[task_agent, schedule_agent, finance_agent, health_agent, notify_agent],
    before_agent_callback=make_before_callback("lifeos_orchestrator"),
    after_agent_callback=make_after_callback("lifeos_orchestrator")
)

# Session and Runner setup
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="lifeos",
    session_service=session_service
)

