import os
import sys
from fastapi import FastAPI, HTTPException
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
    allow_credentials=True,
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

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    POST /chat
    Accepts message and agent_name from the client, routes to the corresponding
    specialist agent, runs the agent execution pipeline asynchronously,
    and returns the formatted agent response.
    """
    agent_key = request.agent_name.lower().strip()
    
    # Resolve the agent
    agent = AGENT_MAPPING.get(agent_key)
    if not agent:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{request.agent_name}' not found. Available options: {list(AGENT_MAPPING.keys())}"
        )
    
    # Define session variables (isolating sessions by agent)
    user_id = "default_user"
    session_id = f"session_{agent_key}"
    app_name = f"lifeos_{agent_key}"
    
    try:
        # Retrieve or create session
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if not session:
            session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
            
        # Instantiate Runner
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service
        )
        
        # Format the user message to ADK types.Content
        content = types.Content(parts=[types.Part.from_text(text=request.message)])
        
        # Run agent asynchronously
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            pass
            
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
            
        return {"response": response_text}
        
    except Exception as e:
        # Log stacktrace for server-side debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal agent execution error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Start the backend server on port 8080
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
