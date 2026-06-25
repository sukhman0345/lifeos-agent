import os
import sys

# Reconfigure stdout to support UTF-8 characters like emojis on Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Ensure root directory is in the Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from dotenv import load_dotenv
load_dotenv()

# Map API Key if needed
if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

from schedule_agent.agent import delete_event

print("--- Calling delete_event with partial title ---")
res = delete_event("delete Debug Test")
print("--- Result ---")
print(res)
