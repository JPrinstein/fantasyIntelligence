
"""Player roster lookup from verified weekly NFL snapshots."""

from pathlib import Path

import polars as pl

from nfl_data.readers import read_dataset


REQUIRED_ROSTER_COLUMNS = {
    "season",
    "week",
    "gsis_id",
    "full_name",
    "team",
    "position",
    "status",
}


def get_player_roster(player_name, season, *, root=None):
    """Return a player's latest available weekly roster record."""
    if not isinstance(player_name, str) or not player_name.strip():
        raise ValueError("A player name is required.")

    season = int(season)

    # We deliberately provide no legacy fallback for weekly rosters.
    # If no verified snapshot exists, the lookup reports missing data.
    legacy_path = Path("__no_legacy_weekly_roster_cache__")

    frame, metadata = read_dataset(
        "rosters_weekly",
        season,
        legacy_path,
        REQUIRED_ROSTER_COLUMNS,
        root=root,
        with_metadata=True,
    )

    matches = frame.filter(
        pl.col("full_name")
        .str.to_lowercase()
        == player_name.strip().lower()
    )

    if matches.is_empty():
        return {
            "success": False,
            "error": f"No roster record found for {player_name}.",
        }

    player_ids = matches["gsis_id"].drop_nulls().unique()

    if len(player_ids) != 1:
        return {
            "success": False,
            "error": "Player name is ambiguous or lacks a GSIS ID.",
        }

    player_id = player_ids[0]

    player_rows = frame.filter(
        (pl.col("gsis_id") == player_id)
        & pl.col("week").is_not_null()
    )

    if player_rows.is_empty():
        return {
            "success": False,
            "error": "Player has no dated weekly roster records.",
        }

    latest_week = player_rows["week"].max()

    latest_rows = player_rows.filter(
        pl.col("week") == latest_week
    )

    # Don't arbitrarily choose between conflicting team records.
    teams = latest_rows["team"].drop_nulls().unique()

    if len(teams) != 1:
        return {
            "success": False,
            "error": "Conflicting or missing team assignments.",
        }

    # A single team is established; choose a stable row.
    latest = latest_rows.sort(
        ["team", "status"],
        nulls_last=True,
    ).row(0, named=True)

    return {
        "success": True,
        "player": latest["full_name"],
        "player_id": player_id,
        "season": season,
        "week": latest_week,
        "team": latest["team"],
        "position": latest["position"],
        "status": latest["status"],
        "depth_chart_position": latest.get(
            "depth_chart_position"
        ),
        "data_source": metadata,
    }
