import polars

def get_player_directory(stats):

    players = (
        stats.select(
            "player_id",
            "player_display_name",
            "player_name",
            "position",
            "team"
        ).filter(polars.col("player_id").is_not_null()).unique(subset=["player_id"])
    )

    return players

def resolve_player(players, player_name):
    matches = players.filter(polars.col("player_display_name").str.to_lowercase() == player_name.lower())

    if matches.is_empty():
        return{
            "success": False,
            "error": f"No player found matching {player_name}."
        }

    if matches.height > 1:
        return{
            "success": False,
            "error": f"Multiple players found matching {player_name}."
        }

    row = matches.row(0, named=True) #Again, changing it to a dictionary rather than a tuple

    return {
        "success": True,
        "player_id": row["player_id"],
        "player_name": row["player_display_name"],
        "position": row["position"],
        "team": row["team"] #May have to rework later on if a player plays for multiple teams in a season.
    }

if __name__ == "__main__":
    from ingestion.stats import load_cached_player_stats

    stats = load_cached_player_stats(2025)

    players = get_player_directory(stats)

    print(resolve_player(players, "Lamar Jackson"))
    print(resolve_player(players, "lamar jackson"))
    print(resolve_player(players, "Fake Person"))