def build_evidence(execution_result):
    if not execution_result.get("success"):
        return {
            "rag_context": "",
            "league_context": "",
            "tool_context": ""
        }

    rag_context = ""
    league_context = ""
    tool_context_parts = []

    for tool_result in execution_result["results"]:
        tool_name = tool_result["tool"]
        result = tool_result["result"]

        if not result.get("success"):
            continue

        if tool_name == "rag_search":
            rag_context = result.get("content","")

        elif tool_name == "league_context":
            league_context = result.get("content","")

        elif tool_name == "player_stats":
            stats = result.get("stats", {})

            player_context = (
                f"Player: {result.get('player')}\n"
                f"Position: {result.get('position')}\n"
                f"Season: {result.get('season')}\n"
            )

            if "recent_games" in result:
                player_context += (f"Recent games: {result.get('recent_games')}\n"
                                   f"Weeks: {result.get('weeks')}\n"
                )

            if "week" in result:
                player_context += (
                f"Week: {result.get('week')}\n"
                f"Team: {result.get('team')}\n"
                f"Opponent: {result.get('opponent')}\n"
                )
            else:
                player_context += (
                f"Games: {result.get('games')}\n" #of games included in result
                )

            player_context += "Stats:\n"

            for stat_name, value in stats.items():
                player_context += f"{stat_name}: {value}\n"

            tool_context_parts.append(player_context)

    tool_context = "\n\n".join(tool_context_parts)

    return {
        "rag_context": rag_context,
        "league_context": league_context,
        "tool_context": tool_context
    }

if __name__ == "__main__":
    test_execution = {
        "success": True,
        "results": [
            {
                "tool": "rag_search",
                "result": {
                    "success": True,
                    "content": "Rushing quarterbacks gain extra fantasy value from rushing yards and touchdowns.",
                    "sources": ["quarterbacks.txt"]
                }
            },
            {
                "tool": "league_context",
                "result": {
                    "success": True,
                    "content": "League: Test League\nPassing TD: 6 points"
                }
            },
            {
                "tool": "player_stats",
                "result": {
                    "success": True,
                    "player": "Lamar Jackson",
                    "position": "QB",
                    "season": 2025,
                    "games": 13,
                    "stats": {
                        "passing_yards": 2549,
                        "passing_tds": 21,
                        "passing_interceptions": 7,
                        "carries": 67,
                        "rushing_yards": 349,
                        "rushing_tds": 2,
                        "fantasy_points": 214.86
                    }
                }
            }
        ]
    }

    evidence = build_evidence(test_execution)

    print(evidence)