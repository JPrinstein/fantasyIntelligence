from league.context import build_league_context

TOOL_NAME = "league_context"

TOOL_DESCRIPTION = (
    "Get authoritative league-specific information including "
    "scoring rules, scoring format, and roster settings."
)

def get_league_context(league):
    return {
        "success": True,
        "content": build_league_context(league)
    }