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
    
    res = f"Logged {name} ({calories} kcal) ✅"
    log_agent_call("health_agent", f"log_meal(name={name}, calories={calories})", res)
    return res

def log_workout(workout_type: str, duration: int) -> str:
    """Log a physical workout with its type and duration in minutes.

    Args:
        workout_type: The type of physical exercise (e.g. 'run', 'swimming').
        duration: The duration of the workout in minutes.

    Returns:
        A confirmation message indicating the workout was logged.
    """
    workout_type = workout_type.strip()
    
    # Robustly convert/extract duration to integer
    try:
        duration_val = int(duration)
    except (ValueError, TypeError):
        import re
        match = re.search(r'\d+', str(duration))
        duration_val = int(match.group()) if match else 0
        
    today_str = date.today().strftime("%Y-%m-%d")
    
    records = _read_health()
    new_record = {
        "type": "workout",
        "workout_type": workout_type,
        "duration": duration_val,
        "date": today_str
    }
    records.append(new_record)
    _write_health(records)
    
    res = f"Logged {duration_val} min {workout_type} ✅"
    log_agent_call("health_agent", f"log_workout(type={workout_type}, duration={duration_val})", res)
    return res

def show_health_summary() -> str:
    """Read and show today's logged meals and workouts along with health insights.

    Returns:
        A formatted summary of today's health data and insights.
    """
    records = _read_health()
    today_str = date.today().strftime("%Y-%m-%d")
    
    today_records = [r for r in records if r.get("date") == today_str]
    
    meals = [r for r in today_records if r.get("type") == "meal"]
    workouts = [r for r in today_records if r.get("type") == "workout"]
    
    total_calories = sum(m.get("calories", 0) for m in meals)
    total_duration = sum(w.get("duration", 0) for w in workouts)
    
    summary_lines = [f"🌿 Health Summary for Today ({today_str}) 🌿", ""]
    
    # Meals section
    summary_lines.append("🍽️ Today's Meals:")
    if meals:
        for m in meals:
            summary_lines.append(f"- {m['name']} ({m['calories']} kcal)")
        summary_lines.append(f"🔥 Total Caloric Intake: {total_calories} kcal")
    else:
        summary_lines.append("- No meals logged today.")
        summary_lines.append("🔥 Total Caloric Intake: 0 kcal")
    summary_lines.append("")
    
    # Workouts section
    summary_lines.append("💪 Today's Workouts:")
    if workouts:
        for w in workouts:
            summary_lines.append(f"- {w['workout_type']} ({w['duration']} minutes)")
        summary_lines.append(f"⏱️ Total Active Time: {total_duration} minutes")
    else:
        summary_lines.append("- No workouts logged today.")
        summary_lines.append("⏱️ Total Active Time: 0 minutes")
    summary_lines.append("")
    
    # 1. Calorie analysis
    if total_calories < 1500:
        cal_insight = "eat more"
    elif total_calories <= 2500:
        cal_insight = "good"
    else:
        cal_insight = "reduce intake"
        
    # 2. Workout analysis
    if total_duration < 30:
        workout_insight = "exercise more today"
    elif total_duration <= 60:
        workout_insight = "good job"
    else:
        workout_insight = "excellent workout!"
        
    summary_lines.append("📊 Health Analysis:")
    summary_lines.append(f"• Calorie Status: {cal_insight}")
    summary_lines.append(f"• Workout Status: {workout_insight}")
    summary_lines.append("")
    
    # 3. Health tip of the day
    if total_duration > 60:
        tip = "Since you had an intense workout, make sure to stretch and consume enough protein to help your muscles recover! 🏋️‍♂️"
    elif total_duration < 30:
        tip = "Try taking a short 10-15 minute walk after your next meal. It's a great way to boost digestion and metabolism! 🚶‍♂️"
    elif total_calories > 2500:
        tip = "Consider swapping high-calorie snacks for fresh fruits or raw almonds to manage your daily intake. 🍎"
    else:
        tip = "Consistency is key! Keep up this fantastic balance of nutrition and physical activity. 🌟"
        
    summary_lines.append(f"💡 Health Tip of the Day:")
    summary_lines.append(tip)
    summary_lines.append("")
    
    # 4. Water reminder
    summary_lines.append("💧 Remember to drink 8 glasses of water today!")
    summary_lines.append("")
    
    # 5. Overall health score out of 10
    score = 5
    # Calorie score adjustment
    if 1500 <= total_calories <= 2500:
        score += 2
    elif total_calories < 1000 or total_calories > 3000:
        score -= 1
        
    # Workout score adjustment
    if total_duration >= 60:
        score += 3
    elif total_duration >= 30:
        score += 2
    elif total_duration == 0:
        score -= 1
        
    # Keep score bound between 1 and 10
    score = max(1, min(10, score))
    
    # Generate score description
    if score >= 8:
        score_desc = "Amazing! You are doing outstanding! 🏆"
    elif score >= 6:
        score_desc = "Good effort! Keep progressing! 🌟"
    else:
        score_desc = "Let's put in some more focus tomorrow! You've got this! 👍"
        
    summary_lines.append(f"🎯 Overall Health Score: {score}/10")
    summary_lines.append(score_desc)
    
    res = "\n".join(summary_lines)
    log_agent_call("health_agent", "show_health_summary", res)
    return res

def get_health_data() -> str:
    """Return the raw JSON health data for integration with other agents (like the Notify Agent).

    Returns:
        A JSON string containing the raw list of all health records.
    """
    records = _read_health()
    res = json.dumps(records)
    log_agent_call("health_agent", "get_health_data", f"Returned {len(records)} records")
    return res

# Create the Health Agent
health_agent = Agent(
    name="health_agent",
    model=FallbackGemini(),
    description="Agent for tracking health parameters, logging meals/calories and workouts/durations.",
    instruction="""
    You are the Health Agent for LifeOS. Your primary responsibility is to manage the user's health logs.
    
    You have 4 custom tools:
    - log_meal: Log a meal name and calories.
    - log_workout: Log a workout type and duration (in minutes).
    - show_health_summary: Display today's meals and workouts.
    - get_health_data: Retrieve raw health records (useful for notify/briefing agent).
    
    Do NOT write python code or perform direct file operations. All database operations must be done via your tools.
    
    Follow these rules:
    1. Single-Message Workout Logging:
       - If the user provides a workout log request in a single message (e.g., "log 30 min jogging", "jogging for 30 minutes", etc.), you MUST parse both the workout type (e.g., "jogging") and the duration (e.g., 30) from the message and call `log_workout` immediately in a single turn without asking any follow-up questions.
    2. Incomplete Logs:
       - If the user specifies a duration but no workout type (e.g. "log 30 min"), ask them for the workout type.
       - Once they reply with the workout type, immediately call `log_workout` using the previously provided duration and the new workout type.
       - Similarly, if they specify the workout type but no duration, ask for the duration and immediately call `log_workout` once provided.
    3. Save all health data to health.json immediately.
    4. Pass Tool Responses Verbatim:
       - After calling show_health_summary tool, always return the EXACT text returned by the tool to the user. Do not summarize or modify it. Return it word for word.
       - Pass any tool confirmation messages (like from log_workout or log_meal) back to the user verbatim.
    5. Be polite, clear, and structured in your responses.
    """,
    tools=[log_meal, log_workout, show_health_summary, get_health_data],
    before_agent_callback=make_before_callback("health_agent"),
    after_agent_callback=make_after_callback("health_agent")
)


