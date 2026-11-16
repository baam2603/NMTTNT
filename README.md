# Battle City Tanks — Adversarial Search

Game tank viết bằng **Python và Pygame**, tập trung vào hai AI đối kháng dùng
Minimax và Alpha-Beta, có hoặc không có heuristic. Giao diện có thanh HP và bảng
phân tích quyết định của AI.

Mô hình zero-sum, giả định và kết quả thực nghiệm: [REPORT.md](REPORT.md).

## 1. Cài đặt và chạy

**Yêu cầu:** Python 3.10 trở lên, Pygame `>=2.5,<3`.

Mở terminal tại **thư mục chứa `tanks.py`** (trong VS Code: _File → Open Folder_).
Nên tạo môi trường ảo trước:

```powershell
# Windows (PowerShell)
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

Cài thư viện và chạy game:

```bash
python -m pip install -r requirements.txt
python tanks.py
```

Chương trình đọc ảnh, font, âm thanh theo đường dẫn tương đối, nên phải chạy từ
thư mục gốc và giữ nguyên các thư mục tài nguyên.

## 2. Chế độ chơi

| Mục menu              | Chức năng                                                             |
| --------------------- | --------------------------------------------------------------------- |
| **01 // SOLO SORTIE** | Một người chơi (bàn phím) đấu với 4 NPC, mỗi NPC dùng một cấu hình AI |
| **02 // AI WARGAME**  | Hai AI đấu nhau; chọn thuật toán, độ sâu và bản đồ                    |

Phần chính của bài toán là **AI WARGAME**. Mặc định: P0 dùng Alpha-Beta (không heuristic),
P1 dùng Heuristic Alpha-Beta, cả hai depth 4 và ngân sách 60 ms mỗi nước.

SOLO SORTIE chỉ là phần mở rộng: mỗi NPC tìm kiếm trên bản chiếu hai xe và coi NPC khác
là vật cản. Phần này không thuộc bộ số liệu so sánh hai AI.

## 3. Điều khiển

**Menu và màn hình cấu hình**

| Phím  | Chức năng                                                 |
| ----- | --------------------------------------------------------- |
| ↑ / ↓ | Chọn dòng                                                 |
| ← / → | Đổi agent, depth hoặc bản đồ                              |
| Enter | Vào chế độ chơi / bắt đầu trận                            |
| B     | Đổi ngân sách: 60 / 120 / 250 ms mỗi nước hoặc FULL DEPTH |
| F5    | Quét lại các file AI bên ngoài                            |
| Esc   | Về menu                                                   |
| Q     | Thoát                                                     |

Depth chọn từ **1 đến 8**; 1 depth là **một hành động của một bên**. **FULL DEPTH** là hoàn tất
đúng depth đã chọn, không phải tìm đến hết ván. Khi có ngân sách thời gian, AI tìm sâu dần
và trả kết quả của vòng hoàn tất cuối cùng (ngân sách là giới hạn mềm).

Khi chọn dòng **COMBAT SECTOR** (bản đồ): ← / → chuyển từng map, PageUp / PageDown lùi/tiến
5 map, Home / End tới map đầu/cuối, O tới ORIGINAL_01.

**Trong trận**

| Phím    | Chức năng                                                     |
| ------- | ------------------------------------------------------------- |
| P       | Dừng / tiếp tục                                               |
| N       | Dừng và cho AI đi một hành động                               |
| Tab     | Bật/tắt bảng phân tích tìm kiếm (trận hai AI)                 |
| V       | Bật/tắt đường ngắm và dấu di chuyển                           |
| + / −   | Đổi tốc độ trình diễn (không đổi luật hay ngân sách tìm kiếm) |
| R       | Khởi động lại trận                                            |
| Enter   | Chơi lại khi trận kết thúc                                    |
| Esc / Q | Về cấu hình / Thoát                                           |

Trong SOLO SORTIE: **mũi tên** để di chuyển/đổi hướng, **Space** để bắn, **X** để bỏ lượt.

## 4. Bốn cấu hình AI

| Mode trong code       | Thuật toán  | Đánh giá lá chưa kết thúc |
| --------------------- | ----------- | ------------------------- |
| `minimax`             | `Minimax`   | `TerminalEvaluator` (0)   |
| `alphabeta`           | `AlphaBeta` | `TerminalEvaluator` (0)   |
| `heuristic_minimax`   | `Minimax`   | `HeuristicEvaluator`      |
| `heuristic_alphabeta` | `AlphaBeta` | `HeuristicEvaluator`      |

- Utility terminal tính theo người tìm kiếm: **thắng +10000, thua −10000, hòa 0**. Khi gặp
  terminal, độ sâu còn lại được cộng/trừ để ưu tiên thắng sớm, thua muộn.
- Alpha-Beta cắt nhánh khi `alpha >= beta`, cho cùng giá trị với Minimax (cùng trạng thái,
  evaluator, depth); các nước đồng điểm có thể khác nhau.
- Heuristic dựa trên chênh lệch **HP base, HP xe, chi phí tới vị trí bắn, hướng ngắm và
  nguy cơ từ đạn**, có xét vật cản và chi phí phá gạch. Đây chỉ là ước lượng
  (xem [task2/heuristics.py](task2/heuristics.py)).
- Bản không heuristic có thể liên tục chọn FIRE nếu trong độ sâu tìm kiếm chưa thấy thắng/thua
  và các nhánh cùng điểm 0. Đây là hạn chế của baseline giới hạn độ sâu.
- Code **không dùng** bảng chuyển vị (TT), phạt lặp hay lệnh ép tank di chuyển.
  Bảng Tab hiển thị giá trị/cận và chuỗi nước dự đoán (PV), chuỗi này không ép đối thủ làm theo.

## 5. Luật và bản đồ

Thứ tự trong trận hai AI: **P0 hành động → P1 hành động → cập nhật đạn**.
P1 nhìn thấy trạng thái sau nước đi của P0.

| Thực thể   | HP khởi tạo | Sát thương mỗi hit |
| ---------- | ----------: | -----------------: |
| Tank       |           6 |                  1 |
| Base       |           9 |                  1 |
| Tường gạch |           3 |                  1 |

- 6 hành động: MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY.
- Di chuyển tối đa 1 ô; nếu ô bị chặn thì có thể chỉ đổi hướng.
- Đạn bay tối đa **3 ô mỗi cycle**, dừng ngay khi trúng vật cản. Thép không bị phá.
- Mất tank hoặc base thì thua. Hai bên cùng mất trong một lần cập nhật thì hòa.
  Bắn trúng phe mình vẫn gây sát thương.
- Luật game không tự kết thúc theo số cycle.

**Bản đồ:** AI WARGAME có **40 map** gồm `default`, `open`, `walls`, `defense`, `bullet` và
`original_01` … `original_35`. SOLO SORTIE chỉ dùng 5 map đầu.

- `levels/`: 35 map nguồn của Battle City gốc.
- `levels_ai/`: bản chuyển 13×13 dùng cho chế độ hai AI (nước chặn như thép; cỏ/băng thành ô trống).
  Chi tiết: [levels_ai/README.md](levels_ai/README.md).

## 6. Nhập AI của nhóm khác

1. Đặt file `.py` vào `task2/` hoặc tạo thư mục `agents/` cạnh `tanks.py`.
2. File cần có `create_agent(player_id)` trả về đối tượng có `choose_action`/`act`, hoặc có
   trực tiếp hàm `choose_action(state)`/`act(state)`.
3. Trong màn hình cấu hình AI WARGAME, nhấn **F5** rồi chọn **FILE: tên_file.py**.

Hành động trả về có thể là `Action`, số enum hoặc tên (`"FIRE"`, `"MOVE_LEFT"`, `"STAY"`),
hoặc tuple `(action, info_dict)`. Nếu hàm khai báo tham số, loader sẽ chuyển `time_limit_ms`
và `history`; nếu có `reset(player_id)` thì gọi khi tạo agent.

Ví dụ: [task2/external_greedy.py](task2/external_greedy.py) (chỉ để kiểm tra tích hợp, không
phải cấu hình thứ năm của đề). AI bên ngoài phải tự tuân thủ ngân sách thời gian.

## 7. Kiểm thử và thực nghiệm

```bash
# Kiểm thử (22 test)
python -m unittest discover -s tests -v

# Benchmark: đo 4 cấu hình trên cùng trạng thái
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output benchmark_results.csv --summary benchmark_summary.csv

# Đối đầu, đổi bên
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output tournament_results.csv --summary tournament_summary.csv
```

Hoặc chạy notebook `task2.ipynb` (cần cài thêm `ipykernel pandas matplotlib`).

- Mỗi lượt benchmark tạo engine/evaluator mới, không dùng lại cache. Benchmark và tournament
  đều tắt PV; CSV ghi riêng `order_evals` và `leaf_evals`.
- `--max-cycles` **chỉ dừng bộ chạy thí nghiệm**, không nằm trong trạng thái tìm kiếm.
  Trận hết ngân sách được ghi `unfinished`, **không tính là hòa**.
- Dữ liệu đã đo nằm trong `experiments/` (240 lượt snapshot, 60 trận). Xem
  [experiments/README.md](experiments/README.md). Đo trên Linux/Python 3.12.14, chưa phải máy
  macOS Intel i5 của đề; không suy ra heuristic luôn thắng hay nhanh hơn.

## 8. Cấu trúc mã nguồn

```text
NMTTNT/
├── tanks.py              # Điểm chạy, menu và tài nguyên Pygame
├── ai_battle.py          # Giao diện và điều phối trận hai AI
├── presentation.py       # Nội suy đạn/hiệu ứng (không chọn hành động AI)
├── arena.py              # Phần mở rộng: một người đấu bốn NPC
├── task2/
│   ├── game.py           # Trạng thái, hành động, luật, terminal
│   ├── search.py         # Minimax, Alpha-Beta, depth, deadline
│   ├── heuristics.py     # TerminalEvaluator và HeuristicEvaluator
│   ├── agent.py          # API agent và bộ chạy trận
│   ├── benchmark.py      # Đo 4 cấu hình trên cùng snapshot
│   ├── tournament.py     # Trận đổi bên, thống kê, xuất CSV
│   ├── original_maps.py  # Đọc/chuyển map gốc
│   └── external_greedy.py  # Ví dụ AI ngoài
├── tests/                # Kiểm thử
├── experiments/          # Dữ liệu và điều kiện thực nghiệm
├── reports/
├── images/  fonts/  sounds/   # Tài nguyên
├── levels/  levels_ai/        # Bản đồ
├── requirements.txt
├── README.md
├── REPORT.md
└── task2.ipynb
```
