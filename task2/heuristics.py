"""Zero-sum leaf evaluations. Distances and bullet forecasts are estimates."""
import heapq
from abc import ABC, abstractmethod
from math import ceil

from game import HUONG, EntityKind, TOC_DO_DAN

WIN = 10_000
W = {"base_hp": 100, "tank_hp": 80, "path": 10, "shoot": 30, "bullet": 60}


def bounded(score):
    # A non-terminal estimate must never outrank a terminal win/loss.
    return max(-WIN + 100, min(WIN - 100, score))


class Evaluator(ABC):
    name = "evaluator"

    @abstractmethod
    def evaluate(self, state, me):
        raise NotImplementedError

    def __call__(self, state, me):
        return self.evaluate(state, me)


class TerminalEvaluator(Evaluator):
    """No heuristic: terminal win/loss/draw utility; non-terminal cutoff is 0."""
    name = "terminal_only"

    def evaluate(self, state, me):
        if not state.is_terminal() or state.winner() is None:
            return 0
        return WIN if state.winner() == me else -WIN


class SimpleEvaluator(TerminalEvaluator):
    name = "material"

    def __init__(self, weights=None):
        self.w = dict(W, **(weights or {}))

    def material(self, state, me):
        enemy = 1 - me
        return (self.w["base_hp"] * (state.bases[me].hp - state.bases[enemy].hp)
                + self.w["tank_hp"] * (state.tanks[me].hp - state.tanks[enemy].hp))

    def evaluate(self, state, me):
        if state.is_terminal():
            return super().evaluate(state, me)
        return bounded(self.material(state, me))


class BasicEvaluator(SimpleEvaluator):
    """Cheap baseline: material and Manhattan progress towards the enemy base.

    This is itself a heuristic, not an exhaustive solution of the whole game.
    It deliberately does not solve obstacle routing or forecast flying bullets.
    """
    name = "basic"

    @staticmethod
    def distance(state, player):
        tank, target = state.tanks[player], state.bases[1 - player]
        return abs(tank.r - target.r) + abs(tank.c - target.c)

    def evaluate(self, state, me):
        if state.is_terminal():
            return TerminalEvaluator.evaluate(self, state, me)
        return bounded(self.material(state, me) + self.w["path"] *
                       (self.distance(state, 1 - me) - self.distance(state, me)))


class HeuristicEvaluator(SimpleEvaluator):
    """Material + orientation-aware firing routes + aim + stationary bullet risk."""
    name = "heuristic"
    CACHE_LIMIT = 512
    FORECAST_CYCLES = 3
    UNREACHABLE = 99

    def __init__(self, weights=None):
        super().__init__(weights)
        self._dist_cache = {}

    def attack_cost_map(self, state, player):
        """Reverse Dijkstra on (row, col, direction), seeded by firing positions.

        Move into an empty cell costs 1 and changes direction as in the engine.
        A blocked turn costs 1. Entering brick estimates its HP in FIRE actions,
        plus a blocked turn if needed, then one move. Shooting rays stop at steel
        or the friendly base. Moving tanks are ignored here (a static relaxation);
        exact tactical blocking and damage are handled by search transitions.
        """
        goal = state.bases[1 - player]
        bases = frozenset((b.r, b.c) for b in state.bases if b.hp > 0)
        key = (state.rows, state.cols, state.steel, state.wall_key,
               bases, (goal.r, goal.c))
        if key in self._dist_cache:
            return self._dist_cache[key]
        distances, queue = {}, []

        def offer(node, cost):
            if cost < distances.get(node, float("inf")):
                distances[node] = cost
                heapq.heappush(queue, (cost, node))

        # Each seed already faces the target. Fire + flight + intervening brick HP.
        for outward, (dr, dc) in enumerate(HUONG):
            row, col, steps, brick_hp = goal.r, goal.c, 0, 0
            while True:
                row, col, steps = row + dr, col + dc, steps + 1
                cell = (row, col)
                if not state.in_bounds(row, col) or cell in state.steel or cell in bases:
                    break
                offer((row, col, outward ^ 1), 1 + ceil(steps / TOC_DO_DAN) + brick_hp)
                brick_hp += state.walls.get(cell, 0)

        while queue:
            cost, (row, col, direction) = heapq.heappop(queue)
            if cost != distances[(row, col, direction)]:
                continue
            dr, dc = HUONG[direction]
            previous = (row - dr, col - dc)
            if (state.in_bounds(*previous) and previous not in state.steel
                    and previous not in bases):
                hp = state.walls.get((row, col), 0)
                for old_direction in range(4):
                    turn = int(hp > 0 and old_direction != direction)
                    offer((*previous, old_direction), cost + 1 + hp + turn)
            # In the real game, changing direction without moving is only possible
            # when the requested neighbouring cell is blocked (including edges).
            ahead = (row + dr, col + dc)
            if (not state.in_bounds(*ahead) or ahead in state.steel
                    or ahead in state.walls or ahead in bases):
                for old_direction in range(4):
                    if old_direction != direction:
                        offer((row, col, old_direction), cost + 1)

        if len(self._dist_cache) >= self.CACHE_LIMIT:
            self._dist_cache.clear()
        self._dist_cache[key] = distances
        return distances

    def attack_distance(self, state, player):
        tank = state.tanks[player]
        return min(self.UNREACHABLE, self.attack_cost_map(state, player).get(
            (tank.r, tank.c, tank.d), self.UNREACHABLE))

    @staticmethod
    def _ray_first_hit(state, row, col, direction):
        dr, dc = HUONG[direction]
        steps = 0
        while True:
            row, col, steps = row + dr, col + dc, steps + 1
            if not state.in_bounds(row, col):
                return None, steps
            entity = state.entity_at(row, col)
            if entity is not None:
                return entity, steps

    def shoot_score(self, state, player):
        tank = state.tanks[player]
        entity, distance = self._ray_first_hit(state, tank.r, tank.c, tank.d)
        if entity is None or entity[0] == EntityKind.STEEL:
            return 0.0
        if entity[0] == EntityKind.WALL:
            # A brick hit is useful only if a target lies beyond it on this ray.
            dr, dc = HUONG[tank.d]
            row, col, hp = tank.r + dr * distance, tank.c + dc * distance, 0
            while entity is not None and entity[0] == EntityKind.WALL:
                hp += state.walls[(row, col)]
                entity, steps = self._ray_first_hit(state, row, col, tank.d)
                row, col = row + dr * steps, col + dc * steps
            if entity is None or entity[0] == EntityKind.STEEL:
                return 0.0
            return (0.5 if entity[1] != player else -0.5) / (1 + hp)
        kind, owner = entity
        value = 1.5 if kind == EntityKind.BASE else 1.0
        score = value / (1 + distance / TOC_DO_DAN)
        return score if owner != player else -score

    def bullet_risk(self, state):
        """Discounted damage for each victim if both tanks keep their positions.

        Reuse the actual collision engine on a copy: walls, friendly fire,
        crossing bullets and simultaneous hits have the same semantics as play.
        This is a threat estimate, not a claim that tanks cannot dodge or fire.
        """
        risk = [0.0, 0.0]
        if not state.bullets:
            return risk
        forecast = state.copy()
        for cycle in range(1, self.FORECAST_CYCLES + 1):
            if forecast.is_terminal() or not forecast.bullets:
                break
            tanks, bases = list(forecast.tanks), list(forecast.bases)
            forecast._advance_bullets()
            for p in (0, 1):
                # A hit matters more when the victim is close to destruction.
                risk[p] += ((tanks[p].hp - forecast.tanks[p].hp) * (1 + 1 / max(1, tanks[p].hp))
                            + 1.5 * (bases[p].hp - forecast.bases[p].hp)
                            * (1 + 1 / max(1, bases[p].hp))) / cycle
            forecast.cycle += 1
        return risk

    def evaluate(self, state, me):
        if state.is_terminal():
            return TerminalEvaluator.evaluate(self, state, me)
        enemy = 1 - me
        risk = self.bullet_risk(state)
        score = self.material(state, me)
        score += self.w["path"] * (self.attack_distance(state, enemy) - self.attack_distance(state, me))
        score += self.w["shoot"] * (self.shoot_score(state, me) - self.shoot_score(state, enemy))
        score += self.w["bullet"] * (risk[enemy] - risk[me])
        return bounded(score)
