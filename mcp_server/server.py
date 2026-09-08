from mcp.server import MCPServer

from tools.player_depth_chart import player_depth_chart


mcp = MCPServer(
    "Fantasy Football Intelligence"
)


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


if __name__ == "__main__":
    mcp.run()