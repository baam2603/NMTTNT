import heapq
from abc import ABC, abstractmethod
from math import ceil

from game import HUONG, EntityKind, TOC_DO_DAN


WIN = 10_000

W = {
    "base_hp": 100,
    "tank_hp": 80,
    "path": 10,
    "shoot": 30,
    "bullet": 60,
}

class Evaluator(ABC):
    name = "evaluator"
    @abstractmethod
    def evaluate(self, state, me):
        raise NotImplementedError
    def __call__(self, state, me):
        return self.evaluate(state, me)

class TerminalEvaluator(Evaluator):
    name = "terminal_only"
    def evaluate(self, state, me):
        if not state.is_terminal():
            return 0
        winner = state.winner()
        if winner is None:
            return 0
        return WIN if winner == me else -WIN

class SimpleEvaluator(Evaluator):
    name = "simple"
    def __init__(self, weights=None):
        self.w = dict(W, **(weights or {}))
    def evaluate(self, state, me):
        enemy = 1 - me
        if state.is_terminal():
            winner = state.winner()
            if winner is None:
                return 0
            return WIN if winner == me else -WIN
        return (
            self.w["base_hp"]
            * (state.bases[me].hp - state.bases[enemy].hp)
            + self.w["tank_hp"]
            * (state.tanks[me].hp - state.tanks[enemy].hp)
        )

class HeuristicEvaluator(SimpleEvaluator):
    name = "heuristic"
    CACHE_LIMIT = 3000
    UNREACHABLE = 99

    def __init__(self, weights=None):
        super().__init__(weights)
        self._dist_cache = {}
    def path_cost_map(self, state, goal):
        key = (
            state.rows,
            state.cols,
            state.steel,
            state.wall_key,
            goal,
        )
        if key in self._dist_cache:
            return self._dist_cache[key]
        if not state.in_bounds(*goal) or goal in state.steel:
            return {}
        distances = {goal: 0}
        queue = [(0, goal)]
        while queue:
            distance, (row, col) = heapq.heappop(queue)
            if distance > distances.get(
                (row, col), float("inf")
            ):
                continue
            enter_cost = 1 + state.walls.get((row, col), 0)

            for dr, dc in HUONG:
                next_row = row + dr
                next_col = col + dc
                cell = (next_row, next_col)
                if (
                    not state.in_bounds(next_row, next_col)
                    or cell in state.steel
                ):
                    continue
                new_distance = distance + enter_cost

                if new_distance < distances.get(
                    cell, float("inf")
                ):
                    distances[cell] = new_distance
                    heapq.heappush(
                        queue, (new_distance, cell)
                    )
        if len(self._dist_cache) >= self.CACHE_LIMIT:
            self._dist_cache.clear()
        self._dist_cache[key] = distances
        return distances

    @staticmethod
    def _ray_first_hit(state, row, col, direction):
        dr, dc = HUONG[direction]
        steps = 0

        while True:
            row += dr
            col += dc
            steps += 1

            if not state.in_bounds(row, col):
                return None, steps
            entity = state.entity_at(row, col)
            if entity is not None:
                return entity, steps

    @staticmethod
    def _behind_wall(
        state, row, col, direction, steps
    ):
        dr, dc = HUONG[direction]
        row += dr * steps
        col += dc * steps
        while True:
            row += dr
            col += dc
            if not state.in_bounds(row, col):
                return None
            entity = state.entity_at(row, col)
            if (
                entity is None
                or entity[0] == EntityKind.WALL
            ):
                continue
            return entity

    def shoot_score(self, state, player):
        tank = state.tanks[player]
        if tank.hp <= 0:
            return 0.0
        entity, distance = self._ray_first_hit(
            state, tank.r, tank.c, tank.d
        )
        if entity is None or entity[0] == EntityKind.STEEL:
            return 0.0
        kind, owner = entity
        if kind == EntityKind.WALL:
            behind = self._behind_wall(
                state,
                tank.r,
                tank.c,
                tank.d,
                distance,
            )
            if (
                behind is None
                or behind[0] == EntityKind.STEEL
            ):
                return 0.0
            if behind[0] in (
                EntityKind.TANK,
                EntityKind.BASE,
            ):
                return (
                    0.15 if behind[1] != player else -0.15
                )
            return 0.0
        closeness = 1.0 / (1.0 + distance / 3.0)
        target_value = (
            1.5 if kind == EntityKind.BASE else 1.0
        )

        score = target_value * closeness
        return score if owner != player else -score

    @staticmethod
    def _head_on(state, bullet, distance):
        dr, dc = HUONG[bullet.d]
        opposite = bullet.d ^ 1

        for other in state.bullets:
            if other.d != opposite:
                continue
            for step in range(1, distance):
                cell = (
                    bullet.r + dr * step,
                    bullet.c + dc * step,
                )

                if (other.r, other.c) == cell:
                    return True

        return False

    def incoming(self, state, shooter):
        total = 0.0

        for bullet in state.bullets:
            if bullet.owner != shooter:
                continue

            entity, distance = self._ray_first_hit(
                state,
                bullet.r,
                bullet.c,
                bullet.d,
            )

            if entity is None or entity[0] not in (
                EntityKind.TANK,
                EntityKind.BASE,
            ):
                continue

            if self._head_on(state, bullet, distance):
                continue
            kind, victim = entity
            cycles = max(1, ceil(distance / TOC_DO_DAN))
            target_value = (
                1.5 if kind == EntityKind.BASE else 1.0
            )
            signed_value = (
                target_value
                if victim != shooter
                else -target_value
            )

            total += signed_value / cycles
        return total

    def evaluate(self, state, me):
        score = super().evaluate(state, me)
        if state.is_terminal():
            return score
        enemy = 1 - me
        my_map = self.path_cost_map(
            state,
            (state.bases[enemy].r, state.bases[enemy].c),
        )
        enemy_map = self.path_cost_map(
            state,
            (state.bases[me].r, state.bases[me].c),
        )

        my_distance = min(
            my_map.get(
                (state.tanks[me].r, state.tanks[me].c),
                self.UNREACHABLE,
            ),
            self.UNREACHABLE,
        )
        enemy_distance = min(
            enemy_map.get(
                (state.tanks[enemy].r, state.tanks[enemy].c),
                self.UNREACHABLE,
            ),
            self.UNREACHABLE,
        )
        score += self.w["path"] * (
            enemy_distance - my_distance
        )
        score += self.w["shoot"] * (
            self.shoot_score(state, me)
            - self.shoot_score(state, enemy)
        )
        score += self.w["bullet"] * (
            self.incoming(state, me)
            - self.incoming(state, enemy)
        )
        # Terminal wins/losses must dominate every non-terminal estimate.
        return max(-WIN + 100, min(WIN - 100, score))