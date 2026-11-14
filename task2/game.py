from collections import namedtuple
from enum import Enum
class Action(Enum):
    MOVE_UP = 0
    MOVE_DOWN = 1
    MOVE_LEFT = 2
    MOVE_RIGHT = 3
    FIRE = 4
    STAY = 5

class EntityKind(str, Enum):
    WALL = "wall"
    STEEL = "steel"
    TANK = "tank"
    BASE = "base"


HUONG = [(-1, 0), (1, 0), (0, -1), (0, 1)]
HUONG_DI = {
    Action.MOVE_UP: 0,
    Action.MOVE_DOWN: 1,
    Action.MOVE_LEFT: 2,
    Action.MOVE_RIGHT: 3,
}
TANK_HP = 6
BASE_HP = 9
WALL_HP = 3
TOC_DO_DAN = 3
Tank = namedtuple("Tank", "r c d hp")
Base = namedtuple("Base", "r c hp")
Bullet = namedtuple("Bullet", "r c d owner")
DEFAULT_MAP = [
    "   b       ",
    "  W     W  ",
    " WS WWW SW ",
    "           ",
    " WW  W  WW ",
    "           ",
    " WW  W  WW ",
    "           ",
    " WS WWW SW ",
    "  W     W  ",
    "       a   ",
]

class GameState:
    def __init__(self):
        self.rows = self.cols = 0
        self.walls = {}
        self.steel = frozenset()
        self.tanks = []
        self.bases = []
        self.bullets = []
        self.to_move = 0
        self.cycle = 0
        self._wkey = None
        self._term = None

    @classmethod
    def from_layout(cls, layout=None, tank_pos=((10, 5), (0, 5)), base_pos=None):
        if layout is None:
            layout = DEFAULT_MAP
        if not layout or not layout[0]:
            raise ValueError("Bản đồ không được rỗng")
        if any(len(row) != len(layout[0]) for row in layout):
            raise ValueError("Các dòng của bản đồ phải có cùng độ dài")
        s = cls()
        s.rows = len(layout)
        s.cols = len(layout[0])
        steel = set()
        markers = {"a": [], "b": []}
        for r, row in enumerate(layout):
            for c, ch in enumerate(row):
                if ch == "W":
                    s.walls[(r, c)] = WALL_HP
                elif ch == "S":
                    steel.add((r, c))
                elif ch in markers:
                    markers[ch].append((r, c))
                elif ch not in (" ", "."):
                    raise ValueError(f"Ký tự không hợp lệ trong bản đồ: {ch!r}")
        s.steel = frozenset(steel)
        if base_pos is None:
            if len(markers["a"]) != 1 or len(markers["b"]) != 1:
                raise ValueError("Cần đúng một base 'a' và một base 'b', hoặc truyền base_pos")
            base_pos = (markers["a"][0], markers["b"][0])
        if len(tank_pos) != 2 or len(base_pos) != 2:
            raise ValueError("Cần đúng 2 tank và 2 base")
        positions = [tuple(pos) for pos in tank_pos] + [tuple(pos) for pos in base_pos]
        if len(set(positions)) != 4:
            raise ValueError("Tank và base không được nằm trùng ô")
        for r, c in positions:
            if not s.in_bounds(r, c):
                raise ValueError(f"Vị trí nằm ngoài bản đồ: {(r, c)}")
            if (r, c) in s.walls or (r, c) in s.steel:
                raise ValueError(f"Tank/base không được nằm trên tường: {(r, c)}")
        s.tanks = [Tank(*tank_pos[0], 0, TANK_HP), Tank(*tank_pos[1], 1, TANK_HP)]
        s.bases = [Base(*base_pos[0], BASE_HP), Base(*base_pos[1], BASE_HP)]
        return s

    def copy(self):
        n = GameState.__new__(GameState)
        n.rows, n.cols, n.steel = self.rows, self.cols, self.steel
        n.walls = dict(self.walls)
        n.tanks = list(self.tanks)
        n.bases = list(self.bases)
        n.bullets = list(self.bullets)
        n.to_move, n.cycle = self.to_move, self.cycle
        n._wkey = self._wkey
        n._term = None
        return n

    @property
    def wall_key(self):
        if self._wkey is None:
            self._wkey = frozenset(self.walls.items())
        return self._wkey

    def in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def entity_at(self, r, c):
        if (r, c) in self.walls:
            return (EntityKind.WALL, None)
        if (r, c) in self.steel:
            return (EntityKind.STEEL, None)
        for i, t in enumerate(self.tanks):
            if t.hp > 0 and (t.r, t.c) == (r, c):
                return (EntityKind.TANK, i)
        for i, b in enumerate(self.bases):
            if b.hp > 0 and (b.r, b.c) == (r, c):
                return (EntityKind.BASE, i)
        return None

    def is_free(self, r, c):
        return self.in_bounds(r, c) and self.entity_at(r, c) is None

    def is_terminal(self):
        if self._term is None:
            self._term = (any(t.hp <= 0 for t in self.tanks)
                          or any(b.hp <= 0 for b in self.bases))
        return self._term

    def winner(self):
        lost = [self.tanks[p].hp <= 0 or self.bases[p].hp <= 0 for p in (0, 1)]
        if lost[0] and not lost[1]:
            return 1
        if lost[1] and not lost[0]:
            return 0
        return None

    def legal_actions(self):
        if self.is_terminal():
            return []
        t = self.tanks[self.to_move]
        acts = [Action.FIRE]
        for action, d in HUONG_DI.items():
            dr, dc = HUONG[d]
            if self.is_free(t.r + dr, t.c + dc) or d != t.d:
                acts.append(action)
        acts.append(Action.STAY)
        return acts

    def apply_action(self, action, check=True):
        if check:
            if self.is_terminal():
                raise ValueError("Game đã kết thúc, không thể thực hiện action")
            if action not in self.legal_actions():
                raise ValueError(f"Action không hợp lệ: {action}")
        s = self.copy()
        p = s.to_move
        t = s.tanks[p]
        if action == Action.FIRE:
            s.bullets.append(Bullet(t.r, t.c, t.d, p))
        elif action in HUONG_DI:
            d = HUONG_DI[action]
            dr, dc = HUONG[d]
            nr, nc = t.r + dr, t.c + dc
            if s.is_free(nr, nc):
                s.tanks[p] = Tank(nr, nc, d, t.hp)
                hit = [b for b in s.bullets if (b.r, b.c) == (nr, nc)]
                if hit:
                    s.bullets = [b for b in s.bullets if (b.r, b.c) != (nr, nc)]
                    s.tanks[p] = s.tanks[p]._replace(hp=max(0, t.hp - len(hit)))
                    s._term = None
            else:
                s.tanks[p] = Tank(t.r, t.c, d, t.hp)
        if s.is_terminal():
            s.bullets = []
        if p == 1:
            s._advance_bullets()
            s.cycle += 1
        s.to_move = 1 - p
        return s

    def _advance_bullets(self):
        if self.is_terminal():
            self.bullets = []
            return
        bullets = self.bullets
        pos = [(b.r, b.c) for b in bullets]
        alive = [True] * len(bullets)
        for _ in range(TOC_DO_DAN):
            old = list(pos)
            wall_hits = {}
            tank_hits = [0, 0]
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
            for k in (0, 1):
                if tank_hits[k]:
                    self.tanks[k] = self.tanks[k]._replace(hp=max(0, self.tanks[k].hp - tank_hits[k]))
                if base_hits[k]:
                    self.bases[k] = self.bases[k]._replace(hp=max(0, self.bases[k].hp - base_hits[k]))
            if any(tank_hits) or any(base_hits):
                self._term = None
                if self.is_terminal():
                    self.bullets = []
                    return

        self.bullets = [Bullet(pos[i][0], pos[i][1], b.d, b.owner)
                        for i, b in enumerate(bullets) if alive[i]]


class TextRenderer:
    """Vẽ trạng thái game dạng văn bản (tách khỏi GameState)."""

    @staticmethod
    def render(state):
        g = [[" " for _ in range(state.cols)] for _ in range(state.rows)]
        for r, c in state.steel:
            g[r][c] = "S"
        for (r, c), hp in state.walls.items():
            g[r][c] = str(hp)
        for i, b in enumerate(state.bases):
            if b.hp > 0:
                g[b.r][b.c] = "AB"[i]
        for i, t in enumerate(state.tanks):
            if t.hp > 0:
                g[t.r][t.c] = "^v<>"[t.d] if i == 0 else "^V<>"[t.d]
        for b in state.bullets:
            if state.in_bounds(b.r, b.c) and g[b.r][b.c] == " ":
                g[b.r][b.c] = "*"
        return "\n".join("".join(row) for row in g)