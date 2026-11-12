# Fantasy Intelligence — NFL snapshot reader integration (v2)

This patch connects existing NFL tools to the independently downloaded data snapshots created by `nfl_data.refresh` from v1. It does not touch the working Qwen3.5 model, existing model files, or the original legacy Parquet caches.

## Install

From the repo root in PowerShell:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\fantasy_nfl_data_integration_v2.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m scripts.enable_auto_refresh
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m nfl_data.refresh status --season 2026
.\.venv\Scripts\python.exe main.py
```

The one-time patch script inserts the background refresh startup call into the current `main.py`, preserving any previously added generation metrics. It creates a backup at `.git/main.before_nfl_refresh.bak` if `.git` is present. Run it again safely; it is idempotent.

## How data selection works

- Published and integrity-verified snapshot available: stats and depth-chart tools read it. Every read verifies SHA-256 and required fields; stale snapshots can still be read but are flagged as stale and include their fetch timestamp.
- No published snapshot for the requested year: tools use the old `data/raw/...` files, with `freshness=unknown`. This preserves historical seasons even if only 2026 is being refreshed.
- Published snapshot corrupt, missing, unsafe, or incompatible: fail clearly rather than silently mixing or substituting data.
- Data provenance is included in tool results and the LLM evidence text. `fetched_at_utc` is *when we fetched the file*, not when NFL data was updated.
- Depth chart query returns the requested player's newest row within the selected season, rather than filtering on the entire league's latest upload date.

When the assistant starts, a daemon thread refreshes the **current NFL season** without blocking the user prompt, then polls every 15 minutes. Dataset cadences remain 6h for stats/injuries, 12h depth, 24h schedules. `FANTASY_NFL_AUTO_REFRESH=0` disables this. The CLI must remain running for periodic refresh to occur; this is not a Windows scheduled task.

Schedules/injuries are refreshed into verified snapshots but **not yet exposed as live assistant tools**; the existing planner tool registry is unchanged. No current injury claims are inferred from stale/missing evidence.

## Important validation and limitations

The patch has offline unit tests. It was not run against the user's actual Windows Parquet schemas, llama.cpp instance, or network; those require the local test run. Keep the legacy caches until the results look correct. Do not run a separate `nfl_data.refresh watch` alongside the assistant: this version has no cross-process writer lock.

If an installed upstream version changes field names, the reader fails with a list of required columns rather than fabricating stats. Check the full error and actual columns; do not rename a source column without checking its meaning.

## Verify in the assistant

1. Ask for Lamar Jackson's **2025** season passing yards; the legacy cache should still support it.
2. Ask for a **2026** player stat; wait for the background refresh to report completion, or manually run `python -m nfl_data.refresh once --season 2026` before launching the assistant. Verify it reads a `verified_snapshot`.
3. Ask about a 2026 depth chart; compare dates, and confirm it reports the selected player's latest available record.
4. Review `python -m nfl_data.refresh status --season 2026` for fetch timestamps and dataset status.

No weights, snapshots, benchmark results, temporary ZIPs or backup files should be committed.

## Git commands

After tests and reviewing `git diff`, stage **only** these files:

```powershell
git add -- ingestion/stats.py ingestion/depth_charts.py tools/player_stats.py tools/player_depth_chart.py agent/evidence.py nfl_data/readers.py nfl_data/auto_refresh.py scripts/enable_auto_refresh.py tests/test_snapshot_readers_v2.py NFL_DATA_INTEGRATION_README.md main.py
git diff --cached --name-only
git diff --cached --check
git commit -m "Connect verified NFL snapshots to fantasy tools and enable background refresh"
git push origin main
```

Do not stage files before unit tests and live questions have passed.
