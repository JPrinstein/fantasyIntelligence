from ingestion.depth_charts import load_cached_depth_charts, get_player_depth_chart
from ingestion.stats import load_cached_player_stats
from ingestion.players import get_player_directory, resolve_player

TOOL_NAME = "player_depth_chart"

TOOL_DESCRIPTION = (
    "Get the latest available NFL depth chart information for a specific player. "
    "Use this for questions about a player's team, depth chart position, role, "
    "or where they currently rank at their position."
)

def player_depth_chart(player_name, season):
    stats = load_cached_player_stats(season)

    players = get_player_directory(stats)

    player = resolve_player(players, player_name)

    if not player["success"]:
        return player

    depth_charts = load_cached_depth_charts(season)

    player_rows = get_player_depth_chart(
        depth_charts,
        player["player_id"]
    )

    if player_rows.is_empty():
        return{
            "success": False,
            "error": f"No depth chart data found for {player_name}"
        }

    row = player_rows.row(0, named=True)

    return {
        "success": True,
        "player": row["player_name"],
        "player_id": row["gsis_id"],
        "season": season,
        "team": row["team"],
        "position": row["pos_abb"],
        "position_name": row["pos_name"],
        "position_rank": row["pos_rank"],
        "snapshot": row["dt"]
    }

if __name__ == "__main__":
    print(
        player_depth_chart(
            "Lamar Jackson",
            2025
        )
    )