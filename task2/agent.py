import importlib
import inspect
from abc import ABC, abstractmethod
from time import perf_counter

from game import Action, GameState
from search import build_search, state_key


class Agent(ABC):
    name = "agent"

    def reset(self, player):
        """Gọi đầu mỗi trận; player = 0 hoặc 1."""

    @abstractmethod
    def act(self, state, time_limit_ms=None, history=None):
        """Trả về Action (hoặc (Action, info_dict))."""


class SearchAgent(Agent):
    def __init__(self, mode="heuristic_alphabeta", depth=4,
                 evaluator=None, track_pv=True):
        self.mode, self.depth = mode, depth
        self.evaluator, self.track_pv = evaluator, track_pv
        self.name = mode
        self.engine = build_search(mode, evaluator)

    def reset(self, player):
        self.engine = build_search(self.mode, self.evaluator)

    def act(self, state, time_limit_ms=None, history=None):
        return self.engine.search(
            state, depth=self.depth, time_limit_ms=time_limit_ms,
            track_pv=self.track_pv,
        )


def call_external(fn, state, time_limit_ms=None, history=None):
    params = inspect.signature(fn).parameters
    arbitrary = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    kwargs = {k: v for k, v in {"time_limit_ms": time_limit_ms, "history": history}.items()
              if arbitrary or k in params}
    return fn(state, **kwargs)


class FunctionAgent(Agent):
    def __init__(self, fn, name=None):
        self.fn = fn
        self.name = name or getattr(fn, "__name__", "function_agent")

    def act(self, state, time_limit_ms=None, history=None):
        return call_external(self.fn, state, time_limit_ms, history)


def load_agent(spec, **kwargs):
    module_name, _, attr = spec.partition(":")
    if not attr:
        raise ValueError("spec phải có dạng 'module:attr'")
    obj = getattr(importlib.import_module(module_name), attr)
    if isinstance(obj, type) and issubclass(obj, Agent):
        return obj(**kwargs)
    if isinstance(obj, Agent):
        return obj
    if hasattr(obj, "act"):
        return _wrap_duck(obj)
    if callable(obj):
        return FunctionAgent(obj, name=spec)
    raise TypeError(f"Không dùng được {spec} làm Agent")


def _wrap_duck(obj):
    class Duck(Agent):
        name = type(obj).__name__
        def reset(self, player):
            if hasattr(obj, 'reset'):
                obj.reset(player)
        def act(self, state, time_limit_ms=None, history=None):
            return call_external(obj.act, state, time_limit_ms, history)
    return Duck()


def _to_action(raw):
    if isinstance(raw, Action):
        return raw
    if isinstance(raw, int):
        return Action(raw)
    if isinstance(raw, str):
        return Action[raw.upper()]
    raise ValueError(f"Không hiểu action: {raw!r}")


def play_match(agent0, agent1, state=None, max_plies=400,
               time_limit_ms=None, verbose=False, max_cycles=None):
    for label, limit in (("max_plies", max_plies), ("max_cycles", max_cycles)):
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            raise ValueError(label + " phải là số nguyên dương hoặc None")
    state = state or GameState.from_layout()
    start_cycle = state.cycle
    agents = (agent0, agent1)
    for p, a in enumerate(agents):
        a.reset(p)

    history = {state_key(state): 1}
    faults = [0, 0]
    overtime = [0, 0]
    plies = 0
    metrics = [{"time_ms": 0.0, "nodes": 0, "evals": 0, "order_evals": 0, "leaf_evals": 0, "moves": 0, "depth_sum": 0} for _ in agents]

    while (not state.is_terminal()
           and (max_plies is None or plies < max_plies)
           and (max_cycles is None or state.cycle - start_cycle < max_cycles)):
        p = state.to_move
        legal = state.legal_actions()
        t0 = perf_counter()
        try:
            out = agents[p].act(state.copy(), time_limit_ms, dict(history))
            info = out[1] if isinstance(out, tuple) else {}
            if not isinstance(info, dict):
                raise ValueError("Agent info must be a dictionary")
            action = _to_action(out[0] if isinstance(out, tuple) else out)
            if action not in legal:
                raise ValueError("action không hợp lệ")
        except Exception:
            faults[p] += 1
            info = {}
            action = Action.STAY
        elapsed = (perf_counter() - t0) * 1000
        metrics[p]["time_ms"] += elapsed
        metrics[p]["moves"] += 1
        metrics[p]["nodes"] += info.get("nodes", 0)
        for key in ("evals", "order_evals", "leaf_evals"):
            metrics[p][key] += info.get(key, 0)
        metrics[p]["depth_sum"] += info.get("depth_reached", 0)
        if time_limit_ms and elapsed > time_limit_ms * 1.1:
            overtime[p] += 1

        state = state.apply_action(action)
        k = state_key(state)
        history[k] = history.get(k, 0) + 1
        plies += 1
        if verbose:
            print(f"#{plies} P{p} {agents[p].name}: {action.name}")

    completed = state.is_terminal()
    reason = (state.termination_reason() if completed else
              "experiment_cycle_limit" if max_cycles is not None and state.cycle - start_cycle >= max_cycles
              else "experiment_ply_limit")
    return {"winner": state.winner() if completed else None, "plies": plies,
            "status": "finished" if completed else "stopped",
            "faults": faults, "overtime": overtime, "metrics": metrics,
            "reason": reason,
            "final": state}