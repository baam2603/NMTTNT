"""Compare evaluators at equal depth, with no time limit or repetition penalty."""
import argparse

from demo_maps import build_demo_maps
from game import Action
from heuristics import HeuristicEvaluator
from search import choose_action

MODES = ("minimax", "heuristic_minimax", "alphabeta", "heuristic_alphabeta")


def compare(depth=4):
    evaluator = HeuristicEvaluator()
    for name, state in build_demo_maps().items():
        base = state.bases[1]
        distances = evaluator.path_cost_map(state, (base.r, base.c))
        tank = state.tanks[0]
        initial = distances.get((tank.r, tank.c))
        print(f"\n{name}: depth={depth}, P0 acts; P1 replies STAY for the HP observation")
        print("No time limit; no history/repetition penalty. Distance = weighted path cost.")
        print(f"Initial HP={tank.hp}, distance={initial}")
        print(f"{'Mode':<23} {'First move':<12} {'HP after round':>14} {'Distance':>9} {'Nodes':>8}")
        for mode in MODES:
            action, info = choose_action(state, depth=depth, mode=mode)
            child = state.apply_action(action)
            after = child.apply_action(Action.STAY)
            t = after.tanks[0]
            print(f"{mode:<23} {action.name:<12} {t.hp:>14} "
                  f"{distances.get((t.r, t.c), 'inf'):>9} {info['nodes']:>8}")
        if name == "h_detour":
            print("Six P0 moves with P1 fixed at STAY (not a match win-rate test):")
            for mode in ("minimax", "heuristic_minimax"):
                current, moves = state, []
                for _ in range(6):
                    action, _ = choose_action(current, depth=depth, mode=mode)
                    current = current.apply_action(action).apply_action(Action.STAY)
                    t = current.tanks[0]
                    moves.append(f"{action.name}@({t.r},{t.c})")
                print(f"  {mode}: " + " -> ".join(moves))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", type=int, default=4)
    args = parser.parse_args()
    if args.depth < 1:
        parser.error("--depth must be >= 1")
    compare(args.depth)
