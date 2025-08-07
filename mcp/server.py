from fastmcp import FastMCP
from tools import initialize_tools
import logging
import asyncio


async def main():
    # run server async
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    mcp = FastMCP("vision mcp server", port = "8006")
    await initialize_tools(mcp) # set up tools
    await mcp.run_async(transport='stdio')


if __name__ == "__main__":
    print("Starting MCP server on port")
    asyncio.run(main())
    

# command to run: mcpo --port 8002 -- python server.py

