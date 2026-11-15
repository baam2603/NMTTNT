# Thực nghiệm đánh giá cơ bản/nâng cao và terminal-only

Profile `basic_advanced_terminal_controls_v2`, Python 3.12.14/Linux x86_64; cấu hình
và hash nguồn trong `environment.json`. Đây không phải macOS Intel i5 của đề.
Đợt đo chạy tuần tự; thời gian phụ thuộc máy/tải hệ thống, không đại diện mọi máy.

## Chọn đúng nhóm so sánh

- Mặc định CLI chạy bốn mode chính: minimax/alphabeta dùng BasicEvaluator (HP +
  Manhattan), heuristic_minimax/heuristic_alphabeta dùng đánh giá nâng cao.
- BASIC cũng là heuristic đơn giản; không gọi nó là “không heuristic”.
- Đối chứng không/có heuristic đúng nghĩa: chọn terminal_minimax, terminal_alphabeta,
  heuristic_minimax, heuristic_alphabeta qua --modes hoặc hai CONTROL trên UI.
- terminal_* chỉ chấm utility thắng/thua/hòa; chưa kết thúc ở ngưỡng cắt nhận 0.
  Các mode khác có điểm tiến triển. Cả sáu giữ cùng luật, utility terminal và phạt
  lặp mặc định 0. Không có điều khiển ép di chuyển hoặc ngẫu nhiên để phá hòa.

## Snapshot và đối đầu đổi bên

Năm map: DEFAULT, OPEN, WALLS, DEFENSE, BULLET; hai bên; depth 2/4 × 3 lần cho
snapshot. Mọi lượt đạt độ sâu yêu cầu, từng cặp Minimax/Alpha-Beta khớp giá trị.

- search_fixed_depth.csv: 240 lượt của bốn mode chính; summary 80 nhóm.
- search_terminal_control.csv: 120 lượt terminal-only; summary 40 nhóm.
- tournament_fixed_depth.csv: 60 trận bốn mode chính; có summary.
- tournament_terminal_control.csv: 60 trận bốn mode đối chứng không/có heuristic;
  có summary. Hai tournament cùng 5 map × 6 cặp × 2 bên, depth 3, tối đa 60 vòng,
  không deadline/phạt lặp; không agent fault.

Tái hiện bốn mode chính:

```sh
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output experiments/search_fixed_depth.csv --summary experiments/search_fixed_depth_summary.csv
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output experiments/tournament_fixed_depth.csv --summary experiments/tournament_fixed_depth_summary.csv
```

Tái hiện đối chứng terminal-only và trận không/có heuristic:

```sh
python task2/benchmark.py --modes terminal_minimax terminal_alphabeta --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output experiments/search_terminal_control.csv --summary experiments/search_terminal_control_summary.csv
python task2/tournament.py --modes terminal_minimax terminal_alphabeta heuristic_minimax heuristic_alphabeta --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output experiments/tournament_terminal_control.csv --summary experiments/tournament_terminal_control_summary.csv
```

Có thể dùng cùng bốn --modes đối chứng trong benchmark.py để tạo một CSV gồm cả
terminal-only và heuristic, hoặc chọn bất kỳ tập mode nào trong sáu lựa chọn.
Cặp chỉ được kiểm chứng khi có đủ hai mode tương ứng; CSV ghi tên evaluator.
Lặp snapshot phục vụ đo thời gian, không tạo các trận độc lập. Thời gian trong trận
dùng lại cache và phụ thuộc trạng thái đã đi qua; không so raw score giữa các
evaluator như cùng thang chất lượng. Bảng kết quả: [REPORT.md](../REPORT.md).

Có thể đo thêm cùng ngân sách thời gian; chưa xuất bản CSV cho giao thức này:

```sh
python task2/tournament.py --modes terminal_minimax terminal_alphabeta heuristic_minimax heuristic_alphabeta --scenarios default open walls --depth 6 --time-limit-ms 30 --max-cycles 20 --output equal_time_results.csv --summary equal_time_summary.csv
```

`benchmark.py --scenarios all` gồm 40 map (5 map kiểm tra + 35 ORIGINAL).

## Cùng đối thủ cố định

behavior_fixed_opponent.csv: 36 trận trên DEFAULT, WALLS, ORIGINAL_20; mỗi cấu hình
đấu GreedyAgent ở cả hai bên, depth 3, tối đa 60 vòng, không deadline/phạt lặp. Cột
evaluator phân biệt rõ basic/heuristic/terminal_only; movements chỉ tính đổi ô,
rotations/fires/stays tính xoay/bắn/bỏ lượt của AI đang thử. Một đối thủ và bộ tình
huống xác định không đủ để suy ra tỷ lệ thắng tổng quát; điểm 0 ở ngưỡng cắt không
chứng minh hòa. Tái hiện tại thư mục repo:

```sh
python - . basic_advanced_terminal_controls_v2 experiments/behavior_fixed_opponent.csv <<'PY'
import sys
from pathlib import Path
repo, profile, output = sys.argv[1:]
sys.path.insert(0, str(Path(repo).resolve() / 'task2'))
from agent import SearchAgent
from benchmark import build_scenarios, MODES_ORDER, write_csv
from external_greedy import GreedyAgent
from game import Action
from search import state_key, CONTROL_MODES
rows = []
for name in ('default', 'walls', 'original_20'):
    for mode in MODES_ORDER + CONTROL_MODES:
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
            rows.append(dict(profile=profile, scenario=name, mode=mode, evaluator=ai.engine.evaluator.name, seat=seat,
                depth=3, max_cycles=60, winner='draw' if winner is None else winner,
                outcome='draw' if winner is None else 'win' if winner == seat else 'loss',
                reason=state.termination_reason(), cycles=state.cycle, decisions=decisions,
                movements=moves, fires=fires, stays=stays, rotations=rotations,
                tank_hp=state.tanks[seat].hp, base_hp=state.bases[seat].hp))
write_csv(output, rows)
PY
```
