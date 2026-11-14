import argparse
import csv
import random
from collections import defaultdict
from math import isclose
from pathlib import Path
from statistics import mean, median

from game import Bullet, GameState
from search import MODES, choose_action


MODES_ORDER = (
    "minimax",
    "alphabeta",
    "heuristic_minimax",
    "heuristic_alphabeta",
)
def make_map(walls=(), steel=()):
    grid = [[" " for _ in range(9)] for _ in range(9)]
    grid[8][6] = "a"
    grid[0][2] = "b"
    for r, c in walls:
        grid[r][c] = "W"
    for r, c in steel:
        grid[r][c] = "S"
    return ["".join(row) for row in grid]


def build_scenarios():
    cases = {"default": GameState.from_layout()}

    cases["open"] = GameState.from_layout(
        make_map(), tank_pos=((7, 4), (1, 4))
    )

    cases["walls"] = GameState.from_layout(
        make_map(
            walls=((2, 3), (2, 4), (2, 5), (4, 2), (4, 4),
                   (4, 6), (6, 3), (6, 4), (6, 5)),
            steel=((4, 1), (4, 7)),
        ),
        tank_pos=((7, 4), (1, 4)),
    )

    defense = GameState.from_layout(
        make_map(), tank_pos=((7, 4), (6, 6))
    )
    defense.tanks[1] = defense.tanks[1]._replace(d=1)
    cases["defense"] = defense

    bullet = GameState.from_layout(
        make_map(), tank_pos=((7, 4), (1, 4))
    )
    # Dan cua player 1 dang tien den tank player 0.
    bullet.bullets.append(Bullet(6, 4, 1, 1))
    cases["bullet"] = bullet

    from demo_maps import build_demo_maps
    cases.update(build_demo_maps())
    from asymmetric_map import build_asymmetric_map
    cases["asymmetric"] = build_asymmetric_map()
    return cases


def measure_one(state, scenario, player, depth, mode, repeat):
    snapshot = state.copy()
    snapshot.to_move = player
    before = (
        tuple(snapshot.tanks), tuple(snapshot.bases),
        tuple(snapshot.bullets), tuple(sorted(snapshot.walls.items())),
        snapshot.to_move, snapshot.cycle,
    )

    action, info = choose_action(snapshot, depth=depth, mode=mode)

    after = (
        tuple(snapshot.tanks), tuple(snapshot.bases),
        tuple(snapshot.bullets), tuple(sorted(snapshot.walls.items())),
        snapshot.to_move, snapshot.cycle,
    )
    if before != after:
        raise AssertionError("Search da thay doi GameState goc")
    if action not in snapshot.legal_actions():
        raise AssertionError(f"Action khong hop le: {action}")

    elapsed = info["time_ms"]
    nodes = info["nodes"]
    return {
        "scenario": scenario,
        "player": player,
        "depth": depth,
        "repeat": repeat,
        "mode": mode,
        "action": action.name,
        "score": info["score"],
        "time_ms": round(elapsed, 6),
        "nodes": nodes,
        "leaves": info["leaves"],
        "cutoffs": info["cutoffs"],
        "pruned_actions": info["pruned_actions"],
        "order_evals": 0,
        "total_evals": info["leaves"],
        "nodes_per_second": round(nodes / (elapsed / 1000), 1) if elapsed > 0 else 0,
    }


def validate_pairs(rows):
    groups = defaultdict(dict)
    for row in rows:
        key = (row["scenario"], row["player"], row["depth"], row["repeat"])
        groups[key][row["mode"]] = row

    for key, d in groups.items():
        for plain, ab in (("minimax", "alphabeta"),
                          ("heuristic_minimax", "heuristic_alphabeta")):
            if not isclose(d[plain]["score"], d[ab]["score"],
                           rel_tol=1e-9, abs_tol=1e-8):
                raise AssertionError(
                    f"Khac diem Minimax/Alpha-Beta tai {key}: "
                    f"{plain}={d[plain]['score']}, {ab}={d[ab]['score']}"
                )
    return len(groups)


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["player"], row["depth"], row["mode"])].append(row)

    summary = []
    for (scenario, player, depth, mode), samples in sorted(groups.items()):
        summary.append({
            "scenario": scenario,
            "player": player,
            "depth": depth,
            "mode": mode,
            "repeats": len(samples),
            "median_time_ms": round(median(x["time_ms"] for x in samples), 4),
            "mean_time_ms": round(mean(x["time_ms"] for x in samples), 4),
            "mean_nodes": round(mean(x["nodes"] for x in samples), 2),
            "mean_leaves": round(mean(x["leaves"] for x in samples), 2),
            "mean_cutoffs": round(mean(x["cutoffs"] for x in samples), 2),
            "mean_pruned_actions": round(mean(x["pruned_actions"] for x in samples), 2),
            "mean_order_evals": round(mean(x["order_evals"] for x in samples), 2),
            "mean_total_evals": round(mean(x["total_evals"] for x in samples), 2),
            "chosen_action": samples[0]["action"],
            "score": samples[0]["score"],
        })
    return summary


def write_csv(path, rows):
    if not rows:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_summary(summary):
    print("\n--- BANG KET QUA (median ms / nodes / evals trung binh) ---")
    head = f"{'Scenario':<9} {'P':>1} {'Depth':>5} {'Mode':<22} {'Time(ms)':>10} {'Nodes':>9} {'Cutoffs':>8} {'Evals':>9}"
    print(head)
    print("-" * len(head))
    for row in summary:
        print(
            f"{row['scenario']:<9} {row['player']:>1} {row['depth']:>5} "
            f"{row['mode']:<22} {row['median_time_ms']:>10.3f} "
            f"{row['mean_nodes']:>9.0f} {row['mean_cutoffs']:>8.0f} "
            f"{row['mean_total_evals']:>9.0f}"
        )


def main():
    parser = argparse.ArgumentParser(description="Benchmark Battle City Adversarial Search")
    parser.add_argument("--depths", type=int, nargs="+", default=[2, 3, 4],
                        help="Do sau tinh theo so ACTION. Mac dinh: 2 3 4")
    parser.add_argument("--repeats", type=int, default=3,
                        help="So lan lap lai moi cau hinh, mac dinh: 3")
    parser.add_argument("--players", choices=["0", "1", "both"], default="both")
    parser.add_argument("--scenarios", nargs="+",
                        choices=list(build_scenarios()) + ["all"], default=["all"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="benchmark_results.csv")
    parser.add_argument("--summary", default="benchmark_summary.csv")
    args = parser.parse_args()

    if args.repeats < 1 or any(depth < 1 for depth in args.depths):
        parser.error("--repeats va moi --depths phai >= 1")

    cases = build_scenarios()
    selected = list(cases) if "all" in args.scenarios else list(dict.fromkeys(args.scenarios))
    players = [0, 1] if args.players == "both" else [int(args.players)]
    rng = random.Random(args.seed)
    rows = []

    for scenario in selected:
        for player in players:
            for depth in args.depths:
                for repeat in range(1, args.repeats + 1):
                    modes = list(MODES_ORDER)
                    rng.shuffle(modes)  # Giam sai lech do thu tu chay thuat toan
                    for mode in modes:
                        rows.append(measure_one(cases[scenario], scenario, player,
                                                depth, mode, repeat))
                print(f"Da xong: scenario={scenario}, player={player}, depth={depth}", flush=True)

    groups_checked = validate_pairs(rows)
    summary = summarize(rows)
    write_csv(args.output, rows)
    write_csv(args.summary, summary)
    print_summary(summary)
    print(f"\nPASS: {groups_checked} cap dieu kien (scenario/player/depth/repeat) "
          "co diem Minimax = Alpha-Beta.")
    print(f"Da luu: {args.output} ({len(rows)} lan chay)")
    print(f"Da luu: {args.summary} ({len(summary)} dong tong hop)")
    print("Luu y: Evals = so lan goi ham danh gia (leaves + order_evals).")
    print("simple_eval la baseline dua vao HP, khong phai terminal-only Minimax.")


if __name__ == "__main__":
    main()