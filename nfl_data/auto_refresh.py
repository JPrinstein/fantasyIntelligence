"""Non-blocking NFL snapshot refresh while the CLI assistant is running."""
from __future__ import annotations

import os
from pathlib import Path
import threading

from nfl_data.refresh import DEFAULT_ROOT, REFRESH_HOURS, describe, refresh_one

_thread = None


def _refresh_loop(stop_event, season, root, poll_minutes):
    # Only one refresh loop should run per assistant process.
    while not stop_event.is_set():
        for dataset in REFRESH_HOURS:
            if stop_event.is_set():
                return
            try:
                status = describe(dataset, season, root)
                if status["status"] == "fresh":
                    continue
                entry = refresh_one(dataset, season, root=root)
                print(f"\n[NFL refresh] {dataset} {season}: {entry['rows']:,} rows", flush=True)
            except Exception as exc:
                print(f"\n[NFL refresh] {dataset} {season} failed: {type(exc).__name__}: {exc}", flush=True)
        stop_event.wait(poll_minutes * 60)


def start_background_refresh(season=None, *, root=DEFAULT_ROOT, poll_minutes=15):
    """Start a daemon only when enabled; never delay the interactive prompt."""
    global _thread
    if os.getenv("FANTASY_NFL_AUTO_REFRESH", "1").lower() in {"0", "false", "off", "no"}:
        return None
    if _thread and _thread.is_alive():
        return _thread
    if season is None:
        import nflreadpy
        season = int(nflreadpy.get_current_season())
    stop_event = threading.Event()
    _thread = threading.Thread(
        target=_refresh_loop,
        args=(stop_event, int(season), Path(root), int(poll_minutes)),
        name="fantasy-nfl-refresh",
        daemon=True,
    )
    _thread.start()
    return _thread
