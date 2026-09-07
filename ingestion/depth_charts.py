from pathlib import Path

import nflreadpy as nfl
import polars

RAW_DATA_DIR = Path("data/raw/depth_charts")

def load_depth_charts(season):
    depth_charts = nfl.load_depth_charts(seasons=[season])

    return depth_charts

def save_depth_charts(depth_charts, season):
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_DATA_DIR/f"depth_charts_{season}.parquet"

    depth_charts.write_parquet(path)

    return path

def load_cached_depth_charts(season):
    path = RAW_DATA_DIR/f"depth_charts_{season}.parquet"

    return polars.read_parquet(path)

def get_latest_depth_chart(depth_charts):
    latest_dt = depth_charts.select(polars.col("dt").max()).item()

    return depth_charts.filter(polars.col("dt") == latest_dt)

def get_player_depth_chart(depth_charts, player_id):
    latest_depth_chart = get_latest_depth_chart(depth_charts)

    player_rows = latest_depth_chart.filter(polars.col("gsis_id") == player_id)

    return player_rows

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