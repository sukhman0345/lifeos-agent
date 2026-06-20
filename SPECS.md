# LifeOS Agent — Gherkin Specifications

## Task Agent

GIVEN user says "add [task] to my tasks"
WHEN Task Agent receives the message
THEN save task to tasks.json
AND reply "Done! Added [task] to your tasks ✅"

GIVEN user says "show my tasks"
WHEN Task Agent receives the message
THEN read tasks.json
AND reply with full task list

GIVEN user says "complete [task]"
WHEN Task Agent receives the message
THEN mark task as done in tasks.json
AND reply "Marked [task] as complete ✅"

---

## Schedule Agent

GIVEN user says "schedule [event] on [date] at [time]"
WHEN Schedule Agent receives the message
THEN save event to schedule.json
AND reply "Scheduled [event] on [date] at [time] ✅"

GIVEN user says "what is my schedule today"
WHEN Schedule Agent receives the message
THEN read today's events from schedule.json
AND reply with full list

---

## Finance Agent

GIVEN user says "log [amount] for [category]"
WHEN Finance Agent receives the message
THEN save expense to expenses.json
AND reply with updated daily total

GIVEN user says "show my expenses today"
WHEN Finance Agent receives the message
THEN read today's expenses from expenses.json
AND reply with itemised list and total

GIVEN user says "clear all expenses"
WHEN Finance Agent receives the message
THEN PAUSE and ask "Are you sure? Type YES to confirm"
AND only clear if user replies YES

---

## Health Agent

GIVEN user says "log [meal]"
WHEN Health Agent receives the message
THEN save meal to health.json
AND reply "Logged [meal] ✅"

GIVEN user says "log [duration] [workout]"
WHEN Health Agent receives the message
THEN save workout to health.json
AND reply "Logged [duration] [workout] ✅"

GIVEN user says "show health summary"
WHEN Health Agent receives the message
THEN read health.json
AND reply with today's meals and workouts

---

## Notify Agent

GIVEN user says "give me my morning brief"
WHEN Notify Agent receives the message
THEN call Task Agent for pending tasks
AND call Schedule Agent for today's events
AND call Finance Agent for daily total
AND call Health Agent for health summary
AND combine all results into one reply