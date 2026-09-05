def build_evidence(execution_result):
    if not execution_result.get("success"):
        return {
            "rag_context": "",
            "league_context": ""
        }

    rag_context = ""
    league_context = ""

    for tool_result in execution_result["results"]:
        tool_name = tool_result["tool"]
        result = tool_result["result"]

        if not result.get("success"):
            continue

        if tool_name == "rag_search":
            rag_context = result.get("content","")

        elif tool_name == "league_context":
            league_context = result.get("content","")

    return {
        "rag_context": rag_context,
        "league_context": league_context
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
            }
        ]
    }

    evidence = build_evidence(test_execution)

    print(evidence)