from collections import deque
from game import Action, HUONG
MOVES = [Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT]

class GreedyAgent:
    def __init__(self, player_id):
        self.player_id = player_id

    def _first_hit(self, state, tank):
        dr, dc = HUONG[tank.d]
        r, c = tank.r + dr, tank.c + dc
        steps = 1
        while state.in_bounds(r, c):
            entity = state.entity_at(r, c)
            if entity is not None:
                return entity, steps
            r, c, steps = r + dr, c + dc, steps + 1
        return None, steps

    def _next_step(self, state, start, goal):
        queue = deque([start])
        parent = {start: None}
        while queue:
            cell = queue.popleft()
            if cell == goal:
                break
            for d, (dr, dc) in enumerate(HUONG):
                nxt = (cell[0] + dr, cell[1] + dc)
                if nxt in parent or not state.in_bounds(*nxt) or nxt in state.steel:
                    continue
                entity = state.entity_at(*nxt)
                if entity is not None and entity[0] == "tank":
                    continue
                parent[nxt] = (cell, d)
                queue.append(nxt)
        if goal not in parent:
            return None
        cell = goal
        while parent[cell][0] != start:
            cell = parent[cell][0]
        return parent[cell][1]

    def choose_action(self, state):
        me = state.tanks[self.player_id]
        enemy = 1 - self.player_id
        legal = state.legal_actions()

        entity, steps = self._first_hit(state, me)
        if entity is not None:
            kind, owner = entity
            if (kind in ("tank", "base") and owner == enemy) or (kind == "wall" and steps == 1):
                return Action.FIRE

        goal = (state.bases[enemy].r, state.bases[enemy].c)
        d = self._next_step(state, (me.r, me.c), goal)
        if d is not None and MOVES[d] in legal:
            return MOVES[d]
        return Action.STAY if Action.STAY in legal else legal[0]


def create_agent(player_id):
    return GreedyAgent(player_id)