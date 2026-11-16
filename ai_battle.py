import os
import importlib.util
import inspect
import sys
import threading
from pathlib import Path
from time import perf_counter

HERE = Path(__file__).resolve().parent

CORE_MODULES = {"game", "agent", "search", "heuristics", "benchmark", "__init__"}

def find_task2_dir():
    """Tim thu muc task2 (chua game.py va agent.py)."""
    candidates = []
    env = os.environ.get("TASK2_DIR")
    if env:
        candidates.append(Path(env))
    candidates += [HERE / "task2", HERE.parent / "task2"]
    for path in candidates:
        if (path / "game.py").is_file() and (path / "agent.py").is_file():
            return path
    return None


class Task2Backend(object):
    """Nap task2 va cung cap cac thao tac can thiet cho giao dien."""

    SHORT = {
        "minimax": "MINIMAX",
        "alphabeta": "ALPHA-BETA",
        "heuristic_minimax": "H-MINIMAX",
        "heuristic_alphabeta": "H-ALPHABETA",
    }
    LONG = {
        "minimax": "MINIMAX (NO HEURISTIC)",
        "alphabeta": "ALPHA-BETA (NO HEURISTIC)",
        "heuristic_minimax": "HEURISTIC MINIMAX",
        "heuristic_alphabeta": "HEURISTIC ALPHA-BETA",
    }

    def __init__(self, task2_dir):
        self.dir = Path(task2_dir)
        if str(self.dir) not in sys.path:
            sys.path.insert(0, str(self.dir))
        import game as game_mod
        import agent as agent_mod
        import search as search_mod
        self.game = game_mod
        self.agent = agent_mod
        self.search = search_mod
        try:
            import benchmark as benchmark_mod
            self._build_scenarios = lambda: benchmark_mod.build_scenarios(include_original=False)
            from original_maps import original_map_names
            self.maps = (["default"] + [n for n in self._build_scenarios() if n != "default"]
                         + original_map_names())
        except Exception:
            self._build_scenarios = None
            self.maps = ["default"]

    # ---- ban do ----
    def new_state(self, map_name):
        if map_name.startswith("original_"):
            from original_maps import load_original_level
            return load_original_level(int(map_name.split("_")[1]))
        if map_name != "default" and self._build_scenarios is not None:
            return self._build_scenarios()[map_name]
        return self.game.GameState.from_layout()

    # ---- agent ----
    def agent_options(self):
        """Danh sach lua chon agent cho man hinh setup."""
        options = []
        for mode in self.search.MODES:
            options.append({"kind": "search", "mode": mode,
                            "label": self.LONG.get(mode, mode.upper()),
                            "short": self.SHORT.get(mode, mode.upper())})
        seen = set()
        folders = [self.dir, self.dir / "agents", HERE / "agents"]
        for folder in folders:
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.py")):
                real = path.resolve()
                if real in seen or path.stem in CORE_MODULES or path.stem == "search":
                    continue
                seen.add(real)
                try:
                    src = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "create_agent" not in src and "def choose_action" not in src and "def act(" not in src:
                    continue
                options.append({"kind": "file", "path": str(path),
                                "label": "FILE: " + path.name,
                                "short": "EXT:" + path.stem[:10].upper()})
        return options

    def create_agent(self, option, player_id, depth):
        if option["kind"] == "human":
            return None
        if option["kind"] == "search":
            # Adapt the existing Agent.act API without changing the algorithms.
            agent = self.agent.SearchAgent(mode=option["mode"], depth=depth)
            agent.reset(player_id)
            return agent
        path = Path(option["path"])
        spec = importlib.util.spec_from_file_location(
            "battle_external_" + path.stem, path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        obj = module.create_agent(player_id) if hasattr(module, "create_agent") else module
        if hasattr(obj, "reset"):
            obj.reset(player_id)
        return ExternalAgentAdapter(obj)


class ExternalAgentAdapter:
    def __init__(self, obj):
        self.obj = obj

    def act(self, state, time_limit_ms=None, history=None):
        fn = self.obj.choose_action if hasattr(self.obj, "choose_action") else self.obj.act
        params = inspect.signature(fn).parameters
        arbitrary = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        kwargs = {k: v for k, v in {"time_limit_ms": time_limit_ms, "history": history}.items()
                  if arbitrary or k in params}
        out = fn(state, **kwargs)
        return out if isinstance(out, tuple) else (out, getattr(self.obj, "last_info", {}))


# --------------------------------------------------------------------------- #
#  Match: dieu khien mot van dau (khong phu thuoc pygame)
# --------------------------------------------------------------------------- #
class Match(object):
    def __init__(self, backend, state, agents, options, depths, time_limit_ms=60, max_cycles=None):
        self.backend = backend
        self.time_limit_ms = time_limit_ms
        self.state = state
        self.max_cycles, self.start_cycle = max_cycles, state.cycle
        self.prev_state = None
        self.agents = agents            # [agent | None (human), agent | None]
        self.options = options
        self.depths = depths
        self.events = []                # [(r, c, kind)] cua nuoc di gan nhat
        self.mover = None               # nguoi vua di
        self.last_action = None
        self.last = [{} for _ in agents]            # thong tin nuoc di gan nhat moi ben
        self.error = None
        self.thinking = False
        self._token = 0
        self._result = None
        self._thread = None
        self.arena = len(state.tanks) > 2
        self.npc_history = {p: {} for p in range(1, len(state.tanks))}
        self.history = {backend.search.state_key(state): 1}

    # ---- trang thai ----
    def is_human(self, player):
        return self.agents[player] is None

    def current_is_human(self):
        return not self.is_over() and self.is_human(self.state.to_move)

    def is_over(self):
        return (self.state.is_terminal() or (self.max_cycles is not None
                and self.state.cycle - self.start_cycle >= self.max_cycles))

    def result_text(self):
        """(tieu de, ly do) cua van dau da ket thuc."""
        s = self.state
        if not s.is_terminal() and self.is_over():
            return "STOPPED", "Experiment limit (%d cycles), no winner" % self.max_cycles
        winner = s.winner()
        if winner is None:
            return "DRAW", "Both sides lost at the same time"
        if self.arena:
            return (("PLAYER WINS", "NPC team defeated") if winner == 0 else
                    ("NPC TEAM WINS", "Player tank or base destroyed"))
        loser = 1 - winner
        reasons = []
        if s.tanks[loser].hp <= 0:
            reasons.append("tank P%d destroyed" % loser)
        if s.bases[loser].hp <= 0:
            reasons.append("base P%d destroyed" % loser)
        return "P%d WINS" % winner, " + ".join(reasons)

    # ---- nuoc di ----
    def _apply(self, action, info):
        prev = self.state
        mover = prev.to_move
        new = prev.apply_action(action)
        self.prev_state = prev
        self.state = new
        key = self.backend.search.state_key(new)
        self.history[key] = self.history.get(key, 0) + 1
        if self.arena and new.to_move > 0 and not new.is_terminal():
            view_key = self.backend.search.state_key(new.duel_view(new.to_move))
            hist = self.npc_history[new.to_move]
            hist[view_key] = hist.get(view_key, 0) + 1
        self.mover = mover
        self.last_action = action
        self.events = self._diff(prev, new)
        data = dict(info)
        data["action"] = action.name
        self.last[mover] = data

    @staticmethod
    def _diff(prev, new):
        events = []
        for cell, hp in prev.walls.items():
            if new.walls.get(cell, 0) < hp:
                events.append((cell[0], cell[1], "wall"))
        for i in range(len(new.tanks)):
            if new.tanks[i].hp < prev.tanks[i].hp:
                events.append((new.tanks[i].r, new.tanks[i].c, "tank"))
        for i in (0, 1):
            if new.bases[i].hp < prev.bases[i].hp:
                events.append((new.bases[i].r, new.bases[i].c, "base"))
        return events

    def submit_human_action(self, action):
        """Nguoi choi chon hanh dong. Tra ve True neu hop le."""
        if not self.current_is_human() or self.error:
            return False
        if action not in self.state.legal_actions():
            return False
        self._apply(action, {})
        return True

    def request_ai_move(self):
        """Chay agent o luong rieng de giao dien khong bi dung hinh."""
        if self.thinking or self.is_over() or self.error or self.current_is_human():
            return
        self._token += 1
        token = self._token
        state = self.state.copy()
        agent = self.agents[state.to_move]
        history = dict(self.history)
        if self.arena:
            history = dict(self.npc_history[state.to_move])
            state = state.duel_view(state.to_move)
        self._result = None
        self.thinking = True

        def work():
            try:
                out = agent.act(state, time_limit_ms=self.time_limit_ms, history=history)
                action, info = out if isinstance(out, tuple) else (out, {})
                result = (token, action, dict(info), None)
            except Exception as exc:  # noqa: BLE001 - hien loi len giao dien
                result = (token, None, {}, exc)
            if token == self._token:
                self._result = result

        self._thread = threading.Thread(target=work, daemon=True)
        self._thread.start()

    def poll(self):
        """Kiem tra agent da tra loi chua. Tra ve True neu trang thai vua doi."""
        result = self._result
        if not self.thinking or result is None or result[0] != self._token:
            return False
        self._result = None
        self.thinking = False
        _, action, info, exc = result
        if exc is not None:
            self.error = "P%d: %s" % (self.state.to_move, exc)
            return False
        if action is None:
            self.error = "P%d: agent returned no action" % self.state.to_move
            return False
        try:
            self._apply(self.backend.agent._to_action(action), info)
        except Exception as exc2:  # noqa: BLE001
            self.error = "P%d: %s" % (self.state.to_move, exc2)
            return False
        return True

    def abort(self):
        """Huy ket qua dang cho (vi du khi thoat van dau)."""
        self._token += 1
        self._result = None
        self.thinking = False


# --------------------------------------------------------------------------- #
#  Giao dien PyGame
# --------------------------------------------------------------------------- #
class AIBattle(object):
    BOARD_X, BOARD_Y, BOARD_SIZE = 10, 38, 336
    PANEL_X = 352
    SPEEDS = [1600, 1000, 650, 360, 180, 90]  # visual ms per 3-cell bullet phase
    EXPLOSION_MS = 220

    def __init__(self, ui_game, screen, sprites, human_mode=False):
        import pygame
        self.pg = pygame
        self.human_mode = human_mode
        self.title = "1 PLAYER" if human_mode else "AI BATTLE"
        self.ui_game = ui_game
        self.screen = screen
        self.sprites = sprites
        self.clock = ui_game.clock
        self.c = ui_game.ui
        pixel = str(HERE / "fonts" / "prstart.ttf")
        self.f_text = pygame.font.Font(pixel, 8)
        self.f_small = pygame.font.Font(pixel, 7)
        self.f_head = pygame.font.Font(pixel, 10)
        self.f_title = pygame.font.Font(pixel, 13)
        self.colors = [self.c["cyan"], self.c["orange"]] + ([self.c["orange"]] * 3 if human_mode else [])

        self.backend = None
        self.backend_error = None
        self.options = []
        self.sel_agent = [0, 0]
        self.depth = [4, 4]
        self.sel_map = 0
        self.row = 0
        self.setup_msg = ""
        self.match = None
        self.paused = False
        self.step_once = False
        self.speed = 3
        self.budgets = [60, 120, 250, None]
        self.budget_index = 0
        self.inspect_search = False
        self.show_vectors = False
        self._step_inflight = False
        self.last_move_ms = 0
        self.flashes = []

        self._load_backend()
        from presentation import BulletPlayback
        self.playback = BulletPlayback(self.backend.game) if self.backend is not None else None
        self._prepare_sprites()

    def _chamfer(self, rect, fill, border, notch=6, width=2, rivets=False):
        pg = self.pg
        x, y, w, h = rect
        n = min(notch, w // 3, h // 3)
        pts = [
            (x + n, y),
            (x + w - n, y),
            (x + w, y + n),
            (x + w, y + h - n),
            (x + w - n, y + h),
            (x + n, y + h),
            (x, y + h - n),
            (x, y + n),
        ]
        pg.draw.polygon(self.screen, fill, pts)
        pg.draw.polygon(self.screen, border, pts, width)
        if rivets and w >= 28 and h >= 28:
            rc = self.c["border_hi"]
            for rx, ry in [(x + n + 2, y + 4), (x + w - n - 4, y + 4),
                           (x + n + 2, y + h - 6), (x + w - n - 4, y + h - 6)]:
                pg.draw.rect(self.screen, rc, (rx, ry, 2, 2))

    def _hazard(self, rect, c1=None, c2=None, stripe=6):
        pg = self.pg
        if c1 is None:
            c1 = self.c["orange"]
        if c2 is None:
            c2 = self.c["bg"]
        x, y, w, h = rect
        clip_prev = self.screen.get_clip()
        self.screen.set_clip(rect)
        pg.draw.rect(self.screen, c2, rect)
        for sx in range(x - h, x + w + h, stripe * 2):
            pts = [(sx, y + h), (sx + stripe, y + h), (sx + stripe + h, y), (sx + h, y)]
            pg.draw.polygon(self.screen, c1, pts)
        self.screen.set_clip(clip_prev)

    def _seg_bar(self, x, y, w, h, value, maxv, color):
        pg = self.pg
        pg.draw.rect(self.screen, self.c["bg"], (x, y, w, h))
        pg.draw.rect(self.screen, self.c["border"], (x, y, w, h), 1)
        if maxv <= 0:
            return
        segs = min(maxv, 12)
        gap = 2
        inner_w = w - 4
        seg_w = max(2, (inner_w - gap * (segs - 1)) // segs)
        filled = int(round((max(0, min(value, maxv)) / float(maxv)) * segs))
        for i in range(segs):
            sx = x + 2 + i * (seg_w + gap)
            if sx + seg_w > x + w - 2:
                break
            col = color if i < filled else self.c["hull"]
            pg.draw.rect(self.screen, col, (sx, y + 2, seg_w, h - 4))

    # ---------------- khoi tao ----------------
    def _load_backend(self):
        path = find_task2_dir()
        if path is None:
            self.backend_error = ("Khong tim thay thu muc task2.\n"
                                  "Dat thu muc task2 canh tanks.py\n"
                                  "(hoac dat bien moi truong TASK2_DIR).")
            return
        try:
            self.backend = Task2Backend(path)
            if self.human_mode:
                # The imported originals are adapted for the requested two-AI duel.
                self.backend.maps = [n for n in self.backend.maps if not n.startswith("original_")]
            self._refresh_options()
        except Exception as exc:  # noqa: BLE001
            self.backend_error = "Khong nap duoc task2:\n%s" % exc

    def _refresh_options(self):
        self.options = [o for o in self.backend.agent_options()
                        if not self.human_mode or o["kind"] == "search"]

        default_index = next(
            (
                index
                for index, option in enumerate(self.options)
                if option.get("mode") == "heuristic_alphabeta"
            ),
            0,
        )

        # Default: terminal-only Alpha-Beta versus heuristic Alpha-Beta.
        plain_index = next((i for i, option in enumerate(self.options)
                            if option.get("mode") == "alphabeta"), default_index)
        self.sel_agent = [plain_index, default_index]

    def _selected_options(self):
        options = [self.options[self.sel_agent[p]] for p in (0, 1)]
        if self.human_mode:
            options = [{"kind": "human", "label": "HUMAN (KEYBOARD)", "short": "HUMAN"},
                       {"kind": "team", "label": "ALL 4 NPCs / 4 ALGORITHMS", "short": "4 NPCs"}]
        return options

    def _prepare_sprites(self):
        pg = self.pg
        sp = self.sprites

        def alpha(rect):
            return sp.subsurface(rect).convert_alpha()

        self.raw = {
            "tank": alpha((0, 0, 32, 32)),
            "castle": alpha((0, 30, 32, 32)),
            "castle_dead": alpha((32, 30, 32, 32)),
            "brick": alpha((96, 128, 16, 16)),
            "steel": alpha((96, 144, 16, 16)),
            "bullet": alpha((150, 148, 6, 8)),
            "boom": [alpha((0, 160, 64, 64)), alpha((64, 160, 64, 64)), alpha((128, 160, 64, 64))],
        }
        # Use the original white enemy sprite rather than recolouring the player.
        tank1 = pg.Surface((32, 32), pg.SRCALPHA)
        tank1.blit(alpha((64, 0, 26, 30)), (3, 1))
        self.raw["tank1"] = tank1
        self.cell = 32
        self._scaled_for = None

    def _build_cell_sprites(self, state):
        """Scale sprite theo kich thuoc ban do (ban do 9x9 hay 11x11 deu vua khung)."""
        pg = self.pg
        cell = max(16, self.BOARD_SIZE // max(state.rows, state.cols))
        if self._scaled_for == cell:
            return
        self._scaled_for = cell
        self.cell = cell
        sc = lambda s, size: pg.transform.scale(s, size)
        rot = {0: 0, 1: 180, 2: 90, 3: 270}  # huong game.py -> do xoay (nguoc chieu kim dong ho)
        self.img_tank = []
        for key in (("tank", "tank1", "tank1", "tank1", "tank1") if self.human_mode else ("tank", "tank1")):
            base = sc(self.raw[key], (cell, cell))
            self.img_tank.append({d: pg.transform.rotate(base, a) for d, a in rot.items()})
        self.img_castle = sc(self.raw["castle"], (cell, cell))
        self.img_castle_dead = sc(self.raw["castle_dead"], (cell, cell))
        self.img_brick = sc(self.raw["brick"], (cell, cell))
        self.img_steel = sc(self.raw["steel"], (cell, cell))
        bw, bh = max(3, cell // 7), max(5, cell // 5)
        bullet = sc(self.raw["bullet"], (bw, bh))
        self.img_bullet = {d: pg.transform.rotate(bullet, a) for d, a in rot.items()}
        self.img_boom = [sc(f, (cell * 2, cell * 2)) for f in self.raw["boom"]]
        spark = max(10, int(cell * .65))
        self.img_spark = [sc(f, (spark, spark)) for f in self.raw["boom"][:2]]

    # ---------------- tien ich ve ----------------
    def _text(self, font, text, color, pos, center=False, right=False):
        surf = font.render(text, False, color)
        rect = surf.get_rect()
        if center:
            rect.center = pos
        elif right:
            rect.topright = pos
        else:
            rect.topleft = pos
        self.screen.blit(surf, rect)
        return rect

    @staticmethod
    def _fit(font, text, maxw):
        if font.size(text)[0] <= maxw:
            return text
        while text and font.size(text + "...")[0] > maxw:
            text = text[:-1]
        return text + "..."

    def _bar(self, x, y, w, h, value, maxv, color):
        pg = self.pg
        pg.draw.rect(self.screen, self.c["panel2"], (x, y, w, h), border_radius=0)
        if maxv > 0 and value > 0:
            fill = max(1, int(w * min(value, maxv) / float(maxv)))
            pg.draw.rect(self.screen, color, (x, y, fill, h), border_radius=0)

    def _quit(self):
        self.pg.quit()
        sys.exit()

    # ---------------- vong lap chinh ----------------
    def run(self):
        """Chay man hinh AI Battle. Tra ve khi nguoi dung bam ESC o man hinh setup."""
        pg = self.pg
        while True:
            if self.backend is None:
                if self._error_screen():
                    return
                continue
            if not self._setup_screen():
                return
            self._play_screen()

    # ---------------- man hinh loi (khong tim thay task2) ----------------
    def _error_screen(self):
        pg = self.pg
        c = self.c
        while True:
            self.clock.tick(30)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self._quit()
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_q:
                        self._quit()
                    if event.key in (pg.K_ESCAPE, pg.K_RETURN):
                        return True
            self.screen.fill(c["bg"])
            pg.draw.rect(self.screen, c["panel"], (42, 74, 396, 268), border_radius=0)
            pg.draw.rect(self.screen, c["red"], (42, 74, 396, 4), border_radius=0)
            self._text(self.f_small, "AI BATTLE  /  TASK2 NOT AVAILABLE", c["red"], (240, 104), center=True)
            for i, line in enumerate(self.backend_error.split("\n")):
                self._text(self.f_text, line, c["text"], (240, 150 + i * 24), center=True)
            self._text(self.f_small, "PRESS ENTER OR ESC TO RETURN", c["orange"], (240, 310), center=True)
            pg.display.flip()

    # ---------------- man hinh setup ----------------
    def _setup_screen(self):
        """Chon agent/ban do. Tra ve True neu bat dau van dau, False neu quay ve menu."""
        pg = self.pg
        c = self.c
        self._refresh_options_keep_selection()
        rows = ["P0", "D0", "P1", "D1", "MAP", "START"]
        while True:
            self.clock.tick(30)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self._quit()
                if event.type != pg.KEYDOWN:
                    continue
                if event.key == pg.K_q:
                    self._quit()
                elif event.key == pg.K_ESCAPE:
                    return False
                elif event.key == pg.K_UP:
                    self.row = (self.row - 1) % len(rows)
                elif event.key == pg.K_DOWN:
                    self.row = (self.row + 1) % len(rows)
                elif event.key in (pg.K_LEFT, pg.K_RIGHT):
                    self._change_row(rows[self.row], 1 if event.key == pg.K_RIGHT else -1)
                elif event.key == pg.K_o and rows[self.row] == "MAP":
                    self.sel_map = next((i for i,n in enumerate(self.backend.maps)
                                         if n.startswith("original_")), self.sel_map)
                elif event.key in (pg.K_PAGEUP, pg.K_PAGEDOWN) and rows[self.row] == "MAP":
                    self._change_row("MAP", -5 if event.key == pg.K_PAGEUP else 5)
                elif event.key in (pg.K_HOME, pg.K_END) and rows[self.row] == "MAP":
                    self.sel_map = 0 if event.key == pg.K_HOME else len(self.backend.maps)-1
                elif event.key == pg.K_F5:
                    self._refresh_options_keep_selection()
                elif event.key == pg.K_b:
                    self.budget_index = (self.budget_index + 1) % len(self.budgets)
                elif event.key == pg.K_RETURN:
                    if self._start_match():
                        return True
            self._draw_setup(rows)

    def _refresh_options_keep_selection(self):
        old = [self.options[i] for i in self.sel_agent] if self.options else None
        self.options = [o for o in self.backend.agent_options()
                        if not self.human_mode or o["kind"] == "search"]
        if old:
            for p in (0, 1):
                for i, o in enumerate(self.options):
                    if o["kind"] == old[p]["kind"] and o.get("mode") == old[p].get("mode") \
                            and o.get("path") == old[p].get("path"):
                        self.sel_agent[p] = i
                        break
        for p in (0, 1):
            self.sel_agent[p] = min(self.sel_agent[p], len(self.options) - 1)

    def _change_row(self, row, step):
        if self.human_mode and row in ("P0", "D0", "P1"):
            return
        if row in ("P0", "P1"):
            p = 0 if row == "P0" else 1
            self.sel_agent[p] = (self.sel_agent[p] + step) % len(self.options)
        elif row in ("D0", "D1"):
            p = 0 if row == "D0" else 1
            self.depth[p] = max(1, min(8, self.depth[p] + step))
        elif row == "MAP":
            self.sel_map = (self.sel_map + step) % len(self.backend.maps)

    def _draw_setup(self, rows):
        pg, c, scr = self.pg, self.c, self.screen
        scr.fill(c["bg"])
        for gx in range(0, 480, 32):
            pg.draw.line(scr, c["grid"], (gx, 0), (gx, 416))
        for gy in range(0, 416, 32):
            pg.draw.line(scr, c["grid"], (0, gy), (480, gy))
        self._chamfer((10, 8, 460, 400), c["hull"], c["border_hi"], notch=10, rivets=True)
        self._hazard((22, 16, 436, 10))
        title = "SOLO SORTIE // CONFIG" if self.human_mode else "AI WARGAME // CONFIG"
        self._text(self.f_title, title, c["text"], (240, 39), center=True)
        options = self._selected_options()
        y = 56
        for idx, row in enumerate(rows):
            selected = idx == self.row
            self._chamfer((24, y, 432, 39), c["panel2"] if selected else c["panel"],
                          c["orange"] if selected else c["border"], notch=6,
                          width=2 if selected else 1)
            if row in ("P0", "P1"):
                side = 0 if row == "P0" else 1
                pg.draw.rect(scr, self.colors[side], (30, y + 7, 4, 25))
                self._text(self.f_small, "UNIT P%d" % side, self.colors[side], (42, y + 6))
                name = self._fit(self.f_text, options[side]["label"], 340)
                if not self.human_mode:
                    name = "< " + name + " >"
                self._text(self.f_text, name, c["text"] if selected else c["muted"], (42, y + 20))
            elif row in ("D0", "D1"):
                side = 0 if row == "D0" else 1
                self._text(self.f_small, "SEARCH DEPTH P%d" % side, c["muted"], (42, y + 14))
                searchable = options[side]["kind"] in ("search", "team")
                value = "< %d >" % self.depth[side] if searchable else "N/A"
                self._text(self.f_text, value, self.colors[side] if selected and searchable else c["muted"],
                           (438, y + 13), right=True)
            elif row == "MAP":
                self._text(self.f_small, "COMBAT SECTOR", c["cyan"], (42, y + 6))
                name = self.backend.maps[self.sel_map].upper()
                self._text(self.f_text, "< " + self._fit(self.f_text, name, 350) + " >",
                           c["text"] if selected else c["muted"], (42, y + 20))
            else:
                self._text(self.f_head, "DEPLOY UNITS", c["orange"] if selected else c["text"],
                           (240, y + 19), center=True)
            y += 46
        hint = ""
        if rows[self.row] == "MAP":
            hint = "PGUP/PGDN: 5 MAPS   HOME/END: FIRST/LAST"
            if not self.human_mode:
                hint = "O: ORIGINALS   PGUP/PGDN: 5 MAPS   HOME/END"
        elif rows[self.row] in ("P0", "P1") and not self.human_mode:
            side = 0 if rows[self.row] == "P0" else 1
            mode = options[side].get("mode")
            evaluator = self.backend.search.MODES[mode][1].name if mode in self.backend.search.MODES else "custom"
            hint = {"terminal_only": "NO HEURISTIC: NONTERMINAL CUTOFF = 0",
                    "heuristic": "HP + FIRING ROUTE + AIM + BULLETS"}.get(evaluator, "EXTERNAL AGENT")
        self._text(self.f_small, self._fit(self.f_small, self.setup_msg or hint, 420),
                   c["red"] if self.setup_msg else c["muted"], (240, 346), center=True)
        self._text(self.f_small, "ARROWS: TUNE   ENTER: DEPLOY   ESC: HANGAR", c["muted"], (240, 365), center=True)
        budget = self.budgets[self.budget_index]
        budget_label = "FULL DEPTH" if budget is None else "%d MS/MOVE" % budget
        self._text(self.f_small, "B: " + budget_label + "   F5: IMPORT   TAB: INFO", c["border_hi"],
                   (240, 380), center=True)
        self._hazard((22, 392, 436, 8))
        pg.display.flip()

    # ---------------- bat dau van dau ----------------
    def _start_match(self):
        try:
            options = self._selected_options()
            state = self.backend.new_state(self.backend.maps[self.sel_map])
            depths = list(self.depth)
            if self.human_mode:
                from arena import ArenaState, NPC_MODES
                state = ArenaState.from_state(state)
                options = [options[0]] + [
                    {"kind": "search", "mode": mode, "label": self.backend.LONG[mode],
                     "short": dict(zip(NPC_MODES, ("MINIMAX", "H-MINIMAX", "ALPHABETA", "H-ALPHA")))[mode]} for mode in NPC_MODES]
                depths = [self.depth[0]] + [self.depth[1]] * 4
            agents = [self.backend.create_agent(o, p, depths[p]) for p, o in enumerate(options)]
        except Exception as exc:  # noqa: BLE001
            self.setup_msg = "Cannot start: %s" % exc
            return False
        self.setup_msg = ""
        self.match = Match(self.backend, state, agents, options, depths, self.budgets[self.budget_index])
        self.paused = False
        self.step_once = False
        self._step_inflight = False
        self.flashes = []
        self.last_move_ms = self.pg.time.get_ticks()
        self.playback.reset(state, self.last_move_ms)
        return True

    # ---------------- man hinh choi ----------------
    def _play_screen(self):
        pg = self.pg
        self._build_cell_sprites(self.match.state)
        key_actions = {pg.K_UP: "MOVE_UP", pg.K_DOWN: "MOVE_DOWN", pg.K_LEFT: "MOVE_LEFT",
                       pg.K_RIGHT: "MOVE_RIGHT", pg.K_SPACE: "FIRE", pg.K_x: "STAY"}
        while True:
            self.clock.tick(60)
            now = pg.time.get_ticks()
            m = self.match
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self._quit()
                if event.type != pg.KEYDOWN:
                    continue
                if event.key == pg.K_q:
                    self._quit()
                elif event.key == pg.K_ESCAPE:
                    m.abort()
                    return
                elif event.key == pg.K_p:
                    self.paused = not self.paused
                elif event.key == pg.K_n:
                    self.paused = True
                    self.step_once = True
                elif event.key == pg.K_TAB:
                    self.inspect_search = not self.inspect_search
                elif event.key == pg.K_v:
                    self.show_vectors = not self.show_vectors
                elif event.key in (pg.K_EQUALS, pg.K_PLUS, pg.K_KP_PLUS, pg.K_RIGHTBRACKET):
                    self.speed = min(len(self.SPEEDS) - 1, self.speed + 1)
                elif event.key in (pg.K_MINUS, pg.K_KP_MINUS, pg.K_LEFTBRACKET):
                    self.speed = max(0, self.speed - 1)
                elif event.key == pg.K_r or (event.key == pg.K_RETURN and (m.is_over() or m.error)):
                    if event.key == pg.K_RETURN and m.error:
                        m.abort()
                        return
                    m.abort()
                    if self._start_match():
                        self._build_cell_sprites(self.match.state)
                        m = self.match
                elif event.key in key_actions and not self.paused and not self.playback.busy(now) and m.current_is_human():
                    name = key_actions[event.key]
                    action = getattr(self.backend.game.Action, name)
                    if m.submit_human_action(action):
                        self._after_move(now)

            m = self.match
            # AI tra loi
            if not self.playback.busy(now) and (not self.paused or self.step_once or self._step_inflight) and m.poll():
                self._after_move(now)
                self.step_once = False
                self._step_inflight = False
            # yeu cau nuoc di ke tiep
            if not m.is_over() and not m.error and not m.thinking and not m.current_is_human():
                if not self.playback.busy(now) and (not self.paused or self.step_once):
                    self._step_inflight = self.step_once
                    self.step_once = False
                    m.request_ai_move()
            self._draw_play(now)

    def _after_move(self, now):
        m = self.match
        self.last_move_ms = now
        self.playback.observe(m.prev_state, m.state, m.last_action, now, self.SPEEDS[self.speed] * self.cell / 32)

    # ---------------- ve van dau ----------------
    def _board_origin(self, state):
        w = self.cell * state.cols
        h = self.cell * state.rows
        ox = self.BOARD_X + (self.BOARD_SIZE - w) // 2
        oy = self.BOARD_Y + (self.BOARD_SIZE - h) // 2
        return ox, oy

    def _cell_xy(self, origin, r, c):
        return origin[0] + c * self.cell, origin[1] + r * self.cell

    def _bullet_positions(self, now):
        return self.playback.positions(now)

    def _draw_play(self, now):
        pg, scr, c, m = self.pg, self.screen, self.c, self.match
        s = self.playback.state_at(now)
        origin, cell = self._board_origin(s), self.cell
        scr.fill(c["bg"])
        pg.draw.rect(scr, c["hull"], (0, 0, 480, 28))
        pg.draw.line(scr, c["border_hi"], (0, 27), (480, 27), 2)
        self._hazard((0, 0, 64, 26), stripe=5)
        self._text(self.f_small, "TACTICAL HUD", c["orange"], (72, 10))
        self._text(self.f_small, "CYCLE %03d" % m.state.cycle, c["text"], (268, 10), center=True)
        self._text(self.f_small, self._fit(self.f_small, self.backend.maps[self.sel_map].upper(), 112),
                   c["cyan"], (472, 10), right=True)
        bw, bh = cell * s.cols, cell * s.rows
        self._chamfer((origin[0] - 6, origin[1] - 6, bw + 12, bh + 12),
                      c["hull"], c["border_hi"], notch=8, rivets=True)
        board = pg.Rect(origin[0], origin[1], bw, bh)
        pg.draw.rect(scr, (12, 15, 19), board)
        for col in range(s.cols + 1):
            x = origin[0] + col * cell
            pg.draw.line(scr, c["grid"], (x, origin[1]), (x, origin[1] + bh))
        for row in range(s.rows + 1):
            y = origin[1] + row * cell
            pg.draw.line(scr, c["grid"], (origin[0], y), (origin[0] + bw, y))
        pg.draw.rect(scr, c["border"], board, 1)
        for r, col in s.steel:
            scr.blit(self.img_steel, self._cell_xy(origin, r, col))
        for (r, col), hp in s.walls.items():
            x, y = self._cell_xy(origin, r, col)
            scr.blit(self.img_brick, (x, y))
            if hp < self.backend.game.WALL_HP:
                shade = pg.Surface((cell, cell), pg.SRCALPHA)
                shade.fill((0, 0, 0, 70 * (self.backend.game.WALL_HP - hp)))
                scr.blit(shade, (x, y))
            if cell >= 22:
                self._text(self.f_small, str(hp), c["text"], (x + cell - 8, y + 2))
        for side, base in enumerate(s.bases):
            x, y = self._cell_xy(origin, base.r, base.c)
            scr.blit(self.img_castle if base.hp > 0 else self.img_castle_dead, (x, y))
            if base.hp > 0:
                pg.draw.rect(scr, self.colors[side], (x, y, cell, cell), 1)
        for side, tank in enumerate(s.tanks):
            if tank.hp <= 0:
                continue
            x, y = self._cell_xy(origin, tank.r, tank.c)
            scr.blit(self.img_tank[side][tank.d], (x, y))
            if self.human_mode and side:
                self._text(self.f_small, str(side), self.colors[side], (x + 2, y + cell - 9))
            if m.mover == side and m.last_action == self.backend.game.Action.FIRE and now - self.last_move_ms < 130:
                dr, dc = self.backend.game.HUONG[tank.d]
                muzzle = (x + cell // 2 + dc * (cell // 2 + 2), y + cell // 2 + dr * (cell // 2 + 2))
                pg.draw.circle(scr, (255, 220, 110), muzzle, max(3, cell // 6))
                pg.draw.circle(scr, self.colors[side], muzzle, max(5, cell // 4), 1)
        if self.show_vectors:
            self._draw_vectors(origin)
        old_clip = scr.get_clip()
        scr.set_clip(board)
        for r, col, direction in self._bullet_positions(now):
            image = self.img_bullet[direction]
            center = (round(origin[0] + (col + .5) * cell), round(origin[1] + (r + .5) * cell))
            scr.blit(image, image.get_rect(center=center))
        for event in self.playback.effects:
            age = now - event['at']
            if not 0 <= age < self.EXPLOSION_MS:
                continue
            images = self.img_boom if event['large'] else self.img_spark
            image = images[min(len(images) - 1, int(age / self.EXPLOSION_MS * len(images)))]
            r, col = event['point']
            center = (round(origin[0] + (col + .5) * cell), round(origin[1] + (r + .5) * cell))
            scr.blit(image, image.get_rect(center=center))
        scr.set_clip(old_clip)
        if (m.is_over() and not self.playback.busy(now)) or m.error:
            title, reason = ("AI ERROR", m.error) if m.error else m.result_text()
            bx, by = origin[0] + (bw - 296) // 2, origin[1] + (bh - 98) // 2
            self._chamfer((bx, by, 296, 98), c["hull"], c["orange"], notch=9, rivets=True)
            self._hazard((bx + 10, by + 6, 276, 7), stripe=5)
            self._text(self.f_title, self._fit(self.f_title, title, 276), c["text"], (bx + 148, by + 32), center=True)
            self._text(self.f_small, self._fit(self.f_small, reason, 276), c["muted"], (bx + 148, by + 58), center=True)
            self._text(self.f_small, "ENTER: REMATCH   ESC: CONFIG", c["orange"], (bx + 148, by + 78), center=True)
        self._draw_panel(now)
        self._draw_footer()
        if self.inspect_search and not self.human_mode:
            self._draw_search_details()
        pg.display.flip()

    def _draw_panel(self, now=None):
        c, m, game = self.c, self.match, self.backend.game
        now = self.pg.time.get_ticks() if now is None else now
        s = self.playback.state_at(now)
        x0, width = self.PANEL_X, 480 - self.PANEL_X - 6
        abbreviations = {"minimax": "MM", "alphabeta": "AB", "heuristic_minimax": "H-MM", "heuristic_alphabeta": "H-AB"}
        for side in (0, 1):
            y0, accent = 32 + side * 174, self.colors[side]
            team = self.human_mode and side == 1
            active = not m.is_over() and (m.state.to_move == side or team and m.state.to_move > 0)
            self._chamfer((x0, y0, width, 168), c["panel2"] if active else c["panel"],
                          accent if active else c["border"], notch=7, width=2 if active else 1, rivets=True)
            self._text(self.f_small, "P%d" % side, accent, (x0 + 9, y0 + 8))
            option = m.options[side]
            name = "4 NPCS" if team else abbreviations.get(option.get("mode"), option['short'])
            if option['kind'] == 'search':
                name += " D%d" % m.depths[side]
            self._text(self.f_small, self._fit(self.f_small, name, width - 36), c['text'], (x0 + 28, y0 + 8))
            hp = sum(t.hp for t in s.tanks[1:]) if team else s.tanks[side].hp
            maximum = game.TANK_HP * (4 if team else 1)
            self._text(self.f_small, "TANK HP", c['muted'], (x0 + 9, y0 + 25))
            self._text(self.f_small, "%d/%d" % (hp, maximum), c['text'], (x0 + width - 9, y0 + 25), right=True)
            self._seg_bar(x0 + 9, y0 + 36, width - 18, 9, hp, maximum, accent)
            base = s.bases[side]
            self._text(self.f_small, "BASE HP", c['muted'], (x0 + 9, y0 + 50))
            self._text(self.f_small, "%d/%d" % (base.hp, game.BASE_HP), c['text'], (x0 + width - 9, y0 + 50), right=True)
            self._seg_bar(x0 + 9, y0 + 61, width - 18, 9, base.hp, game.BASE_HP, accent)
            info = m.last[side]
            if team:
                lines = [("N%d" % i, "%dHP %s" % (s.tanks[i].hp, abbreviations.get(m.options[i].get('mode'), 'AI')))
                         for i in range(1, 5)]
            else:
                lines = [("ACT", info.get('action', 'READY').replace('MOVE_', '')),
                         ("MS", "%.1f" % info['time_ms'] if 'time_ms' in info else '-'),
                         ("NOD", str(info.get('nodes', '-'))),
                         ("DEP", "%s/%s" % (info.get('depth_reached', '-'), m.depths[side]))]
            for index, (label, value) in enumerate(lines):
                y = y0 + 78 + index * 16
                self._text(self.f_small, label, c['muted'], (x0 + 9, y))
                self._text(self.f_small, self._fit(self.f_small, value, width - 46), c['text'],
                           (x0 + width - 9, y), right=True)
            if active:
                status = ">> KEYBOARD" if m.current_is_human() else ">> COMPUTING" if m.thinking else ">> ACTIVE"
                self._text(self.f_small, status, accent, (x0 + 9, y0 + 150))

    def _draw_vectors(self, origin):
        """Current facing rays and previous movement; these are not future actions."""
        pg, s, cell = self.pg, self.match.state, self.cell
        for p, tank in enumerate(s.tanks):
            if tank.hp <= 0:
                continue
            dr, dc = self.backend.game.HUONG[tank.d]
            r, col = tank.r, tank.c
            while True:
                nr, nc = r + dr, col + dc
                if not s.in_bounds(nr, nc):
                    break
                r, col = nr, nc
                if s.entity_at(r, col) is not None:
                    break
            start = (origin[0] + (tank.c + .5) * cell, origin[1] + (tank.r + .5) * cell)
            end = (origin[0] + (col + .5) * cell, origin[1] + (r + .5) * cell)
            steps = max(1, int(max(abs(end[0]-start[0]), abs(end[1]-start[1])) / 7))
            for i in range(0, steps, 2):
                a, b = i / steps, min(i+1, steps) / steps
                pg.draw.line(self.screen, self.colors[p],
                             (start[0]+a*(end[0]-start[0]), start[1]+a*(end[1]-start[1])),
                             (start[0]+b*(end[0]-start[0]), start[1]+b*(end[1]-start[1])), 1)
        m = self.match
        if m.prev_state is not None and m.mover is not None:
            old, new = m.prev_state.tanks[m.mover], s.tanks[m.mover]
            if (old.r, old.c) != (new.r, new.c):
                a = (origin[0]+(old.c+.5)*cell, origin[1]+(old.r+.5)*cell)
                b = (origin[0]+(new.c+.5)*cell, origin[1]+(new.r+.5)*cell)
                pg.draw.line(self.screen, self.colors[m.mover], a, b, 3)
                pg.draw.circle(self.screen, self.colors[m.mover], b, 4)

    def _draw_search_details(self):
        pg, c, m = self.pg, self.c, self.match
        mover = m.mover if m.mover is not None else m.state.to_move
        info = m.last[mover]
        self._chamfer((18, 35, 444, 344), c["hull"], self.colors[mover], notch=9, rivets=True)
        self._text(self.f_text, "SEARCH: P%d MAX / P%d MIN" % (mover, 1-mover), c["text"], (32, 46))
        self._text(self.f_small, "TAB CLOSE    P PAUSE    N NEXT ACTION", c["orange"], (32, 68))
        if not info:
            self._text(self.f_text, "Waiting for the first AI decision...", c["muted"], (32, 110))
            return
        label = {"heuristic": "HEURISTIC: HP + ROUTE + AIM + BULLETS",
                 "terminal_only": "NO HEURISTIC: TERMINAL UTILITY ONLY"}.get(
                     info.get("evaluator"), "EXTERNAL / CUSTOM EVALUATOR")
        self._text(self.f_small, label, c["green"], (32, 90))
        score = info.get("score")
        value = "?" if score is None else "%+.1f" % score
        status = "FALLBACK" if info.get("fallback") else "COMPLETED"
        self._text(self.f_small, "VALUE %s   DEPTH %s/%s   %s" %
                   (value, info.get("depth_reached", "?"), info.get("depth", "?"), status), c["text"], (32, 108))
        self._text(self.f_small, "NODES %s  CUT %s  EVALS %s" %
                   tuple(info.get(k, 0) for k in ("nodes", "cutoffs", "evals")), c["muted"], (32, 126))
        self._text(self.f_small, "ACTION            VALUE/BOUND       NODES", c["orange"], (32, 151))
        for i, row in enumerate(info.get("root_actions", [])):
            y = 171 + i * 19
            selected = row["action"] == info["action"]
            value = ("<= " if row["bound"] == "upper" else "= ") + "%+.1f" % row["score"]
            self._text(self.f_small, ("> " if selected else "  ") + row["action"],
                       c["green"] if selected else c["text"], (32, y))
            self._text(self.f_small, value, c["text"], (206, y))
            self._text(self.f_small, str(row["nodes"]), c["muted"], (410, y), right=True)
        if not info.get("root_actions"):
            self._text(self.f_small, "No complete search iteration within the time budget.", c["muted"], (32, 178))
        line = " > ".join("P%d:%s" % (x["player"], x["action"].replace("MOVE_", "")) for x in info.get("pv", []))
        self._text(self.f_small, "PREDICTED LINE (each side may replan):", c["orange"], (32, 296))
        self._text(self.f_small, self._fit(self.f_small, line or "-", 410), c["text"], (32, 315))
        self._text(self.f_small, "= exact | <= upper bound | view: P%d" % mover,
                   c["muted"], (32, 338))
        note = ("Non-terminal ties may choose FIRE." if info.get("evaluator") == "terminal_only"
                else "Depth = actions. Leaf score is an estimate.")
        if m.is_over():
            note = "RESULT: " + m.result_text()[0] + "   TAB: RETURN TO BOARD"
        self._text(self.f_small, note, c["orange"] if m.is_over() else c["muted"], (32, 355))

    def _draw_footer(self):
        pg, c, scr, m = self.pg, self.c, self.screen, self.match
        pg.draw.rect(scr, c['hull'], (0, 384, 480, 32))
        pg.draw.line(scr, c['border_hi'], (0, 384), (480, 384), 2)
        self._hazard((416, 386, 64, 30), stripe=5)
        if m.error:
            status, color = "ERR: " + m.error, c['red']
        elif m.is_over():
            status, color = "MATCH OVER", c['orange']
        elif self.paused:
            status, color = "PAUSED (P:RUN N:STEP)", c['orange']
        else:
            status, color = "SYSTEM ONLINE", c['cyan']
        status += " // SPD:%d/%d // TAB:INFO" % (self.speed + 1, len(self.SPEEDS))
        self._text(self.f_small, self._fit(self.f_small, status, 404), color, (8, 390))
        hint = ("ARROWS:MOVE  SPACE:FIRE  X:STAY  ESC:CONFIG" if m.current_is_human()
                else "P:PAUSE N:STEP +/-:SPD R:RESET V:AIM ESC:CONFIG")
        self._text(self.f_small, self._fit(self.f_small, hint, 404), c['muted'], (8, 403))
