from ingestion.stats import get_player_stats

TOOL_NAME = "player_stats"

TOOL_DESCRIPTION = (
    "Get real NFL statistics for a specific player. "
    "Use this for questions about a player's performance, passing, rushing, "
    "receiving, targets, carries, fantasy points, or statistics from a "
    "specific season or week."
)

def player_stats(player_name, season, week=None, recent_games=None):
    stats = get_player_stats(
        player_name,
        season,
        week
    )

    if stats.is_empty():
        return{
            "success": False,
            "error": f"No stats found for {player_name}"
        }

    if week is not None:
        row = stats.row(0, named=True) #("Lamar Jackson", 3, 288, 3, ...) -> proper dictionary

        return {
                "success": True,
                "player": row["player_display_name"],
                "position": row["position"],
                "team": row["team"],
                "opponent": row["opponent_team"],
                "season": row["season"],
                "week": row["week"],
                "stats": {
                    "passing_yards": row["passing_yards"],
                    "passing_tds": row["passing_tds"],
                    "interceptions": row["passing_interceptions"],
                    "carries": row["carries"],
                    "rushing_yards": row["rushing_yards"],
                    "rushing_tds": row["rushing_tds"],
                    "targets": row["targets"],
                    "receptions": row["receptions"],
                    "receiving_yards": row["receiving_yards"],
                    "receiving_tds": row["receiving_tds"],
                    "fantasy_points": row["fantasy_points"],
                    "fantasy_points_ppr": row["fantasy_points_ppr"]
                }
            }

    if recent_games is not None:
        stats = stats.sort("week", descending=True).head(recent_games).sort("week") 

    totals = stats.select(
        "passing_yards",
        "passing_tds",
        "passing_interceptions",
        "carries",
        "rushing_yards",
        "rushing_tds",
        "targets",
        "receptions",
        "receiving_yards",
        "receiving_tds",
        "fantasy_points",
        "fantasy_points_ppr"
    ).sum() #Sums their total stats together

    totals = totals.row(
        0,
        named=True
    )

    totals["fantasy_points"] = round(totals["fantasy_points"],2)

    totals["fantasy_points_ppr"] = round(totals["fantasy_points_ppr"],2)

    first_row = stats.row(
        0,
        named=True
    )

    result = {
        "success": True,
        "player": first_row["player_display_name"],
        "position": first_row["position"],
        "season": first_row["season"],
        "games": stats.height,
        "stats": totals
    }

    if recent_games is not None:
        result["recent_games"] = recent_games
        result["weeks"] = stats["week"].to_list()

    return result

if __name__ == "__main__":
    result = player_stats(
        "Lamar Jackson",
        2025,
        recent_games=3
    )

    print(result)