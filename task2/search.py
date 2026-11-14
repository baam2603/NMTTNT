"""Four adversarial-search configurations with observable, bounded-depth decisions.

Plain modes use terminal utility only. No hidden heuristic or scripted movement is
injected into them. Equal values are resolved by the search's stable action order.
"""
from abc import ABC, abstractmethod
from math import isfinite
from time import perf_counter

from heuristics import HeuristicEvaluator, TerminalEvaluator

INF = float('inf')


def state_key(state):
    """Physical position for repetition detection; independent of elapsed time."""
    return (state.rows, state.cols, state.steel, tuple(state.tanks),
            tuple(state.bases), tuple(sorted(state.bullets)),
            state.wall_key, state.to_move)


def transposition_key(state):
    """Search identity includes the draw horizon, unlike repetition identity."""
    limit = getattr(state, 'max_cycles', None)
    remaining = None if limit is None else max(0, limit - state.cycle)
    return state_key(state), remaining


def _new_stats():
    return dict(nodes=0, generated=0, leaves=0, cutoffs=0, pruned_actions=0,
                tt_hits=0, evals=0, order_evals=0, leaf_evals=0)


class SearchTimeout(Exception):
    pass


class SearchAlgorithm(ABC):
    def __init__(self, evaluator=None, name=None, repeat_aware=False):
        self.evaluator = evaluator if evaluator is not None else TerminalEvaluator()
        self.name = name or type(self).__name__.lower()
        self.repeat_aware = repeat_aware
        self.stats = _new_stats()
        self._deadline = None
        self._history = None
        self._penalty = 0
        self._root_order = []
        self._root_static = {}
        self._best_moves = {}

    def _tick(self):
        if self._deadline is not None and perf_counter() >= self._deadline:
            raise SearchTimeout

    def _evaluate(self, state, me, ordering=False):
        self._tick()
        self.stats['evals'] += 1
        self.stats['order_evals' if ordering else 'leaf_evals'] += 1
        return self.evaluator(state, me)

    def _children(self, state, actions=None):
        for action in state.legal_actions() if actions is None else actions:
            self._tick()
            child = state.apply_action(action, check=False)
            self.stats['generated'] += 1
            yield action, child

    def _leaf_terminal(self, state, depth, me):
        value = self._evaluate(state, me)
        return value + depth if value > 0 else value - depth if value < 0 else 0

    def _prepare_search(self):
        pass

    @abstractmethod
    def value(self, state, depth, me, alpha, beta):
        raise NotImplementedError

    def _order_root(self, state, me):
        scored = []
        for i, action in enumerate(state.legal_actions()):
            self._tick()
            child = state.apply_action(action, check=False)
            self.stats['generated'] += 1
            score = self._evaluate(child, me, ordering=True)
            self._root_static[action] = score
            scored.append((-score, i, action))
        return [a for _, _, a in sorted(scored)]

    def _search_root(self, state, depth, me):
        self._tick()
        self.stats['nodes'] += 1
        best_action, best_score, alpha = None, -INF, -INF
        rows, best_line = [], []
        for action, child in self._children(state, self._root_order):
            penalty = 0
            if self.repeat_aware and self._history and not child.is_terminal():
                penalty = self._penalty * self._history.get(state_key(child), 0)
            before, alpha_before = self.stats['nodes'], alpha
            score = self.value(child, depth - 1, me, alpha + penalty, INF) - penalty
            # A fail-low Alpha-Beta result is an upper bound, not an exact value.
            bound = 'upper' if isinstance(self, AlphaBeta) and score <= alpha_before else 'exact'
            rows.append(dict(action=action.name, score=score, bound=bound,
                             static=self._root_static.get(action),
                             nodes=self.stats['nodes'] - before, penalty=penalty))
            if score > best_score:
                best_action, best_score = action, score
                best_line = self._principal_variation(state, action, depth)
            alpha = max(alpha, score)
        return best_action, best_score, rows, best_line

    def _principal_variation(self, state, action, depth):
        line = []
        current = state
        for remaining in range(depth, 0, -1):
            if action is None or current.is_terminal():
                break
            line.append({'player': current.to_move, 'action': action.name})
            current = current.apply_action(action, check=False)
            action = self._best_moves.get((transposition_key(current), remaining - 1))
        return line

    def search(self, state, depth=4, time_limit_ms=None, history=None, repeat_penalty=0):
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
            raise ValueError('depth phải là số nguyên >= 1')
        if time_limit_ms is not None and (isinstance(time_limit_ms, bool)
                or not isinstance(time_limit_ms, (int, float))
                or not isfinite(time_limit_ms) or time_limit_ms <= 0):
            raise ValueError('time_limit_ms phải là số hữu hạn > 0')
        if (isinstance(repeat_penalty, bool) or not isinstance(repeat_penalty, (int, float))
                or not isfinite(repeat_penalty) or repeat_penalty < 0):
            raise ValueError('repeat_penalty phải là số hữu hạn >= 0')
        start = perf_counter()
        self._deadline = None if time_limit_ms is None else start + time_limit_ms / 1000
        self.stats = _new_stats()
        self._history, self._penalty = history, repeat_penalty
        self._root_static, self._best_moves = {}, {}
        self._prepare_search()
        me = state.to_move
        reached, score, rows, pv = 0, None, [], []
        timed_out = False
        action = None
        if state.is_terminal():
            # Terminal evaluation is constant time for the built-in evaluators.
            self._deadline = None
            self.stats['nodes'] = self.stats['leaves'] = 1
            score = self._evaluate(state, me)
        else:
            legal = state.legal_actions()
            action = legal[0]  # Always have a legal result, even if ordering times out.
            self._root_order = list(legal)
            try:
                self._root_order = self._order_root(state, me)
                action = self._root_order[0]
                score = self._root_static.get(action)
                depths = [depth] if time_limit_ms is None else range(1, depth + 1)
                for d in depths:
                    candidate, value, candidate_rows, candidate_pv = self._search_root(state, d, me)
                    # Commit diagnostics only for completed iterations.
                    action, score, rows, reached, pv = candidate, value, candidate_rows, d, candidate_pv
                    self._root_order = [action] + [a for a in self._root_order if a != action]
            except SearchTimeout:
                timed_out = True
                if reached == 0 and self._root_static:
                    action = max(self._root_static, key=self._root_static.get)
                    score = self._root_static[action]
            finally:
                self._deadline = None
        return action, dict(mode=self.name, depth=depth, depth_reached=reached,
                            score=score, time_ms=(perf_counter() - start) * 1000,
                            timed_out=timed_out, fallback=reached == 0 and action is not None,
                            root_actions=rows, pv=pv, repeat_penalty=repeat_penalty,
                            **self.stats)


class Minimax(SearchAlgorithm):
    def value(self, state, depth, me, alpha, beta):
        self._tick()
        self.stats['nodes'] += 1
        if state.is_terminal() or depth <= 0:
            self.stats['leaves'] += 1
            return self._leaf_terminal(state, depth, me) if state.is_terminal() else self._evaluate(state, me)
        maximizing = state.to_move == me
        best, move = (-INF if maximizing else INF), None
        for action, child in self._children(state):
            value = self.value(child, depth - 1, me, alpha, beta)
            if (maximizing and value > best) or (not maximizing and value < best):
                best, move = value, action
        self._best_moves[(transposition_key(state), depth)] = move
        return best


_EXACT, _LOWER, _UPPER = 0, 1, 2


class AlphaBeta(SearchAlgorithm):
    TT_MIN_DEPTH = 2

    def __init__(self, evaluator=None, name=None, repeat_aware=False, use_tt=True):
        super().__init__(evaluator, name, repeat_aware)
        self.use_tt, self._tt = use_tt, {}

    def _prepare_search(self):
        self._tt = {}

    def value(self, state, depth, me, alpha, beta):
        self._tick()
        key = (transposition_key(state), depth)
        cache = self.use_tt and depth >= self.TT_MIN_DEPTH and not state.is_terminal()
        if cache:
            entry = self._tt.get(key)
            if entry is not None:
                flag, stored, move = entry
                if flag == _EXACT:
                    self.stats['nodes'] += 1
                    self.stats['tt_hits'] += 1
                    self._best_moves[key] = move
                    return stored
                if flag == _LOWER:
                    alpha = max(alpha, stored)
                else:
                    beta = min(beta, stored)
                if alpha >= beta:
                    self.stats['nodes'] += 1
                    self.stats['tt_hits'] += 1
                    return stored
        # Use the effective window for conservative TT bound classification.
        alpha_orig, beta_orig = alpha, beta
        score = self._search_node(state, depth, me, alpha, beta)
        if cache:
            flag = _UPPER if score <= alpha_orig else _LOWER if score >= beta_orig else _EXACT
            self._tt[key] = flag, score, self._best_moves.get(key)
        return score

    def _search_node(self, state, depth, me, alpha, beta):
        self._tick()
        self.stats['nodes'] += 1
        if state.is_terminal() or depth <= 0:
            self.stats['leaves'] += 1
            return self._leaf_terminal(state, depth, me) if state.is_terminal() else self._evaluate(state, me)
        maximizing = state.to_move == me
        best, move = (-INF if maximizing else INF), None
        actions = state.legal_actions()
        for index, (action, child) in enumerate(self._children(state, actions)):
            value = self.value(child, depth - 1, me, alpha, beta)
            if (maximizing and value > best) or (not maximizing and value < best):
                best, move = value, action
            if maximizing:
                alpha = max(alpha, best)
            else:
                beta = min(beta, best)
            if alpha >= beta:
                self.stats['cutoffs'] += 1
                self.stats['pruned_actions'] += len(actions) - index - 1
                break
        self._best_moves[(transposition_key(state), depth)] = move
        return best


MODES = {
    'minimax': (Minimax, TerminalEvaluator, False),
    'alphabeta': (AlphaBeta, TerminalEvaluator, False),
    'heuristic_minimax': (Minimax, HeuristicEvaluator, True),
    'heuristic_alphabeta': (AlphaBeta, HeuristicEvaluator, True),
}


def build_search(mode, evaluator=None):
    if mode not in MODES:
        raise ValueError(f'Mode không hợp lệ: {mode}. Chọn: {list(MODES)}')
    algorithm, default_evaluator, repeat = MODES[mode]
    return algorithm(evaluator if evaluator is not None else default_evaluator(),
                     name=mode, repeat_aware=repeat)


def choose_action(state, depth=4, mode='heuristic_alphabeta', time_limit_ms=None,
                  history=None, repeat_penalty=0, evaluator=None):
    return build_search(mode, evaluator).search(state, depth, time_limit_ms, history, repeat_penalty)
