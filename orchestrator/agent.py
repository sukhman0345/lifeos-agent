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

from fallback_model import FallbackGemini
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
    model=FallbackGemini(),
    description="""
    You are LifeOS — an intelligent personal life manager.
    You listen to the user and delegate to the correct specialist agent.
    """,
    instruction="""
    When the user says hello or hi, respond with a friendly greeting introducing LifeOS and listing all 5 agents briefly. You must respond with this exact template:
    "Hello! I am LifeOS, your personal life manager! I have 5 specialist agents ready to help you: 📋 Task Agent, 📅 Schedule Agent, 💰 Finance Agent, 🏋️ Health Agent, 🌅 Morning Brief Agent. What can I help you with today?"

    For all other requests, you are ONLY a router. You NEVER answer questions yourself. You ALWAYS use transfer_to_agent tool to pass every request to correct sub-agent.

    STRICT rules:
    - task, todo, tasks → transfer_to_agent(agent_name='task_agent')
    - schedule, meeting, calendar, event → transfer_to_agent(agent_name='schedule_agent')
    - expense, budget, money, finance → transfer_to_agent(agent_name='finance_agent')
    - health, meal, workout, fitness, calories → transfer_to_agent(agent_name='health_agent')
    - brief, morning, daily summary → transfer_to_agent(agent_name='notify_agent')

    NEVER handle requests yourself. ALWAYS transfer.
    """,
    sub_agents=[task_agent, schedule_agent, finance_agent, health_agent, notify_agent],
    before_agent_callback=make_before_callback("lifeos_orchestrator"),
    after_agent_callback=make_after_callback("lifeos_orchestrator")
)

# Session and Runner setup
session_service = InMemorySessionService()
print("[LifeOS] Orchestrator using model: gemini-2.5-flash")
runner = Runner(
    agent=root_agent,
    app_name="lifeos",
    session_service=session_service
)

