"""Check that offset starts are playable and visible through the map registry."""
import sys
import unittest
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'task2'))
from asymmetric_map import build_asymmetric_map
from benchmark import build_scenarios
from game import HUONG
from search import choose_action


class AsymmetricMapTest(unittest.TestCase):
    def test_offset_spawns_and_asymmetric_obstacles(self):
        state = build_scenarios()['asymmetric']
        a, b = state.tanks
        self.assertNotEqual(a.r, b.r)
        self.assertNotEqual(a.c, b.c)
        self.assertEqual(a.hp, b.hp)
        self.assertEqual(state.bases[0].hp, state.bases[1].hp)
        obstacles = set(state.walls) | state.steel
        rotations = {(state.rows - 1 - r, state.cols - 1 - c) for r, c in obstacles}
        horizontal = {(r, state.cols - 1 - c) for r, c in obstacles}
        vertical = {(state.rows - 1 - r, c) for r, c in obstacles}
        self.assertNotEqual(obstacles, rotations)
        self.assertNotEqual(obstacles, horizontal)
        self.assertNotEqual(obstacles, vertical)
        other = build_asymmetric_map()
        state.walls.clear()
        self.assertTrue(other.walls)

    def test_both_players_can_move_and_reach_enemy_base(self):
        state = build_asymmetric_map()
        for p in (0, 1):
            tank, base = state.tanks[p], state.bases[1-p]
            start, goal = (tank.r, tank.c), (base.r, base.c)
            self.assertGreaterEqual(sum(state.is_free(tank.r+dr, tank.c+dc)
                                        for dr, dc in HUONG), 2)
            seen, queue = {start}, deque([start])
            while queue:
                r, c = queue.popleft()
                for dr, dc in HUONG:
                    cell = (r+dr, c+dc)
                    if cell not in seen and (cell == goal or state.is_free(*cell)):
                        seen.add(cell)
                        queue.append(cell)
            self.assertIn(goal, seen)  # An open route exists even without breaking walls.

    def test_search_pairs_agree_from_both_spawns(self):
        for p in (0, 1):
            for depth in (2, 4):
                state = build_asymmetric_map()
                state.to_move = p
                for pair in (('minimax', 'alphabeta'),
                             ('heuristic_minimax', 'heuristic_alphabeta')):
                    x, a = choose_action(state, depth=depth, mode=pair[0])
                    y, b = choose_action(state, depth=depth, mode=pair[1])
                    self.assertIn(x, state.legal_actions())
                    self.assertEqual(x, y)
                    self.assertAlmostEqual(a['score'], b['score'])


if __name__ == '__main__':
    unittest.main()
