"""Behavior checks for the heuristic demonstration maps."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "task2"))
from benchmark import build_scenarios
from demo_maps import build_demo_maps
from game import Action
from heuristics import HeuristicEvaluator
from search import choose_action


class DemoMapsTest(unittest.TestCase):
    def test_maps_registered_and_fresh(self):
        first, second = build_scenarios(), build_scenarios()
        for name in ("h_detour", "h_dodge"):
            self.assertIn(name, first)
            self.assertFalse(first[name].is_terminal())
            self.assertIsNot(first[name], second[name])
        first["h_dodge"].bullets.clear()
        self.assertEqual(len(second["h_dodge"].bullets), 1)

    def test_equal_depth_pairs_and_visible_behavior(self):
        evaluator = HeuristicEvaluator()
        for name, state in build_demo_maps().items():
            for depth in (2, 4):
                for plain, heuristic in (("minimax", "heuristic_minimax"),
                                         ("alphabeta", "heuristic_alphabeta")):
                    with self.subTest(map=name, depth=depth, plain=plain):
                        before = (tuple(state.tanks), tuple(state.bullets))
                        a, plain_info = choose_action(state, depth=depth, mode=plain)
                        b, heuristic_info = choose_action(state, depth=depth, mode=heuristic)
                        self.assertEqual(before, (tuple(state.tanks), tuple(state.bullets)))
                        self.assertEqual(plain_info["depth_reached"], depth)
                        self.assertEqual(heuristic_info["depth_reached"], depth)
                        self.assertNotEqual(a, b)
                        if name == "h_detour":
                            base = state.bases[1]
                            costs = evaluator.path_cost_map(state, (base.r, base.c))
                            start = state.tanks[0]
                            plain_t = state.apply_action(a).tanks[0]
                            better_t = state.apply_action(b).tanks[0]
                            self.assertEqual(costs[(plain_t.r, plain_t.c)], costs[(start.r, start.c)])
                            self.assertLess(costs[(better_t.r, better_t.c)], costs[(start.r, start.c)])
                        else:
                            plain_child, better_child = state.apply_action(a), state.apply_action(b)
                            # Avoiding this bullet holds against every legal opponent reply.
                            for reply in plain_child.legal_actions():
                                hit = plain_child.apply_action(reply)
                                safe = better_child.apply_action(reply)
                                self.assertEqual(hit.tanks[0].hp, state.tanks[0].hp - 1)
                                self.assertEqual(safe.tanks[0].hp, state.tanks[0].hp)
                for pair in (("minimax", "alphabeta"),
                             ("heuristic_minimax", "heuristic_alphabeta")):
                    results = [choose_action(state, depth=depth, mode=m) for m in pair]
                    self.assertEqual(results[0][0], results[1][0])
                    self.assertAlmostEqual(results[0][1]["score"], results[1][1]["score"])

    def test_detour_rollout_reaches_opening(self):
        state = build_demo_maps()["h_detour"]
        for _ in range(6):
            action, _ = choose_action(state, depth=4, mode="heuristic_minimax")
            state = state.apply_action(action).apply_action(Action.STAY)
        self.assertEqual((state.tanks[0].r, state.tanks[0].c), (3, 0))


if __name__ == "__main__":
    unittest.main()
