
"""Expose verified weekly roster records to the fantasy agent."""

from nfl_data.roster import get_player_roster

TOOL_NAME = "player_roster"

TOOL_DESCRIPTION = (
    "Look up an NFL player's latest recorded team, roster status, "
    "and position for a season. Use for current team membership, "
    "roster assignments, signings, releases, or possible team changes. "
    "Roster records alone do not establish why a player changed teams. "
    "Do not use this tool for historical statistics or depth-chart rank."
)


def player_roster(player_name, season):
    try:
        return get_player_roster(player_name, season)
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as exc:
        return {
            "success": False,
            "error": f"Roster data unavailable: {exc}",
        }
