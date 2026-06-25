import asyncio
import os
import sys
import json

# Reconfigure stdout for UTF-8 support on Windows console
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from dotenv import load_dotenv
load_dotenv()

from finance_agent.agent import log_expense, show_daily_total, clear_expenses, filesystem_toolset

async def test():
    try:
        # 1. Setup: write a daily budget to budget.json
        budget_path = os.path.join(ROOT_DIR, "finance_agent", "budget.json")
        print("Setting daily budget limit to 1000.0...")
        with open(budget_path, "w", encoding="utf-8") as f:
            json.dump({"limit": 1000.0, "period": "daily"}, f)
            
        # 2. Clear current expenses first to have a clean slate
        print("Clearing expenses...")
        await clear_expenses("YES")
        
        # 3. Log the three sample expenses
        print("Logging lunch: 500...")
        await log_expense(500.0, "lunch", "2026-06-25")
        print("Logging coffee: 300...")
        await log_expense(300.0, "coffee", "2026-06-25")
        print("Logging shopping: 400...")
        await log_expense(400.0, "shopping", "2026-06-25")
        
        # 4. Display today's daily total and check formatting
        print("\n--- Displaying Daily Total ---")
        res = await show_daily_total("2026-06-25")
        print(res)
        
    finally:
        await filesystem_toolset.close()

if __name__ == "__main__":
    asyncio.run(test())
