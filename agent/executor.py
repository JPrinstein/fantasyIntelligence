from tools.rag_tool import rag_search
from tools.league_tool import get_league_context
from tools.player_stats import player_stats

def execute_plan(plan, chunks, index, league):
    results = []

    # loop through plan["tools"]
    for tool_call in plan["tools"]:
        tool_name = tool_call["tool"]
        args = tool_call["args"]

        if tool_name == "rag_search":
            result = rag_search(
                args["query"],
                chunks,
                index
            )

        elif tool_name == "league_context":
            result = get_league_context(league)

        elif tool_name == "player_stats":
            week = args.get("week")

            result = player_stats(args["player_name"], args["season"], week)

        results.append({
            "tool": tool_name,
            "result": result
        })

    return {
        "success": True,
        "results": results
    }

if __name__ == "__main__":
    from rag.vector_store import load_index
    from rag.storage import load_chunks
    from league.loader import load_league

    chunks = load_chunks("rag_data/chunks.json")
    index = load_index("rag_data/index.faiss")
    league = load_league()

    test_plan = {
        "tools": [
            {
                "tool": "player_stats",
                "args": {
                    "player_name": "Lamar Jackson",
                    "season": 2025,
                    "week": 3
                }
            }
        ]
    }

    result = execute_plan(
        test_plan,
        chunks,
        index,
        league
    )

    print(result)