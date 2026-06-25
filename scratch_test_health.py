import os
import sys
from datetime import date

# Reconfigure stdout for UTF-8 support on Windows console
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from dotenv import load_dotenv
load_dotenv()

from health_agent.agent import log_meal, log_workout, show_health_summary

def test():
    # Clear health file or overwrite using direct file I/O for test setup
    from health_agent.agent import HEALTH_FILE
    import json
    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump({"records": []}, f)
        
    print("Logging meal and workout synchronously...")
    res_meal = log_meal("sandwich", 600)
    print("Meal Result:", res_meal)
    
    res_workout = log_workout("jogging", 45)
    print("Workout Result:", res_workout)
    
    print("\n--- Displaying Summary ---")
    summary = show_health_summary()
    print(summary)

if __name__ == "__main__":
    test()
