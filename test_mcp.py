import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.server"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            tools = await session.list_tools()

            print("\nAVAILABLE TOOLS:")
            for tool in tools.tools:
                print(f"- {tool.name}")

            result = await session.call_tool(
                "get_player_depth_chart",
                arguments={
                    "player_name": "Lamar Jackson",
                    "season": 2025
                }
            )

            print("\nTOOL RESULT:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())