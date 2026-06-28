---
name: task_agent
description: Skills and rules for the LifeOS Task Agent to manage tasks (adding, listing pending, completing, and setting priority) via Filesystem MCP tools.
---

# Task Agent Skill (MCP Integrated)

The **Task Agent** is a specialized agent in LifeOS that manages personal tasks. It interacts with the filesystem using the Filesystem MCP server tools instead of direct direct Python file operations.

## MCP Tools
The agent is equipped with the Filesystem MCP Server toolset:
- `read_file`: Used to read task list data from `tasks.json`.
- `write_file`: Used to overwrite `tasks.json` with the updated list of tasks.
- `get_file_info`: Used to inspect file metadata.

## Task Management Rules
1. **Adding a Task**:
   - Read the existing list from `tasks.json` using `read_file`.
   - Generate a new unique ID (max existing ID + 1).
   - Create a task object: `{"id": id, "title": title, "status": "pending", "priority": priority}`.
   - Save the updated array to `tasks.json` using `write_file`.
   - Confirm to the user: `Done! Added [task] to your tasks ✅`.
2. **Listing Pending Tasks**:
   - Read the list from `tasks.json` using `read_file`.
   - Filter and display only the tasks where `"status": "pending"`.
3. **Completing a Task**:
   - Read the list from `tasks.json` using `read_file`.
   - Locate the target task by numeric ID or title (case-insensitive exact/partial match).
   - Update its status to `"done"`.
   - Save the updated array using `write_file`.
   - Confirm to the user: `Marked [task] as complete ✅`.
4. **Setting Priority**:
   - Read the list from `tasks.json` using `read_file`.
   - Locate the target task.
   - Update its priority to `low`, `normal`, or `high`.
   - Save using `write_file`.
5. **Deleting a Task**:
   - Locate the target task by numeric ID or title (case-insensitive exact/partial match).
   - Remove the task from the task list.
   - Save the updated array to `tasks.json`.
   - Confirm to the user: `Deleted task '[task]' ✅`.
6. **Clearing All Tasks**:
   - Ask the user: "Are you sure you want to delete all tasks? Type YES to confirm."
   - Only execute the `clear_all_tasks` tool if they confirm with "YES" in the next turn.

## General Rules
1. **Persistent Storage**: All changes must be saved to `task_agent/tasks.json` immediately.
2. **Fuzzy Identification**: Allow tasks to be identified by either their unique numeric ID or by their title (case-insensitive exact or partial match).
3. **Friendly Feedback**: Always include a friendly confirmation message when confirming actions to the user.
4. **Human-in-the-Loop**: Enforce strict textual YES confirmation for the `clear_all_tasks` operation.

