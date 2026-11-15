"""Core assignment checks: independent oracle, game rules and fair experiments."""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'task2'))
from game import GameState, Action, Bullet, Tank, Base
from heuristics import HeuristicEvaluator, TerminalEvaluator
from search import Minimax, AlphaBeta, choose_action, state_key, build_search, MODES
from benchmark import build_scenarios, measure_one, validate_pairs
from agent import FunctionAgent, play_match
from tournament import Tournament


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
    rows, cols, steel, wall_key = 1, 10, frozenset(), frozenset()
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

    def test_zero_sum_and_cycle_counter_does_not_change_rules(self):
        evaluator = HeuristicEvaluator()
        for state in build_scenarios().values():
            self.assertAlmostEqual(evaluator(state, 0), -evaluator(state, 1))
        s, t = board(), board()
        t.cycle = 1_000_000
        self.assertEqual(state_key(s), state_key(t))
        self.assertFalse(t.is_terminal())
        self.assertIsNone(t.termination_reason())
        self.assertTrue(t.legal_actions())
        self.assertFalse(hasattr(s, 'max_cycles'))
        for mode in MODES:
            _, a = choose_action(s, depth=3, mode=mode, track_pv=False)
            _, b = choose_action(t, depth=3, mode=mode, track_pv=False)
            self.assertEqual(a['score'], b['score'])

    def test_terminal_utility_dominates_large_heuristic_weights(self):
        state=build_scenarios()['original_01']
        evaluator=HeuristicEvaluator({'path': 100000000})
        self.assertLess(abs(evaluator(state,0)),10000)
        self.assertAlmostEqual(evaluator(state,0),-evaluator(state,1))
        state.tanks[1]=state.tanks[1]._replace(hp=0)
        state._term=None
        self.assertEqual(evaluator(state,0),10000)
        self.assertEqual(evaluator(state,1),-10000)

    def test_pv_can_be_disabled_without_changing_score_or_building_keys(self):
        state = build_scenarios()['bullet']
        for mode in MODES:
            engine = build_search(mode)
            action, tracked = engine.search(state, depth=4, track_pv=True)
            self.assertTrue(tracked['pv'])
            with patch('search.state_key', side_effect=AssertionError('PV key built during benchmark')):
                other, plain = engine.search(state, depth=4, track_pv=False)
            self.assertEqual(other, action)
            self.assertEqual(plain['score'], tracked['score'])
            self.assertEqual(plain['pv'], [])
            self.assertEqual(engine._best_moves, {})

    def test_exactly_four_modes_with_correct_evaluators(self):
        self.assertEqual(tuple(MODES), ('minimax','alphabeta','heuristic_minimax','heuristic_alphabeta'))
        for mode in MODES:
            engine = build_search(mode)
            expected = HeuristicEvaluator if mode.startswith('heuristic_') else TerminalEvaluator
            self.assertIs(type(engine.evaluator), expected)
        s = board()
        s.tanks[0] = s.tanks[0]._replace(hp=1)
        s.bases[1] = s.bases[1]._replace(hp=2)
        self.assertEqual(TerminalEvaluator()(s,0),0)

    def test_independent_measurements_have_fresh_evaluator_and_pv_off(self):
        engines = []
        original = build_search
        def record(mode, evaluator=None):
            engine = original(mode, evaluator)
            self.assertEqual(engine.evaluator._dist_cache, {})
            engines.append(engine)
            return engine
        with patch('search.build_search', side_effect=record):
            for repeat in (1,2):
                row = measure_one(board(), 'cold_cache', 0, 3, 'heuristic_alphabeta', repeat)
                self.assertFalse(row['track_pv'])
                self.assertEqual(row['total_evals'], row['order_evals'] + row['leaf_evals'])
        self.assertIsNot(engines[0], engines[1])
        self.assertIsNot(engines[0].evaluator, engines[1].evaluator)
        self.assertTrue(all(not e._best_moves for e in engines))

    def test_benchmark_pairs_and_validation(self):
        rows = [measure_one(board(),'case',0,3,mode,1) for mode in MODES]
        self.assertEqual(validate_pairs(rows),2)
        rows[0]['score'] += 1
        with self.assertRaises(AssertionError):
            validate_pairs(rows)

    def test_terminal_only_still_moves_when_loss_is_visible(self):
        s = board(); s.tanks[0] = s.tanks[0]._replace(hp=1)
        s.bullets = [Bullet(4,1,1,1)]
        for mode in ('minimax','alphabeta'):
            action, info = choose_action(s, depth=4, mode=mode)
            self.assertIn(action, (Action.MOVE_LEFT,Action.MOVE_RIGHT))
            self.assertEqual(s.apply_action(action).apply_action(Action.STAY).tanks[0].hp,1)



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

class EnvironmentTest(unittest.TestCase):
    def test_experiment_cycle_cap_stops_without_creating_terminal_or_draw(self):
        agent = FunctionAgent(lambda state: Action.STAY)
        initial = board()
        result = play_match(agent,agent,state=initial,max_plies=None,max_cycles=2)
        self.assertEqual(result['status'],'stopped')
        self.assertEqual(result['reason'],'experiment_cycle_limit')
        self.assertIsNone(result['winner'])
        self.assertFalse(result['final'].is_terminal())
        self.assertEqual(result['final'].cycle,2)
        self.assertEqual(initial.cycle,0)
        self.assertEqual(result['faults'],[0,0])

    def test_ply_cap_is_also_environment_only(self):
        agent = FunctionAgent(lambda state: Action.STAY)
        result = play_match(agent,agent,state=board(),max_plies=1)
        self.assertEqual(result['status'],'stopped')
        self.assertEqual(result['reason'],'experiment_ply_limit')
        self.assertFalse(result['final'].is_terminal())

    def test_destroyed_on_last_cycle_takes_precedence_over_experiment_stop(self):
        s = board(); s.to_move=1; s.tanks[1]=s.tanks[1]._replace(hp=1)
        s.bullets=[Bullet(2,5,0,0)]
        agent = FunctionAgent(lambda state: Action.STAY)
        result = play_match(agent,agent,state=s,max_plies=None,max_cycles=1)
        self.assertEqual(result['status'],'finished')
        self.assertEqual(result['reason'],'destroyed')
        self.assertEqual(result['winner'],0)

    def test_tournament_counts_unfinished_separately_from_draws(self):
        rows=Tournament(depth=1,max_cycles=1).run({'open':board()},['minimax','alphabeta'])
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['winner']=='unfinished' for r in rows))
        for summary in Tournament.summarize(rows):
            self.assertEqual(summary['unfinished'],2)
            self.assertEqual(summary['draws'],0)
            self.assertEqual(summary['faults'],0)

    def test_ui_default_has_no_cap_but_optional_environment_cap_says_stopped(self):
        from ai_battle import Match,Task2Backend
        backend=Task2Backend(ROOT/'task2');s=board()
        live=Match(backend,s,[None,None],[{},{}],[2,2])
        s.cycle=1_000_000
        self.assertFalse(live.is_over())
        s=board();limited=Match(backend,s,[None,None],[{},{}],[2,2],max_cycles=1)
        limited.state=s.apply_action(Action.STAY).apply_action(Action.STAY)
        self.assertTrue(limited.is_over())
        self.assertEqual(limited.result_text()[0],'STOPPED')
        self.assertFalse(limited.state.is_terminal())

    def test_environment_limits_validate_input(self):
        agent=FunctionAgent(lambda state: Action.STAY)
        for invalid in (0,-1,True,1.2):
            with self.assertRaises(ValueError):
                play_match(agent,agent,state=board(),max_cycles=invalid)



if __name__=='__main__':
    unittest.main()
