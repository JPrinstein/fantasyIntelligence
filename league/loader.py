import json
from pathlib import Path

DEFAULT_LEAGUE_PATH = Path("data/league.json")

# Simply loading the JSON league settings into our system

def load_league(path=DEFAULT_LEAGUE_PATH):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)