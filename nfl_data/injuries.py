"""Read player injury reports from verified NFL snapshots."""

from pathlib import Path
import polars as pl
from nfl_data.readers import read_dataset

REQUIRED_INJURY_COLUMNS = {
    "season",
    "week",
    "gsis_id",
    "full_name",
    "team",
    "report_status",
    "practice_status",
    "report_primary_injury",
    "report_secondary_injury",
    "practice_primary_injury",
    "practice_secondary_injury",
}


def _unique_values(frame, column):
    """Return distinct nonempty values without assuming row order."""
    if column not in frame.columns:
        return []

    return sorted({
        str(value).strip()
        for value in frame[column].drop_nulls().to_list()
        if str(value).strip()
    })


def get_player_injury(player_name, season, *, root=None):
    """Return the latest available weekly injury-report observations."""
    if not isinstance(player_name, str) or not player_name.strip():
        raise ValueError("A player name is required.")

    season = int(season)

    # Weekly injuries have no trusted legacy-cache fallback.
    frame, metadata = read_dataset(
        "injuries",
        season,
        Path("__no_legacy_injury_cache__"),
        REQUIRED_INJURY_COLUMNS,
        root=root,
        with_metadata=True,
    )

    matches = frame.filter(
        pl.col("full_name").str.to_lowercase()
        == player_name.strip().lower()
    )

    if matches.is_empty():
        return {
            "success": False,
            "error": (
                f"No injury report found for {player_name} "
                f"in the {season} dataset. This does not "
                "establish that the player is healthy."
            ),
        }

    player_ids = matches["gsis_id"].drop_nulls().unique()

    if len(player_ids) != 1:
        return {
            "success": False,
            "error": "Player name is ambiguous or lacks a GSIS ID.",
        }

    player_id = player_ids[0]

    rows = frame.filter(
        (pl.col("gsis_id") == player_id)
        & pl.col("week").is_not_null()
    )

    if rows.is_empty():
        return {
            "success": False,
            "error": "Player has no dated injury-report records.",
        }

    latest_week = int(rows["week"].max())
    latest = rows.filter(pl.col("week") == latest_week)

    return {
        "success": True,
        "player": player_name.strip(),
        "player_id": player_id,
        "season": season,
        "report_week": latest_week,
        "latest_dataset_week": (
            int(frame["week"].drop_nulls().max())
            if frame["week"].drop_nulls().len()
            else None
        ),
        "teams": _unique_values(latest, "team"),
        "report_statuses": _unique_values(
            latest, "report_status"
        ),
        "practice_statuses": _unique_values(
            latest, "practice_status"
        ),
        "reported_injuries": sorted(set(
            _unique_values(latest, "report_primary_injury")
            + _unique_values(latest, "report_secondary_injury")
            + _unique_values(latest, "practice_primary_injury")
            + _unique_values(latest, "practice_secondary_injury")
        )),
        "report_rows": latest.height,
        "data_source": metadata,
        "interpretation": (
            "These are observations from the latest available "
            "report week for this player. Records have no "
            "report timestamps, so within-week ordering and "
            "current game availability cannot be established."
        ),
    }
