def build_league_context(league):
    scoring = league["scoring"]
    roster = league["roster_settings"]

    scoring_format = get_scoring_format(league)

    lines = [
        f"League: {league['name']}",
        "",
        "Scoring:",
        f"- Passing yards: {scoring['passing_yards']} points per yard",
        f"- Passing touchdown: {scoring['passing_td']} points",
        f"- Interception: {scoring['interception']} points",
        f"- Rushing yards: {scoring['rushing_yards']} points per yard",
        f"- Rushing touchdown: {scoring['rushing_td']} points",
        f"- Receiving yards: {scoring['receiving_yards']} points per yard",
        f"- Receiving touchdown: {scoring['receiving_td']} points",
        f"- Reception: {scoring['reception']} points",
        f"- Scoring format: {scoring_format}",
        "",
        "Roster settings:",
        f"- QB: {roster['QB']}",
        f"- RB: {roster['RB']}",
        f"- WR: {roster['WR']}",
        f"- TE: {roster['TE']}",
        f"- FLEX: {roster['FLEX']}",
        f"- SUPERFLEX: {roster['SUPERFLEX']}",
        f"- BENCH: {roster['BENCH']}"
    ]

    return "\n".join(lines)

def get_scoring_format(league):
    reception_points = league["scoring"]["reception"]

    if reception_points == 1:
        return "PPR"
    elif reception_points == 0.5:
        return "Half-PPR"
    elif reception_points == 0:
        return "Standard"

    return f"Custom ({reception_points} points per reception)"