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
                print(f"\n- {tool.name}")
                print(f"Description: {tool.description}")
                print(f"Schema: {tool.input_schema}")

            result = await session.call_tool(
                "get_player_depth_chart",
                arguments={
                    "player_name": "Lamar Jackson",
                    "season": 2025
                }
            )

            print("\nTOOL RESULT:")
            print(result)

            stats_result = await session.call_tool(
                "get_player_stats",
                arguments={
                    "player_name": "Lamar Jackson",
                    "season": 2025,
                    "recent_games": 3
                }
            )

            print("\nPLAYER STATS RESULT:")
            print(stats_result)

            rag_result = await session.call_tool(
                "search_fantasy_knowledge",
                arguments={
                    "query": "Are running backs or quarterbacks more valuable in fantasy football?"
                }
            )

            print("\nRAG RESULT:")
            print(rag_result)

            league_result = await session.call_tool(
                "get_my_league_context",
                arguments={}
            )

            print("\nLEAGUE CONTEXT RESULT:")
            print(league_result)


if __name__ == "__main__":
    asyncio.run(main())