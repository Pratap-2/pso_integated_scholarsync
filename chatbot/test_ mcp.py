import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession


async def main():

    server = StdioServerParameters(
        command="python",
        args=["chatbot/mcp_server.py"]
    )

    async with stdio_client(server) as (read, write):

        session = ClientSession(read, write)

        await session.initialize()

        print("Connected to MCP server")

        result = await session.call_tool(
            "calculator",
            {"expression": "3*6"}
        )

        print("Result:", result)


asyncio.run(main())