# Thực nghiệm cho bản đánh giá cơ bản/nâng cao

Các số liệu hiện tại được đo lại trên Python 3.12.14/Linux x86_64; cấu hình và hash
mã nguồn trong `environment.json`. Đây không phải máy macOS Intel i5 của đề.
Các phép đo chạy tuần tự. Thời gian phụ thuộc tải máy; không suy ra đánh giá nâng
cao luôn nhanh hơn, luôn thắng hoặc tối ưu cả trận.

## Bốn cấu hình hiện tại

- `search_fixed_depth.csv`: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần × 4 cấu hình.
  `search_fixed_depth_summary.csv`: 80 nhóm. Cặp Minimax/Alpha-Beta cùng evaluator
  khớp giá trị; mọi lượt đạt độ sâu yêu cầu. Cột `evaluator` phân biệt BASIC/heuristic.
- `tournament_fixed_depth.csv`: 60 trận = 5 map × 6 cặp × 2 bên, depth 3, tối đa
  60 vòng, không deadline, không phạt lặp. `tournament_fixed_depth_summary.csv`
  tổng hợp thắng/thua/hòa, thời gian, nút và độ sâu. Không có agent fault.
- Các map trên: DEFAULT, OPEN, WALLS, DEFENSE, BULLET. Lặp snapshot chỉ phục vụ đo
  thời gian, không tạo ra các trận độc lập. Các CSV này thay thế số liệu evaluator cũ.

```sh
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output experiments/search_fixed_depth.csv --summary experiments/search_fixed_depth_summary.csv
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output experiments/tournament_fixed_depth.csv --summary experiments/tournament_fixed_depth_summary.csv
```

Xem bảng kết quả và giới hạn diễn giải ở [REPORT.md](../REPORT.md). Thời gian trong
trận có cache giữa các lượt và phụ thuộc trạng thái đã đi qua; dùng benchmark
snapshot để so sánh cùng một trạng thái. Các con số không thuộc cùng thang utility
khi evaluator khác nhau.

Có thể đo thêm cùng ngân sách thời gian, nhưng chưa có CSV xuất bản cho giao thức này:

```sh
python task2/tournament.py --scenarios default open walls --depth 6 --time-limit-ms 30 --max-cycles 20 --output equal_time_results.csv --summary equal_time_summary.csv
```

`benchmark.py --scenarios all` hiện gồm 40 map: 5 map kiểm tra + 35 ORIGINAL.

## Đối chứng trước/sau, cùng GreedyAgent

`behavior_before_after.csv` có 48 trận: 2 phiên bản × 3 map (DEFAULT, WALLS,
ORIGINAL_20) × 4 cấu hình × 2 bên. Depth 3, tối đa 60 vòng, không deadline/phạt lặp.
Mã GreedyAgent và luật game giống nhau ở hai phiên bản. Các cột `movements`,
`rotations`, `fires`, `stays` đếm hành động của AI được thử; di chuyển chỉ tính đổi ô.
Kết quả determinist trên một đối thủ tham chiếu, không phải tỷ lệ thắng tổng quát.

- `before_3ef0963`: Minimax/Alpha-Beta terminal-only và heuristic cũ, commit
  `3ef0963c9c8e9ac90f9504c74899264070348e60`.
- `after_basic_firing_route_v1`: BASIC và heuristic vị trí bắn/đạn mới; hash nguồn
  trong `environment.json`. Hai bản BASIC đều từ 0/6 lên 4/6 trận thắng. Hai bản
  nâng cao đều giữ 5/6; chưa chứng minh tăng tỷ lệ thắng của đánh giá nâng cao.

Tái hiện bằng hai tiến trình riêng để tránh dùng nhầm module/cache giữa phiên bản.
Tại thư mục repo, tạo checkout đối chứng:

```sh
git worktree add --detach ../NMTTNT-before 3ef0963
```

Chạy đoạn dưới tại thư mục repo hiện tại. Đo bản trước bằng các đối số như đã ghi;
đo bản sau bằng cách đổi ba đối số thành `. after_basic_firing_route_v1 after.csv`.
Hai file tạo ra tương ứng hai profile trong CSV đã gộp. Đối chứng dùng code của
phiên bản được truyền vào, không dùng BASIC mới cho cả hai lượt.

```sh
python - ../NMTTNT-before before_3ef0963 before.csv <<'PY'
import sys
from pathlib import Path
repo, profile, output = sys.argv[1:]
sys.path.insert(0, str(Path(repo).resolve() / 'task2'))
from agent import SearchAgent
from benchmark import build_scenarios, MODES_ORDER, write_csv
from external_greedy import GreedyAgent
from game import Action
from search import state_key
rows = []
for name in ('default', 'walls', 'original_20'):
    for mode in MODES_ORDER:
        for seat in (0, 1):
            state = build_scenarios()[name]
            state.max_cycles = 60
            ai, opponent = SearchAgent(mode, 3), GreedyAgent(1-seat)
            ai.reset(seat)
            history = {}
            moves = fires = stays = rotations = decisions = 0
            while not state.is_terminal():
                player = state.to_move
                if player == seat:
                    action, _ = ai.act(state.copy(), history=history)
                    decisions += 1
                    fires += action == Action.FIRE
                    stays += action == Action.STAY
                else:
                    action = opponent.choose_action(state.copy())
                assert action in state.legal_actions()
                old = state.tanks[seat]
                state = state.apply_action(action)
                if player == seat:
                    new = state.tanks[seat]
                    moved = (new.r, new.c) != (old.r, old.c)
                    moves += moved
                    rotations += new.d != old.d and not moved
                key = state_key(state)
                history[key] = history.get(key, 0) + 1
            winner = state.winner()
            rows.append(dict(profile=profile, scenario=name, mode=mode, seat=seat,
                depth=3, max_cycles=60, winner='draw' if winner is None else winner,
                outcome='draw' if winner is None else 'win' if winner == seat else 'loss',
                reason=state.termination_reason(), cycles=state.cycle, decisions=decisions,
                movements=moves, fires=fires, stays=stays, rotations=rotations,
                tank_hp=state.tanks[seat].hp, base_hp=state.bases[seat].hp))
write_csv(output, rows)
PY
```

Bản terminal-only cũng có thể được gọi trực tiếp trong mã mới qua
`choose_action(..., evaluator=TerminalEvaluator())`, nhưng đó không tái tạo
heuristic nâng cao cũ; đối chiếu đầy đủ hai phiên bản cần checkout như trên.
