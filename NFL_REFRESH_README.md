# NFL data refresh – isolated staging layer (v1)

**Status:** This implements periodic fetching, integrity checks, and provenance metadata. It does **not yet replace the existing `ingestion/` cache readers**: those source files were absent from the uploaded integration source ZIP. This is deliberate; silently guessing the old cache directory/schema could break working NFL tools.

## Set up (project root, Windows PowerShell)

Extract this archive **over the project root**. It only adds `nfl_data/`, `tests/test_nfl_refresh.py`, and this README. It doesn't overwrite the functioning Qwen3.5 integration or existing `ingestion/` code.

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_nfl_refresh -v
.\.venv\Scripts\python.exe -m nfl_data.refresh once --season 2026
.\.venv\Scripts\python.exe -m nfl_data.refresh status --season 2026
```

The first actual refresh downloads season 2026 weekly player stats, depth charts, schedules, and injury data via `nflreadpy`, writing parquet files to `nfl_data/snapshots/`. Explicit season avoids accidentally selecting a future season. No model/API fee, but networking is required. It may fail per-dataset when nflverse has not published a compatible product; other datasets still update.

## Automatic refresh while running

```powershell
.\.venv\Scripts\python.exe -m nfl_data.refresh watch --season 2026
```

The command continuously checks every 15 minutes; only fetches when its snapshot is missing or older than the configured interval (player stats 6h, depth charts 12h, schedules 24h, injuries 6h). Stop with Ctrl+C. It runs only while the command is open; not a Windows background service. Only run **one watcher** at once. Offline failures are logged and retried on a later poll. The snapshot previously published for a dataset is preserved if the new download is empty or fails validation.

### Important limits

- `fetched_at_utc` is the **download time**, *not* the upstream publication/update time. Recent fetch does not guarantee fresh play or injury reports. Provenance is recorded as `nflreadpy/nflverse` with `upstream_updated_at = null` until true provider publication metadata can be verified.
- This is a new **staging** cache: `main.py` still uses the original `ingestion.stats` / `ingestion.depth_charts` cache. Do **not** assume questions in the assistant now use these downloads. The next safe step is connecting readers after inspecting the actual `ingestion/` source.
- Do not commit downloads. Add to `.gitignore`: `nfl_data/snapshots/`.
- NFL injury feeds may have gaps and missing seasons; absence must not be interpreted as a player being healthy. Dates/times and injuries should never be invented.
- To connect live tools accurately, provide the existing `ingestion/` folder (`stats.py`, `depth_charts.py`, `players.py`, any cache helpers), ideally in a small ZIP. Existing `tools/player_stats.py` and `tools/player_depth_chart.py` are available; there is no need to resend the whole repo.
- `nflreadpy` supports the load functions used here: https://nflreadpy.nflverse.com/api/load_functions/

## Optional Git commit

After tests and an initial real refresh succeed, commit only the new source modules, test, and README (not `snapshots/`).
