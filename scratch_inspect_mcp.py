import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

AGENT_DIR = os.path.join(ROOT_DIR, "finance_agent")

filesystem_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    )
)

print("filesystem_toolset attributes and methods:")
print(dir(filesystem_toolset))
print("\nType of filesystem_toolset:", type(filesystem_toolset))
