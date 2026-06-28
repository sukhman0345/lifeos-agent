import os
import json
import asyncio
import sys

# Ensure root directory is in the Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from main import chat, ChatRequest

async def run():
    sys.stdout.reconfigure(encoding='utf-8')
    schedule_agent_dir = os.path.join(ROOT_DIR, "schedule_agent")
    schedule_file = os.path.join(schedule_agent_dir, "schedule.json")
    pending_file = os.path.join(schedule_agent_dir, "pending_confirmation.json")
    
    if os.path.exists(pending_file):
        os.remove(pending_file)
        
    events = [
      {
        "title": "team meeting",
        "date": "2026-06-27",
        "time": "14:00",
        "event_id": "6oc7spc7rqa6qiq65f9jd66874"
      },
      {
        "title": "team meeting",
        "date": "2026-06-30",
        "time": "10:00",
        "event_id": "0t2nj1dhpmp6kjmvbie601erp0"
      }
    ]
    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
        
    print("--- First Request: delete team meeting ---")
    resp = await chat(ChatRequest(message="delete team meeting", agent_name="schedule"))
    print("Response:", resp)
    
    # Check if pending file exists
    if os.path.exists(pending_file):
        with open(pending_file, "r", encoding="utf-8") as f:
            print("Pending file content after first request:", f.read().strip())
    else:
        print("Pending file does not exist!")

    print("\n--- Second Request: Reply 2026-06-30 ---")
    resp2 = await chat(ChatRequest(message="2026-06-30", agent_name="schedule"))
    print("Response2:", resp2)
    
    # Check if event was deleted
    with open(schedule_file, "r", encoding="utf-8") as f:
        print("Schedule content after second request:", f.read().strip())
        
if __name__ == "__main__":
    asyncio.run(run())
