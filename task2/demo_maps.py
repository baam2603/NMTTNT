"""Deterministic maps for comparing terminal-only and heuristic evaluation."""
from game import Bullet, GameState


def build_demo_maps():
    # Two staggered steel barriers force a long detour. Shooting cannot remove steel.
    detour = GameState.from_layout(
        [
            "  b      ",
            "         ",
            "SSSSSSS  ",
            "         ",
            " SSSSSSSS",
            "         ",
            "         ",
            "         ",
            "      a  ",
        ],
        tank_pos=((5, 4), (1, 4)),
    )
    # The player starts facing left, so FIRE does not intercept the downward bullet.
    # A hit costs HP but is not terminal: terminal-only evaluation cannot value it.
    dodge = GameState.from_layout(
        [
            "  b      ",
            "         ",
            " S     S ",
            " S     S ",
            "         ",
            "         ",
            " S     S ",
            "         ",
            "      a  ",
        ],
        tank_pos=((7, 4), (1, 4)),
    )
    dodge.tanks[0] = dodge.tanks[0]._replace(d=2)
    dodge.bullets = [Bullet(5, 4, 1, 1)]
    return {"h_detour": detour, "h_dodge": dodge}
