import json
import re
import nflreadpy

from llm.runtime import generate_chat
from tools.rag_tool import TOOL_NAME as RAG_TOOL_NAME
from tools.rag_tool import TOOL_DESCRIPTION as RAG_TOOL_DESCRIPTION
from tools.league_tool import TOOL_NAME as LEAGUE_TOOL_NAME
from tools.league_tool import TOOL_DESCRIPTION as LEAGUE_TOOL_DESCRIPTION
from tools.player_stats import TOOL_NAME as PLAYER_STATS_TOOL_NAME
from tools.player_stats import TOOL_DESCRIPTION as PLAYER_STATS_TOOL_DESCRIPTION
from agent.validator import validate_plan
from tools.player_depth_chart import TOOL_NAME as PLAYER_DEPTH_CHART_TOOL_NAME
from tools.player_depth_chart import TOOL_DESCRIPTION as PLAYER_DEPTH_CHART_TOOL_DESCRIPTION

AVAILABLE_TOOLS = {
    LEAGUE_TOOL_NAME:{
        "description": LEAGUE_TOOL_DESCRIPTION,
        "arguments":{}
    },

    RAG_TOOL_NAME: {
        "description": RAG_TOOL_DESCRIPTION,
        "arguments": {
            "query": {
                "description": "The search query to use for the knowledge base.",
                "required": True,
                "type": str
            }
        }
    },
    PLAYER_STATS_TOOL_NAME: {
        "description": PLAYER_STATS_TOOL_DESCRIPTION,
        "arguments": {
            "player_name": {
                "description": "The player's full name.",
                "required": True,
                "type": str
            },
            "season": {
                "description": "The NFL season as a four-digit year.",
                "required": True,
                "type": int,
                "min": 1999,
                "max": 2100
            },
            "week": {
                "description": "Optional NFL week number for weekly stats.",
                "required": False,
                "type": int,
                "min": 1,
                "max": 22
            },
            "recent_games":{
                "description": "Optional number of most recent games to include.",
                "required": False,
                "type": int,
                "min": 1,
                "max": 18
            }
        }
    },
    PLAYER_DEPTH_CHART_TOOL_NAME: {
        "description": PLAYER_DEPTH_CHART_TOOL_DESCRIPTION,
        "arguments": {
            "player_name": {
                "description": "The player's full name.",
                "required": True,
                "type": str
            },
            "season": {
                "description": "The NFL season associated with the depth chart data.",
                "required": True,
                "type": int,
                "min": 1999,
                "max": 2100
            }
        }
    }
}

def build_tools_prompt():
    lines = []

    for tool_name, tool_info in AVAILABLE_TOOLS.items():

        lines.append(f"Tool: {tool_name}")
        lines.append(f"Description: {tool_info["description"]}")

        arguments = tool_info["arguments"]

        if arguments:
            lines.append("Arguments:")

            for argument_name, argument_info in arguments.items():
                required_text = (
                    "required" if argument_info.get("required", True) else "optional"
                )

                argument_type = argument_info.get("type")

                type_names = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean"
                }

                type_text = type_names.get(argument_type, "unknown")

                lines.append(
                    f"- {argument_name} ({type_text}, {required_text}): "
                    f"{argument_info['description']}"
                )

        else:
            lines.append("Arguments: none")

        lines.append("")

    return "\n".join(lines)

def create_plan(question):
    tools_prompt = build_tools_prompt()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a tool planner for a fantasy football assistant. "
                "Your only job is to choose which available tools are needed. "
                "Do not answer the fantasy football question yourself. "

                "TOOL RULES: "

                "Use rag_search ONLY for general fantasy football knowledge, strategy, "
                "terminology, concepts, or position information. "

                "Any question containing phrases such as 'my league', 'in my league', "
                "'this league', 'our league', 'my scoring', or 'my roster' MUST use "
                "league_context. This rule is mandatory even if rag_search is also needed. "

                "If the question can be answered entirely from league settings, use "
                "league_context and DO NOT use rag_search. "

                "If the question asks for general fantasy football reasoning AND refers "
                "to the user's specific league, use BOTH rag_search and league_context. "

                "If the question asks WHY or HOW a fantasy concept, player type, or position is valuable, "
                "use rag_search for the general explanation. "
                "If the question also refers to the user's league, use BOTH rag_search and league_context. "

                "Use player_stats for questions asking about a specific NFL player's actual "
                "performance or statistics for a season or week. "
                "Do not use rag_search when player_stats directly provides the requested facts. "

                "Never invent optional tool arguments. "
                "Only supply week when the user requests a specific NFL week. "
                "Only supply recent_games when the user explicitly requests "
                "a specific number of recent games. "
                "If the user asks for season statistics without specifying a "
                "week or number of games, provide only player_name and season. "
                "Never silently replace season statistics with recent-game statistics. "

                "Use player_depth_chart for questions asking about a specific player's "
                "team, depth chart position, depth chart rank, or current role. "
                "An NFL season may have depth chart snapshots dated in the following calendar year. "
                "When depth chart evidence provides an NFL season, treat that season field as "
                "authoritative. Snapshot timestamps are metadata only and may fall in the "
                "following calendar year. Never reject or reclassify depth chart evidence "
                "because the snapshot timestamp's calendar year differs from the NFL season."

                "EXAMPLES: "
                "'What does PPR mean?' -> rag_search only. "
                "'Is this a PPR league?' -> league_context only. "
                "'How many points is a passing touchdown in my league?' -> league_context only. "
                "'Why are rushing quarterbacks valuable?' -> rag_search only. "
                "'Why are rushing quarterbacks valuable in my league?' -> rag_search and league_context. "
                "'How did Lamar Jackson perform in 2025?' -> player_stats only. "
                "'How many passing yards did Lamar Jackson have in Week 3 of 2025?' -> player_stats only. "
                "How has Lamar Jackson performed over his last 3 games in 2025? → player_stats with recent_games=3"
                "'Where is Lamar Jackson on the depth chart in 2025?' -> player_depth_chart only. "
                "'Is Lamar Jackson the starting quarterback in 2025?' -> player_depth_chart only. "

                "Return only valid JSON. Do not include markdown, commentary, or explanation. "
                "Use the exact argument types specified in the tool definitions. "
                "Do not convert integers into strings. "
            )
        },
        {
            "role": "user",
            "content": f"""
            AVAILABLE TOOLS:

            {tools_prompt}

            QUESTION:
            {question}

            Return JSON in exactly this structure:

            {{
                "tools": [
                    {{
                        "tool": "tool_name",
                        "args": {{}}
                    }}
                ]
            }}
            """
        }
    ]

    response = generate_chat(messages, json_mode=True, max_tokens=300)

    print("\nRAW PLANNER RESPONSE:")
    print(repr(response))

    try:
        plan = json.loads(response)
    except json.JSONDecodeError:
        return{
            "tools": [],
            "error": "Planner returned invalid JSON",
            "raw_response": response
        }

    return plan


def enforce_required_tools(question, plan):
    if not isinstance(plan.get("tools"), list):
        return plan

    question_lower = question.lower()
    selected_tools = {
        call.get("tool")
        for call in plan["tools"]
        if isinstance(call, dict)
    }

    league_phrases = (
        "my league", "in my league", "this league",
        "our league", "my scoring", "my roster",
        "our scoring", "our roster",
        "our scoring settings",
        "my league settings", "our league settings",
    )

    if (
        any(phrase in question_lower for phrase in league_phrases)
        and "league_context" not in selected_tools
    ):
        plan["tools"].append({
            "tool": "league_context",
            "args": {},
        })

    # Explicit years take priority over "current" wording.
    explicit_year = re.search(r"\b(?:19|20)\d{2}\b", question_lower)

    current_phrases = (
        "current", "currently", "right now", "today",
        "this season", "this year", "latest",
    )

    is_current_request = (
        explicit_year is None
        and any(
            re.search(r"\b" + re.escape(term) + r"\b", question_lower)
            for term in current_phrases
        )
    )

    if is_current_request:
        season = int(nflreadpy.get_current_season())

        for call in plan["tools"]:
            if not isinstance(call, dict):
                continue

            if call.get("tool") not in {
                "player_stats",
                "player_depth_chart",
            }:
                continue

            args = call.get("args")

            if isinstance(args, dict):
                args["season"] = season

    return plan


if __name__ == "__main__":
    test_plans = [
        "hello",

        {},

        {
            "tools": "rag_search"
        },

        {
            "tools": [
                "hello"
            ]
        },

        {
            "tools": [
                {
                    "args": {}
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "fake_tool",
                    "args": {}
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "rag_search",
                    "args": {}
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "league_context",
                    "args": {
                        "banana": 123
                    }
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "rag_search",
                    "args": {
                        "query": "What does PPR mean?"
                    }
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "player_stats",
                    "args": {
                        "player_name": "Lamar Jackson",
                        "season": 2025
                    }
                }
            ]
        },

        {
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
        },

        {
            "tools": [
                {
                    "tool": "player_stats",
                    "args": {
                        "player_name": "Lamar Jackson"
                    }
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "player_stats",
                    "args": {
                        "player_name": "Lamar Jackson",
                        "season": 2025,
                        "banana": 123
                    }
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "player_stats",
                    "args": {
                        "player_name": "Lamar Jackson",
                        "season": "2025"
                    }
                }
            ]
        },

        {
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
        },

        {
            "tools": [
                {
                    "tool": "player_stats",
                    "args": {
                        "player_name": "Lamar Jackson",
                        "season": 2025,
                        "week": 500
                    }
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "player_stats",
                    "args": {
                        "player_name": "Lamar Jackson",
                        "season": -500,
                        "week": 3
                    }
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "player_stats",
                    "args": {
                        "player_name": "Lamar Jackson",
                        "season": "banana",
                        "week": 3
                    }
                }
            ]
        },
    ]


    for plan in test_plans:
        print(plan)
        print(validate_plan(plan, AVAILABLE_TOOLS))
        print()

