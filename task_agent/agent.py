from dotenv import load_dotenv
load_dotenv()

import os
import json
import sys
import datetime
from google.adk.agents import Agent

# Define path to task_agent directory
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(AGENT_DIR, "tasks.json")

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
from security.telemetry import log_agent_call, make_before_callback, make_after_callback

def _read_tasks() -> list:
    """Read tasks from the tasks.json file."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _write_tasks(tasks: list) -> None:
    """Write tasks to the tasks.json file."""
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        print(f"Error writing tasks: {e}")

def add_task(title: str, priority: str = "normal") -> str:
    """Add a new task to the task list.

    Args:
        title: The description or title of the task.
        priority: The priority of the task. Must be one of: 'low', 'normal', 'high'. Default is 'normal'.

    Returns:
        A confirmation message indicating the task was added.
    """
    priority = priority.strip().lower()
    if priority not in ("low", "normal", "high"):
        priority = "normal"
        
    tasks = _read_tasks()
    
    # Check for duplicates case-insensitively
    for task in tasks:
        if task.get("title", "").strip().lower() == title.strip().lower():
            res = "Task already exists!"
            log_agent_call("task_agent", f"add_task(title={title}, priority={priority})", res)
            return res
            
    # Generate unique ID
    new_id = 1
    if tasks:
        new_id = max(task.get("id", 0) for task in tasks) + 1
        
    new_task = {
        "id": new_id,
        "title": title,
        "status": "pending",
        "priority": priority,
        "date": datetime.date.today().strftime("%Y-%m-%d")
    }
    
    tasks.append(new_task)
    _write_tasks(tasks)
    
    res = f"Done! Added {title} to your tasks ✅"
    log_agent_call("task_agent", f"add_task(title={title}, priority={priority})", res)
    return res

def list_tasks() -> str:
    """List all tasks (both pending and completed).

    Returns:
        A formatted string listing all tasks, or a message indicating there are none.
    """
    tasks = _read_tasks()
    if not tasks:
        res = "You have no tasks! 🎉"
        log_agent_call("task_agent", "list_tasks", res)
        return res
        
    result = "Here is the list of all tasks:\n"
    for task in tasks:
        status_emoji = "⏳" if task.get("status") == "pending" else "✅"
        task_date = task.get("date") or datetime.date.today().strftime("%Y-%m-%d")
        result += f"- [{task['id']}] {task['title']} (Priority: {task['priority']}) [{task.get('status', 'pending')}] {status_emoji} Added: {task_date}\n"
    res = result.strip()
    log_agent_call("task_agent", "list_tasks", res)
    return res

def complete_task(task_id_or_title: str) -> str:
    """Mark a task as complete/done.

    Args:
        task_id_or_title: The ID (as a number or string) or the exact/partial title of the task to complete.

    Returns:
        A confirmation message indicating the task was marked as complete, or an error if not found.
    """
    tasks = _read_tasks()
    found_task = None
    
    # Try parsing as ID first
    try:
        target_id = int(task_id_or_title)
        for task in tasks:
            if task.get("id") == target_id:
                found_task = task
                break
    except ValueError:
        pass
        
    # If not found by ID, try exact title match (case-insensitive)
    if not found_task:
        for task in tasks:
            if task.get("title").strip().lower() == task_id_or_title.strip().lower():
                found_task = task
                break
                
    # If still not found, try partial match among pending tasks
    if not found_task:
        for task in tasks:
            if task_id_or_title.strip().lower() in task.get("title").lower():
                found_task = task
                break
                
    if not found_task:
        res = f"Error: Could not find any task matching '{task_id_or_title}'."
        log_agent_call("task_agent", f"complete_task(task_id_or_title={task_id_or_title})", res)
        return res
        
    found_task["status"] = "done"
    _write_tasks(tasks)
    
    res = f"Marked {found_task['title']} as complete ✅"
    log_agent_call("task_agent", f"complete_task(task_id_or_title={task_id_or_title})", res)
    return res

def set_priority(task_id_or_title: str, priority: str) -> str:
    """Set the priority of a task to low, normal, or high.

    Args:
        task_id_or_title: The ID or title of the task to update.
        priority: The new priority. Must be 'low', 'normal', or 'high'.

    Returns:
        A confirmation message indicating the priority was updated, or an error if not found.
    """
    priority = priority.strip().lower()
    if priority not in ("low", "normal", "high"):
        res = "Error: Priority must be 'low', 'normal', or 'high'."
        log_agent_call("task_agent", f"set_priority(task_id_or_title={task_id_or_title}, priority={priority})", res)
        return res
        
    tasks = _read_tasks()
    found_task = None
    
    # Try parsing as ID
    try:
        target_id = int(task_id_or_title)
        for task in tasks:
            if task.get("id") == target_id:
                found_task = task
                break
    except ValueError:
        pass
        
    # Try exact title match
    if not found_task:
        for task in tasks:
            if task.get("title").strip().lower() == task_id_or_title.strip().lower():
                found_task = task
                break
                
    # Try partial title match
    if not found_task:
        for task in tasks:
            if task_id_or_title.strip().lower() in task.get("title").lower():
                found_task = task
                break
                
    if not found_task:
        res = f"Error: Could not find any task matching '{task_id_or_title}'."
        log_agent_call("task_agent", f"set_priority(task_id_or_title={task_id_or_title}, priority={priority})", res)
        return res
        
    old_priority = found_task.get("priority", "normal")
    found_task["priority"] = priority
    _write_tasks(tasks)
    
    res = f"Updated priority of '{found_task['title']}' from '{old_priority}' to '{priority}' ✅"
    log_agent_call("task_agent", f"set_priority(task_id_or_title={task_id_or_title}, priority={priority})", res)
    return res

# Create the Task Agent
task_agent = Agent(
    name="task_agent",
    model=FallbackGemini(),
    description="Agent for managing personal tasks. It can add tasks, list all tasks, complete tasks, and set task priorities.",
    instruction="""
    You are the Task Agent for LifeOS. Your primary responsibility is to manage the user's tasks.
    
    You have 4 tools available:
    - add_task: Add a new task (optionally with a priority).
    - list_tasks: Show all tasks (both pending and completed).
    - complete_task: Mark a task as done.
    - set_priority: Set task priority to low, normal, or high.
    
    Follow these rules:
    1. Whenever you perform an action using a tool, make sure the tool successfully returns a confirmation, and pass that confirmation back to the user.
    2. Save all task data to tasks.json.
    3. List all tasks (both pending and completed) when asked to list or show tasks.
    4. Be polite, clear, and structured in your responses.
    """,
    tools=[add_task, list_tasks, complete_task, set_priority],
    before_agent_callback=make_before_callback("task_agent"),
    after_agent_callback=make_after_callback("task_agent")
)
