from pathlib import Path

import nflreadpy as nfl
import polars
from nfl_data.readers import read_dataset

RAW_DATA_DIR = Path("data/raw/depth_charts")

def load_depth_charts(season):
    depth_charts = nfl.load_depth_charts(seasons=[season])

    return depth_charts

def save_depth_charts(depth_charts, season):
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_DATA_DIR/f"depth_charts_{season}.parquet"

    depth_charts.write_parquet(path)

    return path

DEPTH_REQUIRED_COLUMNS = {
    "dt", "gsis_id", "player_name", "team", "pos_abb", "pos_name", "pos_rank",
}


def load_cached_depth_charts(season, *, with_metadata=False):
    path = RAW_DATA_DIR / f"depth_charts_{season}.parquet"
    return read_dataset("depth_charts", season, path, DEPTH_REQUIRED_COLUMNS,
                        with_metadata=with_metadata)

def get_latest_depth_chart(depth_charts):
    latest_dt = depth_charts.select(polars.col("dt").max()).item()

    return depth_charts.filter(polars.col("dt") == latest_dt)

def get_player_depth_chart(depth_charts, player_id):
    # A player may be absent from the league's latest global update; use
    # the player's own most recent available snapshot instead.
    player_rows = depth_charts.filter(polars.col("gsis_id") == player_id)
    if player_rows.is_empty():
        return player_rows
    latest_dt = player_rows.select(polars.col("dt").max()).item()
    return player_rows.filter(polars.col("dt") == latest_dt)

if __name__ == "__main__":
    depth_charts = load_depth_charts(2025)

    path = save_depth_charts(
        depth_charts,
        2025
    )

    print(f"Saved to: {path}")

    cached = load_cached_depth_charts(2025)

    print(cached.columns)
    print(cached.shape)