# Load environment variables from the .env file
from dotenv import load_dotenv
load_dotenv()

import os
import json
from datetime import date
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

# Define path to health.json and subdirectory
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
HEALTH_FILE = os.path.join(AGENT_DIR, "health.json")

# Instantiate filesystem MCP server mapped to the health agent directory
filesystem_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    )
)

def _read_health() -> list:
    """Read health records from the health.json file."""
    if not os.path.exists(HEALTH_FILE):
        return []
    try:
        with open(HEALTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("records", [])
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _write_health(data: list) -> None:
    """Write health records to the health.json file."""
    try:
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump({"records": data}, f, indent=2)
    except Exception as e:
        print(f"Error writing health data: {e}")

def log_meal(name: str, calories: int) -> str:
    """Log a meal with its name and estimated calorie count.

    Args:
        name: The name or description of the meal (e.g. 'chicken salad').
        calories: The calorie count of the meal.

    Returns:
        A confirmation message indicating the meal was logged.
    """
    name = name.strip()
    today_str = date.today().strftime("%Y-%m-%d")
    
    records = _read_health()
    new_record = {
        "type": "meal",
        "name": name,
        "calories": calories,
        "date": today_str
    }
    records.append(new_record)
    _write_health(records)
    
    return f"Logged {name} ({calories} kcal) ✅"

def log_workout(workout_type: str, duration: int) -> str:
    """Log a physical workout with its type and duration in minutes.

    Args:
        workout_type: The type of physical exercise (e.g. 'run', 'swimming').
        duration: The duration of the workout in minutes.

    Returns:
        A confirmation message indicating the workout was logged.
    """
    workout_type = workout_type.strip()
    today_str = date.today().strftime("%Y-%m-%d")
    
    records = _read_health()
    new_record = {
        "type": "workout",
        "workout_type": workout_type,
        "duration": duration,
        "date": today_str
    }
    records.append(new_record)
    _write_health(records)
    
    return f"Logged {duration} min {workout_type} ✅"

def show_health_summary() -> str:
    """Read and show today's logged meals and workouts from the health records.

    Returns:
        A formatted summary of today's health data, or a message indicating there are none.
    """
    records = _read_health()
    today_str = date.today().strftime("%Y-%m-%d")
    
    today_records = [r for r in records if r.get("date") == today_str]
    
    if not today_records:
        return f"No health records logged for today ({today_str})! 🎉"
        
    meals = [r for r in today_records if r.get("type") == "meal"]
    workouts = [r for r in today_records if r.get("type") == "workout"]
    
    summary = f"Health Summary for today ({today_str}):\n"
    
    summary += "\nMeals:\n"
    if meals:
        total_calories = sum(m.get("calories", 0) for m in meals)
        for m in meals:
            summary += f"- {m['name']} ({m['calories']} kcal)\n"
        summary += f"Total Caloric Intake: {total_calories} kcal\n"
    else:
        summary += "- No meals logged today.\n"
        
    summary += "\nWorkouts:\n"
    if workouts:
        total_duration = sum(w.get("duration", 0) for w in workouts)
        for w in workouts:
            summary += f"- {w['workout_type']} ({w['duration']} minutes)\n"
        summary += f"Total Active Time: {total_duration} minutes\n"
    else:
        summary += "- No workouts logged today.\n"
        
    return summary.strip()

def get_health_data() -> str:
    """Return the raw JSON health data for integration with other agents (like the Notify Agent).

    Returns:
        A JSON string containing the raw list of all health records.
    """
    records = _read_health()
    return json.dumps(records)

# Create the Health Agent
health_agent = Agent(
    name="health_agent",
    model="gemini-2.0-flash",
    description="Agent for tracking health parameters, logging meals/calories and workouts/durations.",
    instruction="""
    You are the Health Agent for LifeOS. Your primary responsibility is to manage the user's health logs.
    
    You have 4 custom tools:
    - log_meal: Log a meal name and calories.
    - log_workout: Log a workout type and duration (in minutes).
    - show_health_summary: Display today's meals and workouts.
    - get_health_data: Retrieve raw health records (useful for notify/briefing agent).
    
    You also have access to the filesystem MCP server tools (read_file, write_file) to inspect files in your directory.
    
    Follow these rules:
    1. Whenever you perform an action using a tool, make sure the tool successfully returns a confirmation, and pass that confirmation back to the user.
    2. Save all health data to health.json immediately.
    3. Be polite, clear, and structured in your responses.
    """,
    tools=[log_meal, log_workout, show_health_summary, get_health_data, filesystem_toolset]
)
