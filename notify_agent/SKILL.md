---
name: notify_agent
description: Skills and rules for the LifeOS Notify Agent to generate morning briefings and combine daily statuses.
---

# Notify Agent Skill

The **Notify Agent** is a specialized agent in LifeOS that consolidates notifications, updates, and statuses into a daily morning briefing.

## Tools

### 1. `daily_brief`
Reads data from all 5 agents in the LifeOS ecosystem (Orchestrator, Task, Schedule, Finance, Health) and generates a combined daily morning briefing.
- **Parameters**: None.
- **Behavior**: Reads files `tasks.json`, `schedule.json`, `expenses.json`, and `health.json` from other agents' subdirectories. It filters and formats:
  - Pending tasks (Task Agent)
  - Today's schedule events (Schedule Agent)
  - Daily spending total (Finance Agent)
  - Daily meals and workout logs (Health Agent)
- **Confirmation**: Returns a beautifully structured, comprehensive text summary of the user's day.

## MCP Tools
The agent also includes the Filesystem MCP Server toolset:
- `read_file`: Reads files under the `notify_agent` directory.
- `write_file`: Writes/overwrites files under the `notify_agent` directory.
- `get_file_info`: Used to inspect file metadata.

## Rules
1. **Source of Truth**: Consolidate information directly from other agents' JSON databases to ensure accuracy.
2. **Dynamic Date Filtering**: Correctly filter events, spending, and health logs to display only records matching today's date (`YYYY-MM-DD`).
3. **Friendly Presentation**: Present the brief with helpful emojis and clear headings.
