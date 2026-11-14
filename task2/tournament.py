"""Seat-swapped matches under one fixed-depth or equal-time protocol.

Deterministic scenarios: replaying an identical configuration is not an independent
trial. Summary rates describe only the selected maps, seats and search settings.
"""
import argparse
from math import isfinite
from itertools import combinations
from collections import defaultdict

from agent import SearchAgent, play_match
from benchmark import build_scenarios, write_csv
from search import MODES


class Tournament:
    def __init__(self, depth=3, max_cycles=40, time_limit_ms=None):
        self.depth, self.max_cycles, self.time_limit_ms = depth, max_cycles, time_limit_ms

    def run(self, scenarios, modes):
        rows = []
        for scenario, initial in scenarios.items():
            for left, right in combinations(modes, 2):
                for mode0, mode1 in ((left, right), (right, left)):
                    state = initial.copy()
                    state.max_cycles = self.max_cycles
                    result = play_match(SearchAgent(mode0, self.depth), SearchAgent(mode1, self.depth),
                                        state=state, max_plies=2*self.max_cycles + 2,
                                        time_limit_ms=self.time_limit_ms)
                    winner = result['winner']
                    final = result['final']
                    row = dict(scenario=scenario, mode0=mode0, mode1=mode1,
                               depth=self.depth, time_limit_ms=self.time_limit_ms,
                               max_cycles=self.max_cycles, winner='draw' if winner is None else winner,
                               reason=result['reason'], cycles=final.cycle,
                               tank_hp0=final.tanks[0].hp, tank_hp1=final.tanks[1].hp,
                               base_hp0=final.bases[0].hp, base_hp1=final.bases[1].hp)
                    for p in (0, 1):
                        row['faults'+str(p)] = result['faults'][p]
                        row['overtime'+str(p)] = result['overtime'][p]
                        row.update({k+str(p): v for k, v in result['metrics'][p].items()})
                    rows.append(row)
                    print(f'{scenario}: P0 {mode0} / P1 {mode1}: '
                          f'{row["winner"]}, {row["reason"]}, {row["cycles"]} cycles', flush=True)
        return rows

    @staticmethod
    def summarize(rows):
        groups = defaultdict(lambda: dict(games=0, wins=0, losses=0, draws=0, faults=0,
                                         overtime=0, time_ms=0., nodes=0, evals=0, moves=0, depth_sum=0))
        for row in rows:
            for p in (0, 1):
                group = groups[row['mode'+str(p)]]
                group['games'] += 1
                group['draws' if row['winner'] == 'draw' else 'wins' if row['winner'] == p else 'losses'] += 1
                for key in ('faults', 'overtime', 'time_ms', 'nodes', 'evals', 'moves', 'depth_sum'):
                    group[key] += row[key+str(p)]
        return [dict(mode=mode, games=g['games'], wins=g['wins'], losses=g['losses'], draws=g['draws'],
                     faults=g['faults'], overtime=g['overtime'],
                     mean_move_ms=round(g['time_ms']/max(1,g['moves']),3),
                     mean_nodes=round(g['nodes']/max(1,g['moves']),2),
                     mean_evals=round(g['evals']/max(1,g['moves']),2),
                     mean_depth=round(g['depth_sum']/max(1,g['moves']),2)) for mode,g in sorted(groups.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', nargs='+', choices=list(build_scenarios()),
                        default=['h_detour','h_dodge','asymmetric'])
    parser.add_argument('--modes', nargs='+', choices=list(MODES), default=list(MODES))
    parser.add_argument('--depth', type=int, default=3)
    parser.add_argument('--max-cycles', type=int, default=40)
    parser.add_argument('--time-limit-ms', type=float, default=None,
                        help='Omit for equal fixed-depth matches; set for equal-time matches.')
    parser.add_argument('--output', default='tournament_results.csv')
    parser.add_argument('--summary', default='tournament_summary.csv')
    args = parser.parse_args()
    if args.depth < 1 or args.max_cycles < 1 or (args.time_limit_ms is not None and (not isfinite(args.time_limit_ms) or args.time_limit_ms <= 0)):
        parser.error('Depth, max cycles and optional time budget must be positive.')
    modes = list(dict.fromkeys(args.modes))
    if len(modes) < 2:
        parser.error('Choose at least two different modes.')
    maps = build_scenarios()
    runner = Tournament(args.depth,args.max_cycles,args.time_limit_ms)
    rows = runner.run({n:maps[n] for n in dict.fromkeys(args.scenarios)},modes)
    summary = runner.summarize(rows)
    write_csv(args.output,rows)
    write_csv(args.summary,summary)
    for row in summary:
        print(row)
    if any(row['faults0'] or row['faults1'] for row in rows):
        raise SystemExit('Agent faults occurred: inspect the CSV; do not count these as clean matches.')
    print('Rates apply only to these scenarios and settings; both seat assignments were tested.')


if __name__=='__main__':
    main()
