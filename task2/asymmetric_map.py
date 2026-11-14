"""An asymmetric arena with offset tank spawns and equal starting HP."""
from game import GameState


def build_asymmetric_map():
    state = GameState.from_layout(
        [
            "        b  ",
            "  WW       ",
            "  S   W    ",
            "  S   W  W ",
            "      S WW ",
            " W SS S    ",
            " W    S    ",
            "   WW   S  ",
            " S      S  ",
            "   W       ",
            " a         ",
        ],
        tank_pos=((8, 2), (2, 9)),
    )
    state.tanks[0] = state.tanks[0]._replace(d=3)  # P0 faces right.
    state.tanks[1] = state.tanks[1]._replace(d=2)  # P1 faces left.
    return state
