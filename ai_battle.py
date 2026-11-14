
import os
import importlib.util
import sys
import threading
from pathlib import Path
from time import perf_counter

HERE = Path(__file__).resolve().parent

# Cac file loi cua task2, khong phai AI ben ngoai
CORE_MODULES = {"game", "agent", "search", "heuristics", "benchmark", "__init__"}
MAX_CYCLES = 300  # gioi han so chu ky de tranh van dau vo tan


# --------------------------------------------------------------------------- #
#  Backend: tim va nap task2
# --------------------------------------------------------------------------- #
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
        "minimax": "MINIMAX",
        "alphabeta": "ALPHA-BETA",
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
            self._build_scenarios = benchmark_mod.build_scenarios
            self.maps = ["default"] + [n for n in self._build_scenarios() if n != "default"]
        except Exception:
            self._build_scenarios = None
            self.maps = ["default"]

    # ---- ban do ----
    def new_state(self, map_name):
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
                if "create_agent" not in src and "def choose_action" not in src:
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
        spec.loader.exec_module(module)
        obj = module.create_agent(player_id) if hasattr(module, "create_agent") else module
        return ExternalAgentAdapter(obj)


class ExternalAgentAdapter:
    def __init__(self, obj):
        self.obj = obj

    def act(self, state, time_limit_ms=None, history=None):
        if hasattr(self.obj, "choose_action"):
            out = self.obj.choose_action(state)
            return out if isinstance(out, tuple) else (out, getattr(self.obj, "last_info", {}))
        return self.obj.act(state)


# --------------------------------------------------------------------------- #
#  Match: dieu khien mot van dau (khong phu thuoc pygame)
# --------------------------------------------------------------------------- #
class Match(object):
    def __init__(self, backend, state, agents, options, depths):
        self.backend = backend
        self.state = state
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
        return self.state.is_terminal() or self.state.cycle >= MAX_CYCLES

    def result_text(self):
        """(tieu de, ly do) cua van dau da ket thuc."""
        s = self.state
        if not s.is_terminal():
            return "DRAW", "Turn limit reached (%d cycles)" % MAX_CYCLES
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
        data = {"action": action.name}
        data.update({k: info[k] for k in ("time_ms", "nodes", "depth_reached", "cutoffs") if k in info})
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
                out = agent.act(state, time_limit_ms=60, history=history)
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
            self._apply(action, info)
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
    BOARD_X, BOARD_Y, BOARD_SIZE = 0, 32, 352
    PANEL_X = 356
    SPEEDS = [1200, 700, 400, 200, 80, 0]     # ms giua hai nuoc di
    EXPLOSION_MS = 420

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
        self.f_text = ui_game.ui_font
        self.f_small = ui_game.ui_small
        self.f_head = ui_game.ui_heading
        self.f_title = ui_game.ui_title
        self.colors = [self.c["green"], self.c["orange"]] + ([self.c["orange"]] * 3 if human_mode else [])  # P0 cyan, P1 hong (giong tanks.py)

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
        self.speed = 2
        self.last_move_ms = 0
        self.flashes = []

        self._load_backend()
        self._prepare_sprites()

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

        # Hai phía đều dùng thuật toán tìm kiếm.
        self.sel_agent = [default_index, default_index]

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
        # tank P1: doi kenh mau de phan biet voi P0
        tank1 = self.raw["tank"].copy()
        w, h = tank1.get_size()
        for x in range(w):
            for y in range(h):
                r, g, b, a = tank1.get_at((x, y))
                if a:
                    tank1.set_at((x, y), (b, g, r, a))
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
        bw, bh = max(5, cell // 5), max(7, cell // 4)
        bullet = sc(self.raw["bullet"], (bw, bh))
        self.img_bullet = {d: pg.transform.rotate(bullet, a) for d, a in rot.items()}
        self.img_boom = [sc(f, (cell * 2, cell * 2)) for f in self.raw["boom"]]

    # ---------------- tien ich ve ----------------
    def _text(self, font, text, color, pos, center=False, right=False):
        surf = font.render(text, True, color)
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
        pg.draw.rect(self.screen, self.c["panel2"], (x, y, w, h), border_radius=2)
        if maxv > 0 and value > 0:
            fill = max(1, int(w * min(value, maxv) / float(maxv)))
            pg.draw.rect(self.screen, color, (x, y, fill, h), border_radius=2)

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
            pg.draw.rect(self.screen, c["panel"], (42, 74, 396, 268), border_radius=10)
            pg.draw.rect(self.screen, c["red"], (42, 74, 396, 4), border_radius=2)
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
                elif event.key == pg.K_F5:
                    self._refresh_options_keep_selection()
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
        pg = self.pg
        c = self.c
        scr = self.screen
        scr.fill(c["bg"])
        for gx in range(16, 480, 24):
            pg.draw.line(scr, (28, 15, 65), (gx, 0), (gx, 416), 1)
        for gy in range(8, 416, 24):
            pg.draw.line(scr, (28, 15, 65), (0, gy), (480, gy), 1)
        pg.draw.rect(scr, c["green_dark"], (14, 14, 452, 388), 1, border_radius=8)
        pg.draw.rect(scr, c["panel"], (26, 25, 428, 52), border_radius=7)
        pg.draw.rect(scr, c["orange"], (39, 36, 5, 30), border_radius=2)
        self._text(self.f_head, self.title, c["text"], (55, 31))
        self._text(self.f_small, "TASK 2 SEARCH AGENTS", c["green"], (440, 45), right=True)

        y = 92
        for idx, row in enumerate(rows):
            selected = idx == self.row
            h = 38
            pg.draw.rect(scr, c["panel2"] if selected else c["panel"], (34, y, 412, h), border_radius=5)
            if selected:
                pg.draw.rect(scr, c["orange"], (34, y, 4, h), border_radius=2)
            if row in ("P0", "P1"):
                p = 0 if row == "P0" else 1
                self._text(self.f_small, "PLAYER %d" % p, self.colors[p], (48, y + 6))
                name = self._selected_options()[p]["label"]
                name = self._fit(self.f_text, name, 300)
                if not self.human_mode:
                    name = "<  " + name + "  >"
                self._text(self.f_text, name, c["text"] if selected else c["muted"], (48, y + 19 - 2))
            elif row in ("D0", "D1"):
                p = 0 if row == "D0" else 1
                opt = self._selected_options()[p]
                self._text(self.f_small, "  SEARCH DEPTH", c["muted"], (48, y + 12))
                if opt["kind"] in ("search", "team"):
                    val = "<  %d  >" % self.depth[p]
                    col = c["text"] if selected else c["muted"]
                else:
                    val = "-"
                    col = c["muted"]
                self._text(self.f_text, val, col, (430, y + 10), right=True)
            elif row == "MAP":
                self._text(self.f_small, "MAP", c["green"], (48, y + 6))
                self._text(self.f_text, "<  " + self.backend.maps[self.sel_map].upper() + "  >",
                           c["text"] if selected else c["muted"], (48, y + 19 - 2))
            else:
                label = self.f_head.render("START MATCH", True, c["orange"] if selected else c["muted"])
                scr.blit(label, label.get_rect(center=(240, y + h // 2)))
            y += h + 6
        if self.setup_msg:
            msg = self._fit(self.f_small, self.setup_msg, 420)
            self._text(self.f_small, msg, c["red"], (240, 358), center=True)
        self._text(self.f_small, "UP/DOWN SELECT   LEFT/RIGHT CHANGE   ENTER START   ESC BACK",
                   c["muted"], (240, 374), center=True)
        self._text(self.f_small, ("ARROWS MOVE   SPACE FIRE   X STAY" if self.human_mode else
                                  "F5 RESCAN  -  PUT EXTERNAL AI (.py) IN task2/ OR agents/"),
                   c["muted"], (240, 390), center=True)
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
        self.match = Match(self.backend, state, agents, options, depths)
        self.paused = False
        self.step_once = False
        self.flashes = []
        self.last_move_ms = self.pg.time.get_ticks()
        return True

    # ---------------- man hinh choi ----------------
    def _play_screen(self):
        pg = self.pg
        self._build_cell_sprites(self.match.state)
        key_actions = {pg.K_UP: "MOVE_UP", pg.K_DOWN: "MOVE_DOWN", pg.K_LEFT: "MOVE_LEFT",
                       pg.K_RIGHT: "MOVE_RIGHT", pg.K_SPACE: "FIRE", pg.K_x: "STAY"}
        while True:
            self.clock.tick(50)
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
                elif event.key in key_actions and not self.paused and m.current_is_human():
                    name = key_actions[event.key]
                    action = getattr(self.backend.game.Action, name)
                    if m.submit_human_action(action):
                        self._after_move(now)

            m = self.match
            # AI tra loi
            if m.poll():
                self._after_move(now)
            # yeu cau nuoc di ke tiep
            if not m.is_over() and not m.error and not m.thinking and not m.current_is_human():
                delay = self.SPEEDS[self.speed]
                if (not self.paused and now - self.last_move_ms >= delay) or self.step_once:
                    self.step_once = False
                    m.request_ai_move()
            self._draw_play(now)

    def _after_move(self, now):
        m = self.match
        self.last_move_ms = now
        for (r, c, kind) in m.events:
            self.flashes.append((r, c, now))

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
        """Noi suy vi tri vien dan giua hai trang thai de nhin thay dan bay."""
        m = self.match
        game = self.backend.game
        cur = m.state.bullets
        prev = m.prev_state.bullets if m.prev_state is not None else []
        ani = max(60, min(260, self.SPEEDS[self.speed] or 60))
        t = max(0.0, min(1.0, (now - self.last_move_ms) / float(ani)))
        used = set()
        out = []
        for b in cur:
            start = None
            dr, dc = game.HUONG[b.d]
            for i, p in enumerate(prev):
                if i in used or p.owner != b.owner or p.d != b.d:
                    continue
                k = (b.r - p.r) * dr + (b.c - p.c) * dc
                if 0 <= k <= game.TOC_DO_DAN and (b.r - p.r) == k * dr and (b.c - p.c) == k * dc:
                    used.add(i)
                    start = (p.r, p.c)
                    break
            if start is None and m.last_action == game.Action.FIRE and b.owner == m.mover \
                    and m.prev_state is not None:
                tk = m.prev_state.tanks[m.mover]
                k = (b.r - tk.r) * dr + (b.c - tk.c) * dc
                if tk.d == b.d and 0 <= k <= game.TOC_DO_DAN and (b.r - tk.r) == k * dr and (b.c - tk.c) == k * dc:
                    start = (tk.r, tk.c)
            if start is None:
                start = (b.r, b.c)
            r = start[0] + (b.r - start[0]) * t
            c = start[1] + (b.c - start[1]) * t
            out.append((r, c, b.d))
        return out

    def _draw_play(self, now):
        pg = self.pg
        c = self.c
        scr = self.screen
        m = self.match
        s = m.state
        origin = self._board_origin(s)
        cell = self.cell

        scr.fill(c["bg"])
        # --- thanh tren ---
        pg.draw.rect(scr, c["panel"], (0, 0, 480, 32))
        self._text(self.f_small, self.title, c["orange"], (10, 10))
        self._text(self.f_small, "CYCLE %d / %d" % (s.cycle, MAX_CYCLES), c["text"], (176, 10), center=False)
        self._text(self.f_small, "MAP " + self.backend.maps[self.sel_map].upper(), c["muted"], (470, 10), right=True)

        # --- nen ban co ---
        board = pg.Rect(origin[0], origin[1], cell * s.cols, cell * s.rows)
        pg.draw.rect(scr, (12, 8, 30), board)
        for i in range(s.cols + 1):
            x = origin[0] + i * cell
            pg.draw.line(scr, (28, 15, 65), (x, origin[1]), (x, origin[1] + cell * s.rows), 1)
        for i in range(s.rows + 1):
            y = origin[1] + i * cell
            pg.draw.line(scr, (28, 15, 65), (origin[0], y), (origin[0] + cell * s.cols, y), 1)

        # --- thep, tuong ---
        for (r, cc) in s.steel:
            scr.blit(self.img_steel, self._cell_xy(origin, r, cc))
        for (r, cc), hp in s.walls.items():
            x, y = self._cell_xy(origin, r, cc)
            scr.blit(self.img_brick, (x, y))
            wall_hp = self.backend.game.WALL_HP
            if hp < wall_hp:
                shade = pg.Surface((cell, cell), pg.SRCALPHA)
                shade.fill((0, 0, 0, 80 * (wall_hp - hp)))
                scr.blit(shade, (x, y))
                pg.draw.line(scr, (20, 10, 10), (x + 3, y + 4), (x + cell - 5, y + cell - 4), 1)
            self._text(self.f_small, str(hp), c["text"], (x + cell - 9, y + 1))

        # --- base ---
        for i, b in enumerate(s.bases):
            x, y = self._cell_xy(origin, b.r, b.c)
            scr.blit(self.img_castle if b.hp > 0 else self.img_castle_dead, (x, y))
            pg.draw.rect(scr, self.colors[i], (x, y, cell, cell), 2)
            if b.hp > 0:
                self._bar(x + 2, y + 1, cell - 4, 4, b.hp, self.backend.game.BASE_HP, self.colors[i])

        # --- tank ---
        for i, t in enumerate(s.tanks):
            if t.hp <= 0:
                continue
            x, y = self._cell_xy(origin, t.r, t.c)
            scr.blit(self.img_tank[i][t.d], (x, y))
            pg.draw.rect(scr, self.colors[i], (x, y, cell, cell), 1)
            self._bar(x + 2, y + 1, cell - 4, 4, t.hp, self.backend.game.TANK_HP, self.colors[i])
            if self.human_mode and i > 0:
                self._text(self.f_small, str(i), c["text"], (x + 2, y + cell - 13))

        # --- dan ---
        for (r, cc, d) in self._bullet_positions(now):
            img = self.img_bullet[d]
            cx = origin[0] + cc * cell + cell / 2.0
            cy = origin[1] + r * cell + cell / 2.0
            scr.blit(img, img.get_rect(center=(int(cx), int(cy))))

        # --- no ---
        alive = []
        for (r, cc, t0) in self.flashes:
            age = now - t0
            if age >= self.EXPLOSION_MS:
                continue
            alive.append((r, cc, t0))
            frame = min(2, int(age * 3 / self.EXPLOSION_MS))
            img = self.img_boom[frame]
            x, y = self._cell_xy(origin, r, cc)
            scr.blit(img, img.get_rect(center=(x + cell // 2, y + cell // 2)))
        self.flashes = alive

        # --- ket qua tren ban co ---
        if m.is_over():
            title, reason = m.result_text()
            ov = pg.Surface((300, 84), pg.SRCALPHA)
            ov.fill((8, 5, 24, 225))
            bx = origin[0] + (cell * s.cols - 300) // 2
            by = origin[1] + (cell * s.rows - 84) // 2
            scr.blit(ov, (bx, by))
            pg.draw.rect(scr, c["orange"], (bx, by, 300, 84), 1, border_radius=4)
            self._text(self.f_head, title, c["text"], (bx + 150, by + 28), center=True)
            self._text(self.f_small, self._fit(self.f_small, reason, 280), c["muted"], (bx + 150, by + 56), center=True)
            self._text(self.f_small, "ENTER REMATCH   ESC SETUP", c["orange"], (bx + 150, by + 72), center=True)

        self._draw_panel()
        self._draw_footer()
        pg.display.flip()

    def _draw_panel(self):
        pg = self.pg
        c = self.c
        scr = self.screen
        m = self.match
        s = m.state
        game = self.backend.game
        x0 = self.PANEL_X
        w = 480 - x0 - 4
        for p in (0, 1):
            y0 = 38 + p * 160
            turn = (not m.is_over()) and (s.to_move == p or (self.human_mode and p == 1 and s.to_move > 0))
            pg.draw.rect(scr, c["panel2"] if turn else c["panel"], (x0, y0, w, 152), border_radius=5)
            pg.draw.rect(scr, self.colors[p], (x0, y0, 3, 152), border_radius=2)
            self._text(self.f_small, "P%d" % p, self.colors[p], (x0 + 9, y0 + 5))
            name = "4 NPCs" if self.human_mode and p == 1 else m.options[p]["short"]
            if m.options[p]["kind"] == "search" and not self.human_mode:
                name += " D%d" % m.depths[p]
            self._text(self.f_small, self._fit(self.f_small, name, w - 36), c["text"], (x0 + 30, y0 + 5))
            t, b = s.tanks[p], s.bases[p]
            tank_max = game.TANK_HP
            if self.human_mode and p == 1:
                t = t._replace(hp=sum(n.hp for n in s.tanks[1:]))
                tank_max *= 4
            self._text(self.f_small, "TANK %d/%d" % (t.hp, tank_max), c["muted"], (x0 + 9, y0 + 24))
            self._bar(x0 + 9, y0 + 38, w - 18, 6, t.hp, tank_max, self.colors[p])
            self._text(self.f_small, "BASE %d/%d" % (b.hp, game.BASE_HP), c["muted"], (x0 + 9, y0 + 50))
            self._bar(x0 + 9, y0 + 64, w - 18, 6, b.hp, game.BASE_HP, self.colors[p])
            info = m.last[p]
            lines = [("MOVE", info.get("action", "-").replace("MOVE_", ""))]
            if "time_ms" in info:
                lines.append(("TIME", "%.1f ms" % info["time_ms"]))
            if "nodes" in info:
                lines.append(("NODES", str(info["nodes"])))
            if "depth_reached" in info:
                lines.append(("DEPTH", str(info["depth_reached"])))
            if self.human_mode and p == 1:
                lines = [(str(i) + " " + m.options[i]["short"],
                          str(s.tanks[i].hp) + "/" + str(game.TANK_HP)) for i in range(1, 5)]
            for i, (k, v) in enumerate(lines):
                yy = y0 + 78 + i * 15
                self._text(self.f_small, self._fit(self.f_small, k, w - 42), c["muted"], (x0 + 9, yy))
                self._text(self.f_small, self._fit(self.f_small, v, w - 62), c["text"], (x0 + w - 6, yy), right=True)
            if turn:
                label = "YOUR MOVE" if m.is_human(p) else ("THINKING..." if m.thinking else "READY")
                if self.human_mode and p == 1:
                    label = "NPC %d %s" % (s.to_move, "THINKING" if m.thinking else "READY")
                self._text(self.f_small, label, c["orange"], (x0 + 9, y0 + 138))

    def _draw_footer(self):
        pg = self.pg
        c = self.c
        scr = self.screen
        m = self.match
        pg.draw.rect(scr, c["panel"], (0, 384, 480, 32))
        if m.error:
            status, col = "ERROR: " + m.error, c["red"]
        elif m.is_over():
            status, col = "MATCH OVER", c["orange"]
        elif self.paused:
            status, col = "PAUSED  (P resume, N step)", c["orange"]
        else:
            status, col = "RUNNING", c["green"]
        status = "%s    SPEED %d/%d" % (status, self.speed + 1, len(self.SPEEDS))
        self._text(self.f_small, self._fit(self.f_small, status, 464), col, (8, 388))
        if m.current_is_human():
            hint = "ARROWS MOVE   SPACE FIRE   X STAY"
        else:
            hint = "P PAUSE   N STEP   +/- SPEED   R RESTART   ESC SETUP"
        self._text(self.f_small, hint, c["muted"], (8, 401))
