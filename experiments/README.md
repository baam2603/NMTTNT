# Thực nghiệm không heuristic / có heuristic

Các số liệu được đo lại cho profile `terminal_vs_heuristic_v1` trên Python
3.12.14/Linux x86_64; cấu hình và hash mã nguồn trong `environment.json`.
Đây không phải máy macOS Intel i5 của đề. Các phép đo chạy tuần tự; thời gian phụ
thuộc tải máy. Không dùng dữ liệu BASIC trước đây để mô tả cấu hình hiện tại.

## Bốn cấu hình

- Minimax và Alpha-Beta: `TerminalEvaluator`, không heuristic, trạng thái chưa kết
  thúc ở ngưỡng cắt nhận 0; terminal thắng/thua/hòa là +10000/−10000/0.
- Heuristic Minimax và Heuristic Alpha-Beta: cùng `HeuristicEvaluator`, thêm HP,
  đường tới vị trí bắn, hướng ngắm và đạn. Utility terminal vẫn như hai bản trên.
- Cùng depth nghĩa là cùng số hành động được nhìn trước. Phạt lặp mặc định 0.
  Bản không heuristic không được thêm điều khiển di chuyển hoặc điểm khoảng cách.

## Snapshot cùng độ sâu và đối đầu đổi bên

`search_fixed_depth.csv`: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần × 4 cấu hình;
`search_fixed_depth_summary.csv`: 80 nhóm. Mọi lượt đạt độ sâu yêu cầu; cặp
Minimax/Alpha-Beta cùng evaluator khớp giá trị. Cột evaluator ghi terminal_only hoặc
heuristic. Lặp snapshot phục vụ đo thời gian, không tạo các trận độc lập.

`tournament_fixed_depth.csv`: 60 trận = 5 map × 6 cặp × 2 bên; depth 3, tối đa 60
vòng, không deadline/phạt lặp. File summary tổng hợp thắng/thua/hòa, thời gian,
nút, đánh giá và độ sâu. Không có agent fault. Năm map là DEFAULT, OPEN, WALLS,
DEFENSE, BULLET; kết quả và giới hạn diễn giải ở [REPORT.md](../REPORT.md).

```sh
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output experiments/search_fixed_depth.csv --summary experiments/search_fixed_depth_summary.csv
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output experiments/tournament_fixed_depth.csv --summary experiments/tournament_fixed_depth_summary.csv
```

Thời gian trong trận dùng lại cache và phụ thuộc trạng thái đã đi qua; benchmark
snapshot dùng cùng trạng thái và evaluator mới. Không so raw score của các evaluator
như cùng một thang chất lượng. Alpha-Beta phải giữ giá trị Minimax khi cùng evaluator
và depth, không có nghĩa luôn trả cùng nước khi đồng điểm.

Có thể đo thêm cùng ngân sách thời gian, nhưng chưa xuất bản CSV cho giao thức này:

```sh
python task2/tournament.py --scenarios default open walls --depth 6 --time-limit-ms 30 --max-cycles 20 --output equal_time_results.csv --summary equal_time_summary.csv
```

`benchmark.py --scenarios all` gồm 40 map: 5 map kiểm tra + 35 ORIGINAL.

## Cùng GreedyAgent, có đổi bên

`behavior_fixed_opponent.csv`: 24 trận trên DEFAULT, WALLS, ORIGINAL_20, mỗi cấu hình
đấu GreedyAgent ở cả hai bên; depth 3, tối đa 60 vòng, không deadline/phạt lặp.
Các cột movements, rotations, fires, stays đếm hành động của AI đang thử; di chuyển
chỉ tính đổi ô. Một tập tình huống xác định và một đối thủ không cho tỷ lệ thắng
tổng quát. Điểm 0 của terminal-only ở ngưỡng cắt là trung tính, không chứng minh hòa.

Tái hiện tại thư mục repo bằng đoạn dưới. Chương trình nhập module từ repo hiện
tại; không cần checkout phiên bản BASIC cũ. Dữ liệu trước/sau BASIC cũ được giữ
trong lịch sử commit b6e13ec và đã bỏ khỏi bộ số liệu của bản nộp hiện tại.

```sh
python - . terminal_vs_heuristic_v1 experiments/behavior_fixed_opponent.csv <<'PY'
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
