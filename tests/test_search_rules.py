"""Independent small-tree oracle, game-rule edge cases, and timing accounting."""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'task2'))
from game import GameState, Action, Bullet, Tank, Base
from heuristics import HeuristicEvaluator, TerminalEvaluator
from search import Minimax, AlphaBeta, choose_action, state_key, transposition_key
from benchmark import build_scenarios


def board():
    s = GameState.from_layout(['      b'] + ['       ']*5 + ['a      '],
                              tank_pos=((5, 1), (1, 5)))
    return s


def round_end(s):
    return s.apply_action(Action.STAY).apply_action(Action.STAY)


def oracle(s, depth, me, evaluator):
    if s.is_terminal():
        v = evaluator(s, me)
        return v + depth if v > 0 else v - depth if v < 0 else 0
    if depth <= 0:
        return evaluator(s, me)
    values = [oracle(s.apply_action(a), depth-1, me, evaluator) for a in s.legal_actions()]
    return (max if s.to_move == me else min)(values)


class ToyState:
    rows, cols, steel, wall_key, max_cycles = 1, 10, frozenset(), frozenset(), None
    bases, bullets = [], []
    def __init__(self, path=()):
        self.path = path
        self.tanks = [path]
        self.to_move, self.cycle = len(path) % 2, len(path) // 2
    def legal_actions(self):
        return [] if self.is_terminal() else [Action.MOVE_UP, Action.MOVE_DOWN]
    def is_terminal(self):
        return len(self.path) == 2
    def apply_action(self, action, check=True):
        return ToyState(self.path + (action,))


def toy_eval(s, me):
    values = {(Action.MOVE_UP, Action.MOVE_UP): 3,
              (Action.MOVE_UP, Action.MOVE_DOWN): 5,
              (Action.MOVE_DOWN, Action.MOVE_UP): 2,
              (Action.MOVE_DOWN, Action.MOVE_DOWN): 9}
    return values.get(s.path, 0) * (1 if me == 0 else -1)


class SearchTest(unittest.TestCase):
    def test_hand_calculated_tree_and_eval_counts(self):
        for cls, leaves in ((Minimax, 4), (AlphaBeta, 3)):
            engine = cls(toy_eval)
            a, info = engine.search(ToyState(), depth=2)
            self.assertEqual(a, Action.MOVE_UP)  # max(min(3,5), min(2,9)) = 3
            self.assertEqual(info['score'], 3)
            self.assertEqual(info['leaves'], leaves)
            self.assertEqual(info['order_evals'], 2)
            self.assertEqual(info['leaf_evals'], leaves)
            self.assertEqual(info['evals'], leaves+2)
            if cls is AlphaBeta:
                self.assertGreater(info['cutoffs'], 0)
                self.assertEqual(info['root_actions'][1]['bound'], 'upper')

    def test_all_maps_against_independent_exhaustive_oracle(self):
        for name, initial in build_scenarios().items():
            for player in (0, 1):
                for evaluator_cls, modes in ((TerminalEvaluator, ('minimax', 'alphabeta')),
                                            (HeuristicEvaluator, ('heuristic_minimax', 'heuristic_alphabeta'))):
                    state = initial.copy()
                    state.to_move = player
                    evaluator = evaluator_cls()
                    expected = oracle(state, 3, player, evaluator)
                    for mode in modes:
                        with self.subTest(map=name, player=player, mode=mode):
                            action, info = choose_action(state, depth=3, mode=mode)
                            self.assertAlmostEqual(info['score'], expected)
                            self.assertAlmostEqual(oracle(state.apply_action(action), 2, player, evaluator), expected)
                            self.assertEqual(info['evals'], info['leaf_evals'] + info['order_evals'])
                            self.assertEqual(info['leaf_evals'], info['leaves'])
                            for row in info['root_actions']:
                                exact = oracle(state.apply_action(Action[row['action']]), 2, player, evaluator)
                                if row['bound'] == 'exact':
                                    self.assertAlmostEqual(exact, row['score'])
                                else:
                                    self.assertLessEqual(exact, row['score'] + 1e-8)
                            current = state
                            for entry in info['pv']:
                                self.assertEqual(entry['player'], current.to_move)
                                self.assertIn(Action[entry['action']], current.legal_actions())
                                current = current.apply_action(Action[entry['action']])
                            if len(info['pv']) == 3 or current.is_terminal():
                                remaining = 3-len(info['pv'])
                                self.assertAlmostEqual(oracle(current, remaining, player, evaluator), expected)

    def test_deadline_covers_root_ordering_and_fallback(self):
        calls = []
        def slow(state, me):
            calls.append(1)
            time.sleep(.01)
            return 0
        state = board()
        action, info = Minimax(slow).search(state, depth=4, time_limit_ms=1)
        self.assertIn(action, state.legal_actions())
        self.assertEqual(len(calls), 1)
        self.assertEqual(info['evals'], 1)
        self.assertEqual(info['depth_reached'], 0)
        self.assertTrue(info['fallback'])
        self.assertTrue(info['timed_out'])
        self.assertEqual(info['root_actions'], [])

    def test_zero_sum_and_distinct_horizon_keys(self):
        evaluator = HeuristicEvaluator()
        for state in build_scenarios().values():
            self.assertAlmostEqual(evaluator(state, 0), -evaluator(state, 1))
        s, t = board(), board()
        t.cycle = 1
        self.assertEqual(state_key(s), state_key(t))
        self.assertNotEqual(transposition_key(s), transposition_key(t))
        s.max_cycles = t.max_cycles = None
        self.assertEqual(transposition_key(s), transposition_key(t))

    def test_terminal_utility_dominates_large_heuristic_weights(self):
        state=build_scenarios()['asymmetric']
        evaluator=HeuristicEvaluator({'path': 100000000})
        self.assertLess(abs(evaluator(state,0)),10000)
        self.assertAlmostEqual(evaluator(state,0),-evaluator(state,1))
        state.tanks[1]=state.tanks[1]._replace(hp=0)
        state._term=None
        self.assertEqual(evaluator(state,0),10000)
        self.assertEqual(evaluator(state,1),-10000)

    def test_tt_enabled_disabled_and_history_default(self):
        s = build_scenarios()['h_dodge']
        evaluator = HeuristicEvaluator()
        x, a = AlphaBeta(evaluator, use_tt=True).search(s, depth=4)
        y, b = AlphaBeta(evaluator, use_tt=False).search(s, depth=4)
        self.assertEqual(x, y)
        self.assertAlmostEqual(a['score'], b['score'])
        history = {state_key(s.apply_action(action)): 100 for action in s.legal_actions()}
        z, c = choose_action(s, depth=4, mode='heuristic_alphabeta', history=history)
        self.assertEqual(x, z)
        self.assertEqual(a['score'], c['score'])


class RulesTest(unittest.TestCase):
    def test_one_cell_motion_rotation_and_blocking(self):
        s = board()
        t = s.apply_action(Action.MOVE_RIGHT)
        self.assertEqual((t.tanks[0].r, t.tanks[0].c, t.tanks[0].d), (5,2,3))
        s.walls[(5,2)] = 3
        t = s.apply_action(Action.MOVE_RIGHT)
        self.assertEqual((t.tanks[0].r,t.tanks[0].c,t.tanks[0].d), (5,1,3))
        self.assertEqual(s.tanks[0].d, 0)

    def test_bullets_move_only_after_both_actions_and_up_to_three_cells(self):
        s = board();s.bullets=[Bullet(4,0,3,0)]
        half=s.apply_action(Action.STAY)
        self.assertEqual(half.bullets, s.bullets)
        end=half.apply_action(Action.STAY)
        self.assertEqual(end.bullets,[Bullet(4,3,3,0)])
        self.assertEqual(end.cycle,1)

    def test_intermediate_collision_and_wall_hp(self):
        s=board();s.walls[(4,2)]=3;s.bullets=[Bullet(4,0,3,0)]
        end=round_end(s)
        self.assertEqual(end.walls[(4,2)],2)
        self.assertEqual(end.bullets,[])
        self.assertEqual(s.walls[(4,2)],3)
        s.bullets=[Bullet(4,1,3,0),Bullet(3,2,1,0),Bullet(5,2,0,0)]
        s.tanks[1]=Tank(4,4,2,6)
        end=round_end(s)
        self.assertNotIn((4,2),end.walls)
        self.assertEqual(end.tanks[1].hp,6)
        self.assertEqual(end.bullets,[])
        s=board();s.steel=frozenset({(4,2)});s.bullets=[Bullet(4,0,3,0)]
        self.assertEqual(round_end(s).bullets,[])

    def test_meeting_and_crossing_bullets(self):
        for pair in ((1,3),(2,3)):
            s=board();s.bullets=[Bullet(4,pair[0],3,0),Bullet(4,pair[1],2,1)]
            self.assertEqual(round_end(s).bullets,[])

    def test_tank_steps_onto_bullet(self):
        s=board();s.bullets=[Bullet(5,2,3,1)]
        t=s.apply_action(Action.MOVE_RIGHT)
        self.assertEqual(t.tanks[0].hp,5)
        self.assertEqual(t.bullets,[])

    def test_simultaneous_destruction_draw_and_friendly_base_hit(self):
        s=board();s.tanks=[Tank(5,1,0,1),Tank(1,5,1,1)]
        s.bullets=[Bullet(4,1,1,1),Bullet(2,5,0,0)]
        end=round_end(s)
        self.assertTrue(end.is_terminal());self.assertIsNone(end.winner())
        s=board();s.bases[0]=Base(6,1,9);s.tanks[0]=s.tanks[0]._replace(d=1)
        end=s.apply_action(Action.FIRE).apply_action(Action.STAY)
        self.assertEqual(end.bases[0].hp,8)

    def test_cycle_limit_is_engine_terminal_and_last_round_win_takes_precedence(self):
        s=board();s.max_cycles=1
        self.assertFalse(s.is_terminal())
        end=round_end(s)
        self.assertTrue(end.is_terminal());self.assertIsNone(end.winner())
        self.assertEqual(end.legal_actions(),[])
        with self.assertRaises(ValueError):end.apply_action(Action.STAY)
        s=board();s.max_cycles=1;s.to_move=1;s.tanks[1]=s.tanks[1]._replace(hp=1)
        s.bullets=[Bullet(2,5,0,0)]
        end=s.apply_action(Action.STAY)
        self.assertEqual(end.cycle,1);self.assertEqual(end.winner(),0)


if __name__=='__main__':
    unittest.main()
