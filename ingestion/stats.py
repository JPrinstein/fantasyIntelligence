from pathlib import Path
import nflreadpy as nfl
import polars
from ingestion.players import resolve_player, get_player_directory

RAW_DATA_DIR = Path("data/raw/player_stats")

def load_cached_player_stats(season):
    path = RAW_DATA_DIR / f"player_stats_{season}.parquet"

    return polars.read_parquet(path)

def load_player_stats(season):
    stats = nfl.load_player_stats(seasons=[season]) #nflreadypy expects a list as an input

    return stats

def save_player_stats(stats, season):
    RAW_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = RAW_DATA_DIR / f"player_stats_{season}.parquet"

    stats.write_parquet(path)

    return path

def get_player_rows(stats, player_name): #Gets player data on a week to week basis
    return stats.filter(
        polars.col("player_display_name").str.to_lowercase() == player_name.lower()
    )

def get_player_stats(player_name, season, week=None): #Can either get the full season stats or a specific week
    stats = load_cached_player_stats(season)

    players = get_player_directory(stats)

    player = resolve_player(players, player_name)

    if not player["success"]:
        return polars.DataFrame()

    player_rows = stats.filter(polars.col("player_id") == player["player_id"])

    if week is not None:
        player_rows = player_rows.filter(polars.col("week") == week)

    return player_rows

if __name__ == "__main__":
    season = 2025

    stats = load_cached_player_stats(season)

    player_stats = get_player_rows(
        stats,
        "Lamar Jackson"
    )

    print(player_stats)