
from game import GameState, Action, Tank, Bullet, HUONG, HUONG_DI, TOC_DO_DAN, EntityKind
NPC_MODES = ("minimax", "heuristic_minimax", "alphabeta", "heuristic_alphabeta")

class ArenaState(GameState):
    @classmethod
    def from_state(cls, state):
        s = cls()
        s.__dict__.update(state.copy().__dict__)
        # Place NPCs near the original enemy, using BFS over free cells.
        seed = (s.tanks[1].r, s.tanks[1].c)
        cells, seen, queue = [seed], {seed}, [seed]
        while queue and len(cells) < 4:
            r, c = queue.pop(0)
            for dr, dc in HUONG:
                cell = (r + dr, c + dc)
                if cell in seen or not s.in_bounds(*cell):
                    continue
                seen.add(cell)
                if s.is_free(*cell):
                    queue.append(cell)
                    if len(cells) < 4:
                        cells.append(cell)
        if len(cells) != 4:
            raise ValueError("Map has insufficient free cells for four NPCs")
        enemy = s.tanks[1]
        s.tanks = [s.tanks[0]] + [Tank(r, c, enemy.d, enemy.hp) for r, c in cells]
        s._term = None
        return s

    def copy(self):
        n = ArenaState()
        n.__dict__.update(super().copy().__dict__)
        return n

    def is_terminal(self):
        return (self.tanks[0].hp <= 0 or all(t.hp <= 0 for t in self.tanks[1:])
                or any(b.hp <= 0 for b in self.bases))

    def winner(self):
        human_lost = self.tanks[0].hp <= 0 or self.bases[0].hp <= 0
        npc_lost = all(t.hp <= 0 for t in self.tanks[1:]) or self.bases[1].hp <= 0
        if human_lost != npc_lost:
            return 1 if human_lost else 0
        return None

    def termination_reason(self):
        human = self.tanks[0].hp <= 0 or self.bases[0].hp <= 0
        npcs = all(t.hp <= 0 for t in self.tanks[1:]) or self.bases[1].hp <= 0
        if human and npcs:
            return 'mutual_destruction'
        if human or npcs:
            return 'destroyed'
        return None

    def apply_action(self, action, check=True):
        if check and (self.is_terminal() or action not in self.legal_actions()):
            raise ValueError("Invalid arena action")
        s = self.copy()
        p, t = s.to_move, s.tanks[s.to_move]
        if action == Action.FIRE:
            s.bullets.append(Bullet(t.r, t.c, t.d, p))
        elif action in HUONG_DI:
            d = HUONG_DI[action]
            dr, dc = HUONG[d]
            nr, nc = t.r + dr, t.c + dc
            if s.is_free(nr, nc):
                hits = [b for b in s.bullets if (b.r, b.c) == (nr, nc)]
                s.bullets = [b for b in s.bullets if (b.r, b.c) != (nr, nc)]
                s.tanks[p] = Tank(nr, nc, d, max(0, t.hp - len(hits)))
            else:
                s.tanks[p] = t._replace(d=d)
        if s.is_terminal():
            s.bullets = []
            return s
        next_player = p + 1
        while next_player < len(s.tanks) and s.tanks[next_player].hp <= 0:
            next_player += 1
        if next_player == len(s.tanks):
            s._advance_bullets()
            s.cycle += 1
            next_player = 0
        s.to_move = next_player
        return s

    def _advance_bullets(self):
        # Reuse the original simultaneous bullet rules for N tanks: the engine's
        # implementation is supplied below with only hit-array sizes generalized.
        return _advance_arena_bullets(self)

    def duel_view(self, npc):
        """Human = side 0, current NPC = side 1, shared team bases unchanged."""
        s = GameState()
        s.__dict__.update(super().copy().__dict__)
        s.tanks = [self.tanks[0], self.tanks[npc]]
        s.steel = self.steel | frozenset((t.r, t.c) for i, t in enumerate(self.tanks)
                                        if i not in (0, npc) and t.hp > 0)
        s.bullets = [b._replace(owner=0 if b.owner == 0 else 1) for b in self.bullets]
        s.to_move = 1
        s._term = None
        return s


def _advance_arena_bullets(self):
    if self.is_terminal():
        self.bullets = []
        return
    bullets = self.bullets
    pos = [(b.r, b.c) for b in bullets]
    alive = [True] * len(bullets)
    for _ in range(TOC_DO_DAN):
        old = list(pos)
        wall_hits = {}
        tank_hits = [0] * len(self.tanks)
        base_hits = [0, 0]
        flying = []
        for i, b in enumerate(bullets):
            if not alive[i]:
                continue
            dr, dc = HUONG[b.d]
            r, c = old[i][0] + dr, old[i][1] + dc
            pos[i] = (r, c)
            if not self.in_bounds(r, c):
                alive[i] = False
                continue
            entity = self.entity_at(r, c)
            if entity is None:
                flying.append(i)
                continue
            kind, k = entity
            if kind == EntityKind.WALL:
                wall_hits[(r, c)] = wall_hits.get((r, c), 0) + 1
            elif kind == EntityKind.TANK:
                tank_hits[k] += 1
            elif kind == EntityKind.BASE:
                base_hits[k] += 1
            alive[i] = False

        cells = {}
        for i in flying:
            cells.setdefault(pos[i], []).append(i)
        for group in cells.values():
            if len(group) > 1:
                for i in group:
                    alive[i] = False
        for x, i in enumerate(flying):
            for j in flying[x + 1:]:
                if pos[i] == old[j] and pos[j] == old[i]:
                    alive[i] = alive[j] = False

        for cell, n in wall_hits.items():
            self.walls[cell] -= n
            if self.walls[cell] <= 0:
                del self.walls[cell]
            self._wkey = None
        for k in range(len(self.tanks)):
            if tank_hits[k]:
                self.tanks[k] = self.tanks[k]._replace(hp=max(0, self.tanks[k].hp - tank_hits[k]))
        for k in (0, 1):
            if base_hits[k]:
                self.bases[k] = self.bases[k]._replace(hp=max(0, self.bases[k].hp - base_hits[k]))
        if any(tank_hits) or any(base_hits):
            self._term = None
            if self.is_terminal():
                self.bullets = []
                return

    self.bullets = [Bullet(pos[i][0], pos[i][1], b.d, b.owner)
                    for i, b in enumerate(bullets) if alive[i]]
