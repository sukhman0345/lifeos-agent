import os
import sys
import time
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure root directory is in the Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# Security & Credentials Mapping:
# Under the hood, Google's genai SDK checks for GEMINI_API_KEY for Google AI Studio calls.
# If only GOOGLE_API_KEY is defined, we map it here to prevent 401 unauthenticated errors.
if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

# Import all 5 specialist agents from their folders
from task_agent.agent import task_agent
from schedule_agent.agent import schedule_agent
from finance_agent.agent import finance_agent
from health_agent.agent import health_agent
from notify_agent.agent import notify_agent
from orchestrator.agent import root_agent as orchestrator_agent

# Initialize FastAPI App
app = FastAPI(
    title="LifeOS AI Agent Backend",
    description="Backend routing API to coordinate messages with the 5 specialist agents."
)

# Enable CORS so the local frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=False,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Define request schema
class ChatRequest(BaseModel):
    message: str
    agent_name: str

# Import ADK elements
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

# Setup in-memory session service to track conversation histories
session_service = InMemorySessionService()

# Create separate runners for each agent
task_runner = Runner(agent=task_agent, app_name="lifeos_task_agent", session_service=session_service)
schedule_runner = Runner(agent=schedule_agent, app_name="lifeos_schedule_agent", session_service=session_service)
finance_runner = Runner(agent=finance_agent, app_name="lifeos_finance_agent", session_service=session_service)
health_runner = Runner(agent=health_agent, app_name="lifeos_health_agent", session_service=session_service)
notify_runner = Runner(agent=notify_agent, app_name="lifeos_notify_agent", session_service=session_service)
orchestrator_runner = Runner(agent=orchestrator_agent, app_name="lifeos_orchestrator", session_service=session_service)


# Agent mapping lookup table
AGENT_MAPPING = {
    "orchestrator": orchestrator_agent,
    "lifeos_orchestrator": orchestrator_agent,
    "tasks": task_agent,
    "task_agent": task_agent,
    "schedule": schedule_agent,
    "schedule_agent": schedule_agent,
    "finance": finance_agent,
    "finance_agent": finance_agent,
    "health": health_agent,
    "health_agent": health_agent,
    "brief": notify_agent,
    "notify_agent": notify_agent,
}

@app.get("/{agent_folder}/SKILL.md")
async def get_skill_file(agent_folder: str):
    """
    GET /{agent_folder}/SKILL.md
    Serves the raw SKILL.md file contents for the requested agent folder.
    """
    agent_folder = agent_folder.strip()
    valid_folders = ["task_agent", "schedule_agent", "finance_agent", "health_agent", "notify_agent"]
    if agent_folder not in valid_folders:
        raise HTTPException(status_code=400, detail=f"Invalid agent folder: {agent_folder}")
        
    file_path = os.path.join(ROOT_DIR, agent_folder, "SKILL.md")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="SKILL.md not found")
        
    return FileResponse(file_path, media_type="text/markdown")

@app.get("/skill/{agent_key}")
async def get_skill(agent_key: str):
    """
    GET /skill/{agent_key}
    Reads and returns the contents of the agent's SKILL.md file.
    """
    agent_key = agent_key.lower().strip()
    
    # Map friendly names to folder names
    folder_mapping = {
        "tasks": "task_agent",
        "task_agent": "task_agent",
        "schedule": "schedule_agent",
        "schedule_agent": "schedule_agent",
        "finance": "finance_agent",
        "finance_agent": "finance_agent",
        "health": "health_agent",
        "health_agent": "health_agent",
        "brief": "notify_agent",
        "notify_agent": "notify_agent",
    }
    
    folder = folder_mapping.get(agent_key)
    if not folder:
        raise HTTPException(status_code=400, detail=f"Invalid agent key: {agent_key}")
        
    skill_file_path = os.path.join(ROOT_DIR, folder, "SKILL.md")
    
    if not os.path.exists(skill_file_path):
        raise HTTPException(status_code=404, detail=f"SKILL.md not found for agent: {agent_key}")
        
    try:
        with open(skill_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read SKILL.md: {str(e)}")

@app.get("/agent-info/{agent_name}")
async def get_agent_info(agent_name: str):
    """
    GET /agent-info/{agent_name}
    Reads the agent's SKILL.md file and returns structured JSON details.
    """
    import re
    agent_name = agent_name.lower().strip()
    
    # Map friendly names to folder names
    folder_mapping = {
        "tasks": "task_agent",
        "task_agent": "task_agent",
        "schedule": "schedule_agent",
        "schedule_agent": "schedule_agent",
        "finance": "finance_agent",
        "finance_agent": "finance_agent",
        "health": "health_agent",
        "health_agent": "health_agent",
        "brief": "notify_agent",
        "notify_agent": "notify_agent",
    }
    
    folder = folder_mapping.get(agent_name)
    if not folder:
        raise HTTPException(status_code=400, detail=f"Invalid agent name: {agent_name}")
        
    skill_file_path = os.path.join(ROOT_DIR, folder, "SKILL.md")
    if not os.path.exists(skill_file_path):
        raise HTTPException(status_code=404, detail=f"SKILL.md not found for agent: {agent_name}")
        
    try:
        with open(skill_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Split content into sections based on level-2 headers only (starts with ## )
        lines = content.split("\n")
        sections = []
        current_section = {"title": "Root", "lines": []}
        
        for line in lines:
            match = re.match(r'^(##)\s+(.*)', line)
            if match:
                sections.append(current_section)
                current_section = {"title": match.group(2).strip(), "lines": []}
            else:
                current_section["lines"].append(line)
        sections.append(current_section)
        
        who_i_am = ""
        what_i_do = []
        my_tools = []
        mcp_servers = []
        security_features = []
        
        # Extract who_i_am from the Root/First H1 section
        first_h1_found = False
        who_i_am_lines = []
        for l in lines:
            if l.strip().startswith("# "):
                first_h1_found = True
                continue
            if first_h1_found:
                if l.strip().startswith("##"):
                    break
                cleaned = l.strip()
                if cleaned:
                    if not cleaned.startswith("---"):
                        who_i_am_lines.append(cleaned)
                elif who_i_am_lines:
                    break
        who_i_am = " ".join(who_i_am_lines)
        
        # Parse mcp_servers
        content_lower = content.lower()
        if "filesystem mcp" in content_lower:
            mcp_servers.append("Filesystem MCP Server")
        if "google calendar mcp" in content_lower:
            mcp_servers.append("Google Calendar MCP Server")
            
        # Parse tools, what_i_do, security_features section by section
        for section in sections:
            title = section["title"].lower()
            sec_lines = section["lines"]
            
            # If it is an MCP tools section
            if "mcp" in title and "tools" in title:
                tool_pattern = re.compile(r'^\s*[-\*]\s+`([^`]+)`')
                for l in sec_lines:
                    l_str = l.strip()
                    m = tool_pattern.match(l_str)
                    if m:
                        t_name = m.group(1).strip()
                        if t_name not in my_tools:
                            my_tools.append(t_name)
                            
            # If it is a custom tools section (like ## Tools in health_agent and notify_agent)
            elif "tools" in title:
                custom_tool_header_pattern = re.compile(r'^###\s+\d+\.\s+`([^`]+)`')
                for idx, l in enumerate(sec_lines):
                    l_str = l.strip()
                    m_h = custom_tool_header_pattern.match(l_str)
                    if m_h:
                        t_name = m_h.group(1).strip()
                        if t_name not in my_tools:
                            my_tools.append(t_name)
                        if idx + 1 < len(sec_lines):
                            desc = sec_lines[idx+1].strip()
                            if desc and not desc.startswith("#") and not desc.startswith("-"):
                                what_i_do.append(f"{t_name}: {desc}")
                                
            if "management rules" in title or "instructions & workflow" in title or "workflow" in title:
                rule_pattern = re.compile(r'^\d+\.\s+\*\*(.*?)\*\*')
                for l in sec_lines:
                    l_str = l.strip()
                    m = rule_pattern.match(l_str)
                    if m:
                        rule_name = m.group(1).strip()
                        if rule_name.endswith(":"):
                            rule_name = rule_name[:-1].strip()
                        desc = l_str[m.end():].strip()
                        if desc.startswith(":"):
                            desc = desc[1:].strip()
                        if desc:
                            what_i_do.append(f"{rule_name}: {desc}")
                        else:
                            what_i_do.append(rule_name)
                            
            if title == "rules" or title == "general rules":
                rule_pattern = re.compile(r'^\d+\.\s+\*\*(.*?)\*\*')
                for l in sec_lines:
                    l_str = l.strip()
                    m = rule_pattern.match(l_str)
                    if m:
                        rule_name = m.group(1).strip()
                        if rule_name.endswith(":"):
                            rule_name = rule_name[:-1].strip()
                        desc = l_str[m.end():].strip()
                        if desc.startswith(":"):
                            desc = desc[1:].strip()
                        if desc:
                            security_features.append(f"{rule_name}: {desc}")
                        else:
                            security_features.append(rule_name)
                            
        return {
            "who_i_am": who_i_am,
            "what_i_do": what_i_do,
            "my_tools": my_tools,
            "mcp_servers": mcp_servers,
            "security_features": security_features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse SKILL.md: {str(e)}")

@app.get("/config")
async def get_config():
    """
    GET /config
    Returns configuration details needed by the frontend, including the mapped API key.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    return {"gemini_api_key": api_key}

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    POST /chat
    Accepts message and agent_name from the client, routes to the corresponding
    specialist agent, runs the agent execution pipeline asynchronously,
    and returns the formatted agent response.
    """
    msg_lower = request.message.lower().strip()
    
    greeting_words = ['hello', 'hi', 'hey', 'how are you', 'what can you do', 'who are you', 'help', 'what are you']
    task_keywords = ['add task', 'complete task', 'show tasks', 'list tasks', 'set priority', 'mark task', 'delete task']
    schedule_keywords = ['schedule', 'book meeting', 'add event', 'delete event', 'cancel appointment']
    finance_keywords = ['log expense', 'set budget', 'show expenses', 'clear expenses', 'how much did i spend']
    health_keywords = ['log meal', 'log workout', 'show health', 'health summary']
    notify_keywords = ['morning brief', 'daily brief', 'give me my brief']

    def match(keywords):
        return any(msg_lower == kw or msg_lower.startswith(kw) for kw in keywords)

    if match(notify_keywords):
        runner = notify_runner
        agent_key = "notify_agent"
        agent_label = "Briefing Agent"
    elif match(health_keywords):
        runner = health_runner
        agent_key = "health_agent"
        agent_label = "Health Agent"
    elif match(schedule_keywords):
        runner = schedule_runner
        agent_key = "schedule_agent"
        agent_label = "Schedule Agent"
    elif match(finance_keywords):
        runner = finance_runner
        agent_key = "finance_agent"
        agent_label = "Finance Agent"
    elif match(task_keywords):
        runner = task_runner
        agent_key = "task_agent"
        agent_label = "Task Agent"
    else:
        runner = orchestrator_runner
        agent_key = "orchestrator"
        agent_label = "Orchestrator"


    friendly_names = {
        "orchestrator": "Orchestrator",
        "tasks": "Task Agent",
        "task_agent": "Task Agent",
        "schedule": "Schedule Agent",
        "schedule_agent": "Schedule Agent",
        "finance": "Finance Agent",
        "finance_agent": "Finance Agent",
        "health": "Health Agent",
        "health_agent": "Health Agent",
        "brief": "Briefing Agent",
        "notify_agent": "Briefing Agent"
    }
    
    # Define session variables (isolating sessions by agent)
    user_id = "default_user"
    session_id = f"session_{agent_key}"
    app_name = runner.app_name
    
    try:
        # Retrieve or create session
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if not session:
            session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
            
        # Format the user message to ADK types.Content
        content = types.Content(parts=[types.Part.from_text(text=request.message)])
        
        # Run agent asynchronously
        max_attempts = 4  # Initial attempt + 3 retries
        for attempt in range(max_attempts):
            try:
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content
                ):
                    pass
                break
            except Exception as e:
                code = getattr(e, 'code', None)
                if code is None:
                    err_str = str(e).lower()
                    if "503" in err_str:
                        code = 503
                
                if code == 503 and attempt < max_attempts - 1:
                    print(f"Got 503 error. Retrying request in 5 seconds (attempt {attempt + 1}/3)...")
                    await asyncio.sleep(5)
                    continue
                
                import traceback
                print("ERROR: Agent runner run_async failed:")
                traceback.print_exc()
                tb_str = traceback.format_exc()
                detailed_error = f"⚠️ **Agent Runner Execution Error:** {str(e)}\n\n```\n{tb_str}\n```"
                return {"response": detailed_error, "handled_by": friendly_names.get(agent_key, "Orchestrator")}
            
        # Retrieve updated session containing final response
        updated_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        
        response_text = ""
        if updated_session and updated_session.events:
            # Look backwards for the latest text response from the agent
            for ev in reversed(updated_session.events):
                if ev.content and ev.content.parts:
                    parts_txt = [p.text for p in ev.content.parts if p.text]
                    if parts_txt:
                        response_text = " ".join(parts_txt)
                        break
        
        # Fallback if no text event parts were found
        if not response_text:
            response_text = "I completed the action but did not yield a written response."
            
        handled_by = agent_label
        if agent_key == "orchestrator":
            if updated_session and updated_session.events:
                for ev in reversed(updated_session.events):
                    ev_agent = getattr(ev, "agent_name", None)
                    if ev_agent and ev_agent.lower() != "lifeos_orchestrator":
                        clean_ev_agent = ev_agent.lower().strip()
                        if clean_ev_agent in friendly_names:
                            handled_by = friendly_names[clean_ev_agent]
                            break
                        for k, friendly in friendly_names.items():
                            if k in clean_ev_agent:
                                handled_by = friendly
                                break
                        if handled_by != "Orchestrator":
                            break
                            
            # Multi-layer fallback keyword search in response text
            if handled_by == "Orchestrator" and response_text:
                text_lower = response_text.lower()
                if "task agent" in text_lower or "tasks agent" in text_lower:
                    handled_by = "Task Agent"
                elif "schedule agent" in text_lower:
                    handled_by = "Schedule Agent"
                elif "finance agent" in text_lower:
                    handled_by = "Finance Agent"
                elif "health agent" in text_lower:
                    handled_by = "Health Agent"
                elif "briefing agent" in text_lower or "morning brief" in text_lower:
                    handled_by = "Briefing Agent"
            
        return {"response": response_text, "handled_by": handled_by}
        
    except Exception as e:
        # Log stacktrace for server-side debugging
        import traceback
        print("ERROR: Chat endpoint session or general setup failed:")
        traceback.print_exc()
        tb_str = traceback.format_exc()
        detailed_error = f"⚠️ **System Setup Error:** {str(e)}\n\n```\n{tb_str}\n```"
        return {"response": detailed_error, "handled_by": agent_label}

if __name__ == "__main__":
    import uvicorn
    # Start the backend server on port 8080
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
