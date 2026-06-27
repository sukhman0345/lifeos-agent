---
name: lifeos_orchestrator
description: Skills and guidelines for the LifeOS Master Orchestrator agent to coordinate specialist sub-agents, handle greetings, and manage zero-trust execution.
---

# Master Orchestrator Skill

This document details the configuration and behaviors of the LifeOS Master Orchestrator agent.

## Identity & Role
- **Who I am**: Master Orchestrator for LifeOS (configured in [orchestrator/agent.py](file:///D:/capstone_project/lifeos-agent/orchestrator/agent.py))
- **What I do**: Route user requests to the correct specialist sub-agent and handle general conversation or system-level coordination.

## Management & Routing
- **Sub-agents I manage**:
  - `task_agent` ([task_agent/agent.py](file:///D:/capstone_project/lifeos-agent/task_agent/agent.py))
  - `schedule_agent` ([schedule_agent/agent.py](file:///D:/capstone_project/lifeos-agent/schedule_agent/agent.py))
  - `finance_agent` ([finance_agent/agent.py](file:///D:/capstone_project/lifeos-agent/finance_agent/agent.py))
  - `health_agent` ([health_agent/agent.py](file:///D:/capstone_project/lifeos-agent/health_agent/agent.py))
  - `notify_agent` ([notify_agent/agent.py](file:///D:/capstone_project/lifeos-agent/notify_agent/agent.py))
- **Routing rules**:
  - `tasks` / `todo` / `task` → transfers to `task_agent`
  - `schedule` / `meeting` / `calendar` / `event` → transfers to `schedule_agent`
  - `finance` / `expense` / `budget` / `money` → transfers to `finance_agent`
  - `health` / `meal` / `workout` / `fitness` / `calories` → transfers to `health_agent`
  - `brief` / `morning` / `daily summary` → transfers to `notify_agent`

## Self-Handled Operations
- **What I handle myself**:
  - Greetings (exact template message welcoming the user and introducing the 5 specialist agents)
  - General questions
  - Help requests

## Security & Observability
- **Security**: Strict zero-trust verification (detects and blocks UNC paths, external databases like `DATABASE_URL`, or remote storage targets) to keep personal data local.
- **Observability**: OpenTelemetry-based logging integrated through `before_agent_callback` and `after_agent_callback` telemetry handlers (defined in [security/telemetry.py](file:///D:/capstone_project/lifeos-agent/security/telemetry.py)).

## Infrastructure
- **Model**: `gemini-2.5-flash` with fallback to `gemini-2.5-flash-lite` (implemented in [fallback_model.py](file:///D:/capstone_project/lifeos-agent/fallback_model.py)).
