"""Idempotently integrate background NFL refresh into the interactive CLI."""
from pathlib import Path
import sys


def patch(source):
    import_line = 'from nfl_data.auto_refresh import start_background_refresh'
    marker = 'print("Inference backend:", backend())'
    start_line = 'start_background_refresh()'
    if import_line in source and start_line in source:
        return source, False
    if marker not in source:
        raise ValueError("Cannot find expected backend banner in main.py; no changes made")
    source = import_line + "\n" + source if import_line not in source else source
    source = source.replace(marker, marker + "\n" + start_line, 1)
    return source, True


def main():
    path = Path("main.py")
    if not path.is_file():
        raise SystemExit("Run from the fantasyIntelligence repository root")
    old = path.read_text(encoding="utf-8-sig")
    new, changed = patch(old)
    if changed:
        backup_dir = Path(".git") if Path(".git").is_dir() else Path(".")
        backup = backup_dir / "main.before_nfl_refresh.bak"
        if not backup.exists():
            backup.write_text(old, encoding="utf-8")
        path.write_text(new, encoding="utf-8")
        print("Enabled background NFL refresh in main.py; previous version backed up locally.")
    else:
        print("main.py already has background refresh enabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
