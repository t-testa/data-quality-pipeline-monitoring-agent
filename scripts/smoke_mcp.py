"""Exercise real stdio initialization and tools against the running local API."""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dqagent.settings import Settings


async def main():
    env = dict(os.environ)
    env["DQ_MCP_TOKEN"] = Settings().api_token.get_secret_value()
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "dqagent.mcp_server"], env=env)
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listing = await session.list_tools()
        assert len(listing.tools) == 9
        result = await session.call_tool("list_pipelines", {})
        assert not result.isError
        assert "demo-success" in str(result)
        invalid = await session.call_tool("get_pipeline_run", {"run_id": "invalid"})
        assert invalid.isError
        print(
            "MCP stdio smoke passed: initialize, nine tools, authenticated evidence, invalid input rejected"
        )


if __name__ == "__main__":
    asyncio.run(main())
