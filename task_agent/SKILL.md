---
name: task_agent
description: Skills and rules for the LifeOS Task Agent to manage tasks (adding, listing pending, completing, and setting priority).
---

# Task Agent Skill

The **Task Agent** is a specialized agent in LifeOS that manages personal tasks.

## Tools

### 1. `add_task`
Adds a new task to the user's task list.
- **Parameters**:
  - `title` (string, required): The title or description of the task.
  - `priority` (string, optional): The priority of the task. Must be one of `low`, `normal`, or `high`. Defaults to `normal`.
- **Behavior**: Generates a unique task ID, appends the task with a status of `pending`, and saves the updated list to `tasks.json`.
- **Confirmation**: Returns `Done! Added [task] to your tasks ✅`.

### 2. `list_tasks`
Lists all pending/incomplete tasks.
- **Parameters**: None.
- **Behavior**: Reads `tasks.json` and filters out completed tasks.
- **Confirmation**: Returns a formatted string list of all pending tasks.

### 3. `complete_task`
Marks a task as done/complete.
- **Parameters**:
  - `task_id_or_title` (string, required): The ID (as a number/string) or case-insensitive title (exact or partial) of the task to mark as done.
- **Behavior**: Locates the task, updates its status to `done`, and saves to `tasks.json`.
- **Confirmation**: Returns `Marked [task] as complete ✅`.

### 4. `set_priority`
Sets the priority of a task.
- **Parameters**:
  - `task_id_or_title` (string, required): The ID or title of the task to update.
  - `priority` (string, required): The new priority. Must be `low`, `normal`, or `high`.
- **Behavior**: Locates the task, updates its priority to the new value, and saves to `tasks.json`.
- **Confirmation**: Returns a confirmation message including the old and new priority.

## Rules
1. **Persistent Storage**: All changes must be saved to `task_agent/tasks.json` immediately.
2. **Pending Filtering**: `list_tasks` must only display tasks that are pending (status `pending`).
3. **Fuzzy Identification**: Allow tasks to be identified by either their unique numeric ID or by their title (case-insensitive exact or partial match).
4. **Friendly Feedback**: Always include a friendly confirmation message when confirming actions to the user.
