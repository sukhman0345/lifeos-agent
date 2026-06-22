---
name: finance_agent
description: Skills and rules for the LifeOS Finance Agent to manage expenses and budgets (logging, showing total, setting budget, and checking alerts) via Filesystem MCP tools.
---

# Finance Agent Skill (MCP Integrated)

The **Finance Agent** is a specialized agent in LifeOS that manages personal finances. It interacts with storage databases using the Filesystem MCP server tools instead of direct Python file operations.

## MCP Tools
The agent is equipped with the Filesystem MCP Server toolset:
- `read_file`: Used to read expenses and budget configurations from `expenses.json` and `budget.json`.
- `write_file`: Used to save data by overwriting `expenses.json` and `budget.json`.
- `get_file_info`: Used to inspect file metadata.

## Finance Management Rules
1. **Logging an Expense**:
   - Read `expenses.json` using `read_file`.
   - Append the new expense object: `{"amount": amount, "category": category, "date": date}`.
   - Save the updated list using `write_file`.
   - Perform a proactive budget check.
2. **Showing Daily Total**:
   - Read `expenses.json` using `read_file`.
   - Sum the expenses for the target date and present an itemized list and total.
3. **Setting Budget**:
   - Save a budget configuration object: `{"limit": limit, "period": period}` to `budget.json` using `write_file`.
4. **Checking Budget Alerts**:
   - Read `budget.json` and `expenses.json` using `read_file`.
   - Sum the spending for the specified period and alert the user if it exceeds the limit.
5. **Clearing All Expenses**:
   - Enforce Human-in-the-Loop (HITL) confirmation.
   - When requested to clear expenses, ask the user: "Are you sure? Type YES to confirm."
   - Do NOT clear the file or call `clear_expenses` in the same turn.
   - Only call `clear_expenses` with `confirm="YES"` if the user explicitly replies with "YES" (case-insensitive) in the next turn.
   - Never use `write_file` to clear `expenses.json` directly.

## General Rules
1. **Persistent Storage**: All changes must be saved to `expenses.json` and `budget.json` immediately.
2. **Proactive Check**: Perform a budget alert check whenever the user logs an expense or requests their spending summary.
3. **Friendly Feedback**: Always include a friendly confirmation message when confirming actions to the user.
4. **Human-in-the-Loop**: Enforce strict textual YES confirmation for the `clear_expenses` operation.
