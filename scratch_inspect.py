import asyncio
import os
import sys

# Ensure root directory is in the Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

from orchestrator.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="lifeos_test",
        session_service=session_service
    )
    
    user_id = "test_user"
    session_id = "test_session"
    app_name = "lifeos_test"
    
    content = types.Content(parts=[types.Part.from_text(text="add buy milk to my tasks")])
    
    await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    print("Running agent...")
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content
    ):
        print(f"Event received: {type(event)}")
        
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    print("\n--- Inspecting Session ---")
    print(f"Session events count: {len(session.events)}")
    for i, ev in enumerate(session.events):
        print(f"\nEvent {i}: {type(ev)}")
        print(f"ev.content: {ev.content}")
        print(f"ev.call_info: {getattr(ev, 'call_info', None)}")
        print(f"ev.agent_name: {getattr(ev, 'agent_name', None)}")
        # Check all attributes
        print("Attributes:", dir(ev))

if __name__ == "__main__":
    asyncio.run(main())
