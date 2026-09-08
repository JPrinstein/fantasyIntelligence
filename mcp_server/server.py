from mcp.server import MCPServer

from tools.player_depth_chart import player_depth_chart
from tools.player_stats import player_stats
from tools.rag_tool import rag_search
from tools.league_tool import get_league_context

from rag.vector_store import load_index
from rag.storage import load_chunks
from league.loader import load_league

mcp = MCPServer(
    "Fantasy Football Intelligence"
)

chunks = load_chunks("rag_data/chunks.json")
index = load_index("rag_data/index.faiss")
league = load_league()

@mcp.tool()
def get_player_depth_chart(
    player_name: str,
    season: int
) -> dict:
    """
    Get the latest available depth chart information for an NFL player
    for a specific NFL season.
    """

    return player_depth_chart(
        player_name,
        season
    )

@mcp.tool()
def get_player_stats(
    player_name: str,
    season: int,
    week: int | None = None,
    recent_games: int | None = None
) -> dict:
    """
    Get NFL statistics for a specific player.

    Args:
        player_name: Full name of the NFL player.
        season: NFL season, such as 2025.
        week: Optional NFL week for stats from one specific week.
        recent_games: Optional number of most recent games to include.

    Returns:
        Player statistics for the requested season, week, or recent games.
    """

    return player_stats(
        player_name,
        season,
        week,
        recent_games
    )

@mcp.tool()
def search_fantasy_knowledge(query: str) -> dict:
    """
    Search the fantasy football knowledge base for general fantasy football
    rules, concepts, strategy, and positional information.

    Args:
        query: The fantasy football question or topic to search for.

    Returns:
        Relevant knowledge base content and its sources.
    """

    return rag_search(
        query,
        chunks,
        index
    )

@mcp.tool()
def get_my_league_context() -> dict:
    """
    Get authoritative settings and scoring information for the configured
    fantasy football league.

    Returns:
        The league's scoring rules, roster settings, and other
        league-specific context.
    """

    return get_league_context(league)



if __name__ == "__main__":
    mcp.run()