import os
import json
from google.adk.agents import Agent

# Define path to tasks.json
TASKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")

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
    
    # Generate unique ID
    new_id = 1
    if tasks:
        new_id = max(task.get("id", 0) for task in tasks) + 1
        
    new_task = {
        "id": new_id,
        "title": title,
        "status": "pending",
        "priority": priority
    }
    
    tasks.append(new_task)
    _write_tasks(tasks)
    
    return f"Done! Added {title} to your tasks ✅"

def list_tasks() -> str:
    """List all pending (incomplete) tasks.

    Returns:
        A formatted string listing all pending tasks, or a message indicating there are none.
    """
    tasks = _read_tasks()
    pending = [task for task in tasks if task.get("status") == "pending"]
    
    if not pending:
        return "You have no pending tasks! 🎉"
        
    result = "Here are your pending tasks:\n"
    for task in pending:
        result += f"- [{task['id']}] {task['title']} (Priority: {task['priority']})\n"
    return result

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
        return f"Error: Could not find any task matching '{task_id_or_title}'."
        
    found_task["status"] = "done"
    _write_tasks(tasks)
    
    return f"Marked {found_task['title']} as complete ✅"

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
        return "Error: Priority must be 'low', 'normal', or 'high'."
        
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
        return f"Error: Could not find any task matching '{task_id_or_title}'."
        
    old_priority = found_task.get("priority", "normal")
    found_task["priority"] = priority
    _write_tasks(tasks)
    
    return f"Updated priority of '{found_task['title']}' from '{old_priority}' to '{priority}' ✅"

# Create the Task Agent
task_agent = Agent(
    name="task_agent",
    description="Agent for managing personal tasks. It can add tasks, list pending tasks, complete tasks, and set task priorities.",
    instruction="""
    You are the Task Agent for LifeOS. Your primary responsibility is to manage the user's tasks.
    
    You have 4 tools available:
    - add_task: Add a new task (optionally with a priority).
    - list_tasks: Show all pending tasks.
    - complete_task: Mark a task as done.
    - set_priority: Set task priority to low, normal, or high.
    
    Follow these rules:
    1. Whenever you perform an action using a tool, make sure the tool successfully returns a confirmation, and pass that confirmation back to the user.
    2. Save all task data to tasks.json.
    3. List only pending tasks when asked to list or show tasks.
    4. Be polite, clear, and structured in your responses.
    """,
    tools=[add_task, list_tasks, complete_task, set_priority]
)
