---
name: health_agent
description: Skills and rules for the LifeOS Health Agent to track meals, workouts, calorie count, workout duration, and summary.
---

# Health Agent Skill

The **Health Agent** is a specialized agent in LifeOS that tracks physical health, caloric intake, and workouts.

## Tools

### 1. `log_meal`
Logs a meal with its name and estimated calories.
- **Parameters**:
  - `name` (string, required): The name or description of the meal.
  - `calories` (integer, required): The calorie count of the meal.
- **Behavior**: Saves the meal record to `health.json`.
- **Confirmation**: Returns `Logged [name] ([calories] kcal) ✅`.

### 2. `log_workout`
Logs physical exercise with its type and duration in minutes.
- **Parameters**:
  - `workout_type` (string, required): The type of workout (e.g. `run`, `swim`, `walk`).
  - `duration` (integer, required): The duration of the workout in minutes.
- **Behavior**: Saves the workout record to `health.json`.
- **Confirmation**: Returns `Logged [duration] min [workout_type] ✅`.

### 3. `show_health_summary`
Reads `health.json` and shows today's meals and workouts.
- **Parameters**: None.
- **Behavior**: Filters `health.json` for records logged on today's date, presenting totals for active time and calorie intake.
- **Confirmation**: Returns a formatted text summary of today's health logs.

### 4. `get_health_data`
Returns raw health records as a JSON string for integration with other agents (such as Notify Agent).
- **Parameters**: None.
- **Behavior**: Reads all records from `health.json` and returns the raw string.

## MCP Tools
The agent also includes the Filesystem MCP Server toolset:
- `read_file`: Reads files under the `health_agent` directory.
- `write_file`: Writes/overwrites files under the `health_agent` directory.
- `get_file_info`: Used to inspect file metadata.

## Rules
1. **Persistent Storage**: All changes must be saved to `health_agent/health.json` immediately.
2. **Date Format**: Ensure proper date tracking (formatted as `YYYY-MM-DD`) for all records.
3. **Friendly Feedback**: Always include a friendly confirmation message when confirming actions to the user.
