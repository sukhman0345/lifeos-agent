# LifeOS — AI Personal Life Manager Agent

> Your intelligent personal assistant that manages tasks, schedule, finances, and health — all in one chat.

## Problem
Managing daily life across multiple apps is fragmented and time-consuming. LifeOS brings everything into one AI-powered agent system.

## Solution
A multi-agent system built with Google ADK where one Master Orchestrator delegates to 5 specialist agents: Task, Schedule, Finance, Health, and Notify.

## Architecture
![Architecture](docs/architecture.png)

## Key Concepts Used
- Multi-agent system (ADK)
- MCP Servers (Google Calendar + File System)
- Agent Skills (SKILL.md)
- Security (human-in-the-loop + zero-trust)
- Deployed on Google Cloud Run

## Setup Instructions
Coming soon after build is complete.

## Example Prompts
- "Add buy milk to my tasks"
- "Schedule meeting tomorrow at 3pm"
- "Log ₹200 for lunch"
- "Log 30 min walk"
- "Give me my morning brief"

## Tech Stack
- Google ADK
- Antigravity IDE + CLI
- MCP Servers
- Google Cloud Run (free tier)
- Gemini model via Google AI Studio

## Built for
5-Day AI Agents: Intensive Vibe Coding Course With Google — Capstone Project