from league.context import build_league_context

TOOL_NAME = "league_context"

TOOL_DESCRIPTION = (
    "Get authoritative information about the user's specific fantasy league. "
    "Use this for questions about 'my league' or 'this league', scoring rules, "
    "points per touchdown, points per reception, scoring format, roster settings, "
    "and league-specific player or position value."
)

def get_league_context(league):
    return {
        "success": True,
        "content": build_league_context(league)
    }