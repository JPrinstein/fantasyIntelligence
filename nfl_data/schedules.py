"""Look up NFL matchups from verified schedule snapshots."""

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

from nfl_data.readers import read_dataset


REQUIRED_SCHEDULE_COLUMNS = {
    "season", "week", "game_type", "gameday",
    "gametime", "home_team", "away_team",
    "home_score", "away_score", "game_id",
}


def _game_result(row, team, metadata):
    """Format a matchup from the requested team's perspective."""
    is_home = row["home_team"] == team

    return {
        "success": True,
        "team": team,
        "season": int(row["season"]),
        "week": int(row["week"]),
        "game_id": row["game_id"],
        "game_date": str(row["gameday"]),
        "game_time": row["gametime"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "opponent": (
            row["away_team"] if is_home else row["home_team"]
        ),
        "location": "home" if is_home else "away",
        "completed": (
            row["home_score"] is not None
            and row["away_score"] is not None
        ),
        "home_score": row["home_score"],
        "away_score": row["away_score"],
        "data_source": metadata,
    }


def get_team_schedule(team, season, week=None, *, root=None, as_of=None):
    """Get a regular-season matchup or next scheduled game."""
    if not isinstance(team, str) or not team.strip():
        raise ValueError("A team abbreviation is required.")

    team = team.strip().upper()
    season = int(season)

    if as_of is None:
        as_of = datetime.now(ZoneInfo("America/New_York")).date()
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    if not isinstance(as_of, date) or isinstance(as_of, datetime):
        raise ValueError("as_of must be a date or ISO date string.")

    if week is not None:
        week = int(week)
        if not 1 <= week <= 18:
            raise ValueError("Regular-season week must be 1–18.")

    frame, metadata = read_dataset(
        "schedules",
        season,
        Path("__no_legacy_schedule_cache__"),
        REQUIRED_SCHEDULE_COLUMNS,
        root=root,
        with_metadata=True,
    )

    regular = frame.filter(
        (pl.col("season") == season)
        & (pl.col("game_type") == "REG")
    )

    team_games = regular.filter(
        (pl.col("home_team") == team)
        | (pl.col("away_team") == team)
    )

    if team_games.is_empty():
        return {
            "success": False,
            "error": f"No regular-season games found for {team}.",
        }

    if week is not None:
        requested = team_games.filter(pl.col("week") == week)

        if requested.is_empty():
            scheduled_week = regular.filter(
                pl.col("week") == week
            )

            if scheduled_week.is_empty():
                return {
                    "success": False,
                    "error": f"Week {week} has no schedule data.",
                }

            return {
                "success": True,
                "team": team,
                "season": season,
                "week": week,
                "bye_week": True,
                "message": f"{team} has no scheduled game in Week {week}.",
                "data_source": metadata,
            }

        row = requested.sort(
            ["gameday", "gametime", "game_id"]
        ).row(0, named=True)

        result = _game_result(row, team, metadata)
        result["bye_week"] = False
        return result

    # For next-game lookups, exclude older dates and games
    # that already have final scores in the snapshot.
    upcoming = team_games.filter(
        (pl.col("gameday").cast(pl.String) >= as_of.isoformat())
        & pl.col("home_score").is_null()
        & pl.col("away_score").is_null()
    )

    if upcoming.is_empty():
        return {
            "success": False,
            "team": team,
            "season": season,
            "error": "No upcoming regular-season game found.",
            "data_source": metadata,
        }

    row = upcoming.sort(
        ["gameday", "gametime", "game_id"]
    ).row(0, named=True)

    result = _game_result(row, team, metadata)
    result["bye_week"] = False
    result["as_of_date"] = as_of.isoformat()
    return result
