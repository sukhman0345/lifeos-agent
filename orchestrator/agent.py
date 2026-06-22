from dotenv import load_dotenv
load_dotenv()

import sys
import os
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Ensure the root project directory is in the python path for module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import task_agent
from task_agent.agent import task_agent
from schedule_agent.agent import schedule_agent
from finance_agent.agent import finance_agent

# Placeholder sub-agents for health, and notify to be fully implemented later.
# This prevents import/run errors while satisfying delegation requirements.

health_agent = Agent(
    name="health_agent",
    description="Specialist agent for managing health, meals, workouts, and fitness.",
    instruction="Handle health-related requests (meals, workouts, fitness). Confirm you are health_agent."
)

notify_agent = Agent(
    name="notify_agent",
    description="Specialist agent for providing daily briefs or summaries.",
    instruction="Provide a combined daily brief or summary by gathering information. Confirm you are notify_agent."
)

# Master Orchestrator — delegates to sub-agents based on user input
root_agent = Agent(
    name="lifeos_orchestrator",
    model="gemini-2.5-flash",
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
)

# Session and Runner setup
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="lifeos",
    session_service=session_service
)
