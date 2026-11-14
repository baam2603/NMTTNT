import importlib
from abc import ABC, abstractmethod
from time import perf_counter

from game import Action, GameState
from search import choose_action, state_key


class Agent(ABC):
    name = "agent"

    def reset(self, player):
        """Gọi đầu mỗi trận; player = 0 hoặc 1."""

    @abstractmethod
    def act(self, state, time_limit_ms=None, history=None):
        """Trả về Action (hoặc (Action, info_dict))."""


class SearchAgent(Agent):
    def __init__(self, mode="heuristic_alphabeta", depth=4,
                 repeat_penalty=30, evaluator=None):
        self.mode, self.depth = mode, depth
        self.repeat_penalty, self.evaluator = repeat_penalty, evaluator
        self.name = mode

    def act(self, state, time_limit_ms=None, history=None):
        return choose_action(
            state, depth=self.depth, mode=self.mode,
            time_limit_ms=time_limit_ms, history=history,
            repeat_penalty=self.repeat_penalty, evaluator=self.evaluator,
        )


class FunctionAgent(Agent):
    def __init__(self, fn, name=None):
        self.fn = fn
        self.name = name or getattr(fn, "__name__", "function_agent")

    def act(self, state, time_limit_ms=None, history=None):
        return self.fn(state)


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
        def act(self, state, time_limit_ms=None, history=None):
            return obj.act(state)
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
               time_limit_ms=None, verbose=False):
    state = state or GameState.from_layout()
    agents = (agent0, agent1)
    for p, a in enumerate(agents):
        a.reset(p)

    history = {state_key(state): 1}
    faults = [0, 0]
    overtime = [0, 0]
    plies = 0

    while not state.is_terminal() and plies < max_plies:
        p = state.to_move
        legal = state.legal_actions()
        t0 = perf_counter()
        try:
            out = agents[p].act(state.copy(), time_limit_ms, dict(history))
            action = _to_action(out[0] if isinstance(out, tuple) else out)
            if action not in legal:
                raise ValueError("action không hợp lệ")
        except Exception:
            faults[p] += 1
            action = Action.STAY
        if time_limit_ms and (perf_counter() - t0) * 1000 > time_limit_ms * 1.5:
            overtime[p] += 1

        state = state.apply_action(action)
        k = state_key(state)
        history[k] = history.get(k, 0) + 1
        plies += 1
        if verbose:
            print(f"#{plies} P{p} {agents[p].name}: {action.name}")

    return {"winner": state.winner(), "plies": plies,
            "faults": faults, "overtime": overtime, "final": state}