---
name: schedule_agent
description: Skills and rules for the LifeOS Schedule Agent to manage real Google Calendar events using MCP toolsets, and backup to schedule.json using the filesystem MCP toolset.
---

# Schedule Agent Skill (MCP Integrated)

The **Schedule Agent** is a specialized agent in LifeOS that manages personal schedules, meetings, and events. It integrates with real-world calendars via Google Calendar MCP and backs up schedule logs using Filesystem MCP.

## MCP Servers and Tools

### 1. Google Calendar MCP Server (`@modelcontextprotocol/server-google-calendar`)
This toolset allows the agent to interact directly with the user's real Google Calendar.
- **Key Tools**:
  - `create_event`: Creates a new calendar event (accepts summary, description, start time, end time, etc.).
  - `list_events`: Lists calendar events within a specified timeframe.
  - `delete_event`: Deletes a calendar event.
  - `update_event`: Modifies an existing calendar event.
  - `quick_add_event`: Instantly adds a calendar event using a natural language query.

### 2. Filesystem MCP Server (`@modelcontextprotocol/server-filesystem`)
This toolset allows the agent to access the agent's subdirectory for database backups.
- **Key Tools**:
  - `read_file`: Reads the contents of `schedule.json` locally.
  - `write_file`: Overwrites `schedule.json` with the updated list of events.
  - `get_file_info`: Inspects metadata of files.

## Instructions & Workflow
1. **Primary Database**: Google Calendar is the source of truth. All scheduling operations must hit the Google Calendar API via the calendar MCP tools.
2. **Local Backup**: After any write or delete operation on the Google Calendar, the agent must update `schedule_agent/schedule.json` using the filesystem MCP tools to reflect the same state.
   - Use `read_file` to read the existing list of backup events.
   - Use `write_file` to write the updated list.
3. **Synchronization**: When listing events, check both sources to confirm they are synchronized.

## Rules
1. **Zero Data Loss**: Always back up calendar events to the local `schedule.json` file immediately.
2. **Real-world execution**: Confirm every scheduling operation with the user clearly and politely.
3. **Date/Time Formatting**: Ensure proper timezone handling and ISO strings when scheduling events via the Google Calendar API.
