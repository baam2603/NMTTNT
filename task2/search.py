from abc import ABC, abstractmethod
from math import isfinite
from time import perf_counter

from heuristics import HeuristicEvaluator, TerminalEvaluator

INF = float("inf")


def state_key(state):
    """Khóa trạng thái (bỏ cycle vì cycle không ảnh hưởng động lực game).
    Dùng cho cả lịch sử lặp lẫn bảng chuyển vị."""
    return (
        tuple(state.tanks),
        tuple(state.bases),
        tuple(sorted(state.bullets)),
        state.wall_key,
        state.to_move,
    )


def _new_stats():
    return {
        "nodes": 0,
        "generated": 0,
        "leaves": 0,
        "cutoffs": 0,
        "pruned_actions": 0,
        "tt_hits": 0,
    }


class SearchTimeout(Exception):
    pass


class SearchAlgorithm(ABC):
    def __init__(self, evaluator=None, name=None, repeat_aware=False):
        self.evaluator = (
            evaluator if evaluator is not None else TerminalEvaluator()
        )
        self.name = name or type(self).__name__.lower()
        self.repeat_aware = repeat_aware
        self.stats = _new_stats()
        self._deadline = None
        self._history = None
        self._penalty = 0
        self._root_order = []

    def _tick(self):
        if self._deadline is not None and perf_counter() > self._deadline:
            raise SearchTimeout

    def _children(self, state, actions=None):
        if actions is None:
            actions = state.legal_actions()
        for action in actions:
            self._tick()
            child = state.apply_action(action, check=False)
            self.stats["generated"] += 1
            yield action, child

    def _leaf_terminal(self, state, depth, me):
        """Thắng sớm / thua muộn: cộng-trừ depth còn lại."""
        value = self.evaluator(state, me)
        if value > 0:
            return value + depth
        if value < 0:
            return value - depth
        return value

    def _prepare_search(self):
        """Hook đầu mỗi lần search (xóa bảng chuyển vị...)."""

    @abstractmethod
    def value(self, state, depth, me, alpha, beta):
        raise NotImplementedError

    def _order_root(self, state, me):
        scored = []
        for i, action in enumerate(state.legal_actions()):
            child = state.apply_action(action, check=False)
            scored.append((-self.evaluator(child, me), i, action))
        scored.sort(key=lambda x: (x[0], x[1]))
        return [a for _, _, a in scored]

    def _search_root(self, state, depth, me):
        best_action, best_score = None, -INF
        alpha, beta = -INF, INF

        for action, child in self._children(state, self._root_order):
            penalty = 0
            if self.repeat_aware and self._history and not child.is_terminal():
                penalty = self._penalty * self._history.get(state_key(child), 0)

            score = self.value(child, depth - 1, me, alpha + penalty, beta)
            score -= penalty
            alpha = max(alpha, score)

            if score > best_score:
                best_score, best_action = score, action

        return best_action, best_score
    def search(self, state, depth=4, time_limit_ms=None,
               history=None, repeat_penalty=30):
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
            raise ValueError("depth phải là số nguyên >= 1")
        if time_limit_ms is not None and (
            isinstance(time_limit_ms, bool)
            or not isinstance(time_limit_ms, (int, float))
            or not isfinite(time_limit_ms)
            or time_limit_ms <= 0
        ):
            raise ValueError("time_limit_ms phải là số hữu hạn > 0")
        if (
            isinstance(repeat_penalty, bool)
            or not isinstance(repeat_penalty, (int, float))
            or not isfinite(repeat_penalty)
            or repeat_penalty < 0
        ):
            raise ValueError("repeat_penalty phải là số hữu hạn >= 0")

        self._deadline = None
        self.stats = _new_stats()
        self._history = history
        self._penalty = repeat_penalty
        self._prepare_search()

        start = perf_counter()

        if state.is_terminal():
            self.stats["nodes"] = 1
            self.stats["leaves"] = 1
            return None, {
                "mode": self.name, "depth": depth, "depth_reached": 0,
                "score": self.evaluator(state, state.to_move),
                "time_ms": 0.0, **self.stats,
            }

        me = state.to_move
        self.stats["nodes"] = 1
        self._root_order = self._order_root(state, me)

        if time_limit_ms is None:
            best_action, best_score = self._search_root(state, depth, me)
            reached = depth
        else:
            best_action = self._root_order[0]
            best_score = self.evaluator(
                state.apply_action(best_action, check=False), me
            )
            reached = 0
            self._deadline = start + time_limit_ms / 1000
            try:
                for d in range(1, depth + 1):
                    action, score = self._search_root(state, d, me)
                    best_action, best_score, reached = action, score, d
            except SearchTimeout:
                pass
            finally:
                self._deadline = None

        return best_action, {
            "mode": self.name, "depth": depth, "depth_reached": reached,
            "score": best_score,
            "time_ms": (perf_counter() - start) * 1000,
            **self.stats,
        }


class Minimax(SearchAlgorithm):
    def value(self, state, depth, me, alpha, beta):
        self._tick()
        self.stats["nodes"] += 1

        if state.is_terminal():
            self.stats["leaves"] += 1
            return self._leaf_terminal(state, depth, me)
        if depth <= 0:
            self.stats["leaves"] += 1
            return self.evaluator(state, me)

        maximizing = state.to_move == me
        best = -INF if maximizing else INF
        for _, child in self._children(state):
            score = self.value(child, depth - 1, me, alpha, beta)
            best = max(best, score) if maximizing else min(best, score)
        return best


_EXACT, _LOWER, _UPPER = 0, 1, 2


class AlphaBeta(SearchAlgorithm):
    TT_MIN_DEPTH = 2

    def __init__(self, evaluator=None, name=None, repeat_aware=False,
                 use_tt=True):
        super().__init__(evaluator, name, repeat_aware)
        self.use_tt = use_tt
        self._tt = {}

    def _prepare_search(self):
        self._tt = {}

    def value(self, state, depth, me, alpha, beta):
        if (not self.use_tt or depth < self.TT_MIN_DEPTH
                or state.is_terminal()):
            return self._search_node(state, depth, me, alpha, beta)

        key = (state_key(state), depth)
        alpha_orig = alpha
        entry = self._tt.get(key)

        if entry is not None:
            flag, stored = entry
            if flag == _EXACT:
                self.stats["nodes"] += 1
                self.stats["tt_hits"] += 1
                return stored
            if flag == _LOWER:
                alpha = max(alpha, stored)
            else:
                beta = min(beta, stored)
            if alpha >= beta:
                self.stats["nodes"] += 1
                self.stats["tt_hits"] += 1
                return stored

        score = self._search_node(state, depth, me, alpha, beta)

        if score <= alpha_orig:
            flag = _UPPER
        elif score >= beta:
            flag = _LOWER
        else:
            flag = _EXACT
        self._tt[key] = (flag, score)
        return score

    def _search_node(self, state, depth, me, alpha, beta):
        self._tick()
        self.stats["nodes"] += 1

        if state.is_terminal():
            self.stats["leaves"] += 1
            return self._leaf_terminal(state, depth, me)
        if depth <= 0:
            self.stats["leaves"] += 1
            return self.evaluator(state, me)

        actions = state.legal_actions()
        n = len(actions)
        maximizing = state.to_move == me
        best = -INF if maximizing else INF

        for index, (_, child) in enumerate(self._children(state, actions)):
            score = self.value(child, depth - 1, me, alpha, beta)
            if maximizing:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)
            if alpha >= beta:
                self.stats["cutoffs"] += 1
                self.stats["pruned_actions"] += n - index - 1
                break
        return best

MODES = {
    "minimax": (Minimax, TerminalEvaluator, False),
    "alphabeta": (AlphaBeta, TerminalEvaluator, False),
    "heuristic_minimax": (Minimax, HeuristicEvaluator, True),
    "heuristic_alphabeta": (AlphaBeta, HeuristicEvaluator, True),
}


def build_search(mode, evaluator=None):
    """evaluator: truyền Evaluator tùy ý (vd. của nhóm khác) để thay mặc định."""
    if mode not in MODES:
        raise ValueError(f"Mode không hợp lệ: {mode}. Chọn: {list(MODES)}")
    algorithm_cls, evaluator_cls, repeat_aware = MODES[mode]
    return algorithm_cls(
        evaluator if evaluator is not None else evaluator_cls(),
        name=mode,
        repeat_aware=repeat_aware,
    )


def choose_action(state, depth=4, mode="heuristic_alphabeta",
                  time_limit_ms=None, history=None, repeat_penalty=30,
                  evaluator=None):
    return build_search(mode, evaluator).search(
        state, depth=depth, time_limit_ms=time_limit_ms,
        history=history, repeat_penalty=repeat_penalty,
    )


if __name__ == "__main__":
    from game import GameState

    state = GameState.from_layout()
    for mode in MODES:
        action, info = choose_action(state, depth=4, mode=mode)
        print(f"{mode:22s} -> {action.name:12s} | score={info['score']:8.1f} | "
              f"nodes={info['nodes']:7d} | time={info['time_ms']:8.2f} ms")