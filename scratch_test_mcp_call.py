import asyncio
import os
import sys

# Reconfigure stdout for UTF-8 character support on Windows console
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from dotenv import load_dotenv
load_dotenv()

from finance_agent.agent import clear_expenses, filesystem_toolset

async def test():
    try:
        print("Calling clear_expenses('YES')...")
        res = await clear_expenses("YES")
        print("Result:", res)
    finally:
        await filesystem_toolset.close()

if __name__ == "__main__":
    asyncio.run(test())
