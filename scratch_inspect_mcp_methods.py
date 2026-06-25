import asyncio
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

AGENT_DIR = os.path.join(ROOT_DIR, "finance_agent")

async def test():
    filesystem_toolset = McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
        )
    )
    
    tools = await filesystem_toolset.get_tools()
    print("Tools returned by get_tools():", tools)
    print("Types of tools:", [type(t) for t in tools])
    for t in tools:
        print(f"\nTool: {t.name}")
        print("Attributes:", dir(t))
        # Let's see if it's a function or object
        if hasattr(t, "__call__"):
            print("Is callable: Yes")
        else:
            print("Is callable: No")
            
    await filesystem_toolset.close()

if __name__ == "__main__":
    asyncio.run(test())
