# Battle City Tanks — Adversarial Search

Game tank viết bằng **Python và Pygame**, tập trung vào hai AI đối kháng bằng
Minimax và Alpha-Beta, có hoặc không có heuristic. Giao diện HUD cơ khí dùng nền
tối, khung kim loại, thanh HP và bảng phân tích quyết định của AI.

Mô hình zero-sum, giả định và kết quả thực nghiệm: [REPORT.md](REPORT.md).

## 1. Cài đặt và chạy

**Yêu cầu:** Python 3.10 trở lên và Pygame `>=2.5,<3`.

Sau khi clone repo hoặc giải nén ZIP, mở terminal tại **thư mục chứa `tanks.py`**.
Nếu dùng VS Code, chọn **File → Open Folder** và mở thư mục này.

Có thể tạo môi trường ảo trước khi cài:

**Windows — PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Sau đó cài thư viện và chạy game:

```bash
python -m pip install -r requirements.txt
python tanks.py
```

Chương trình đọc ảnh, font và âm thanh theo đường dẫn tương đối. Vì vậy, cần chạy
từ thư mục gốc và giữ các thư mục tài nguyên đi kèm; không chỉ sao chép các file AI.

## 2. Chế độ chơi

| Mục trên menu | Chức năng |
| --- | --- |
| **01 // SOLO SORTIE** | Một người dùng bàn phím đấu đồng thời với 4 NPC, mỗi NPC dùng một trong bốn cấu hình AI |
| **02 // AI WARGAME** | Hai AI đấu nhau; chọn thuật toán, độ sâu và bản đồ cho trận |

Phần chính của bài toán đối kháng và thực nghiệm là **AI WARGAME**. Mặc định, P0
chạy Alpha-Beta không heuristic, P1 chạy Heuristic Alpha-Beta; cả hai chọn depth 4
và ngân sách 60 ms mỗi nước. Có thể thay đổi tại màn hình cấu hình.

SOLO SORTIE là phần mở rộng: mỗi NPC tìm kiếm trên bản chiếu hai xe, coi các NPC
khác là vật cản. Phần này không phải tìm kiếm đối kháng đầy đủ năm tác nhân và
không thuộc bộ số liệu so sánh hai AI.

## 3. Điều khiển

### Menu và màn hình cấu hình

| Phím | Chức năng |
| --- | --- |
| ↑ / ↓ | Chọn mục hoặc dòng cấu hình |
| ← / → | Đổi agent, depth hoặc bản đồ tại dòng đang chọn |
| Enter | Vào chế độ chơi hoặc bắt đầu trận |
| Esc | Từ cấu hình trở về menu |
| B | Đổi ngân sách: 60 / 120 / 250 ms mỗi nước hoặc FULL DEPTH |
| F5 | Quét lại các file AI bên ngoài |
| Q | Thoát chương trình |

Trong cấu hình hai AI, depth trên UI chọn từ **1 đến 8**. Một depth tương ứng
**một hành động của một bên**, không phải một cycle gồm hai lượt.

**FULL DEPTH** nghĩa là hoàn tất depth đã chọn, không phải tìm đến cuối toàn bộ
ván đấu. Khi có ngân sách thời gian, AI tìm sâu dần và trả kết quả của lần tìm
kiếm hoàn tất cuối cùng; ngân sách là giới hạn mềm.

Khi chọn dòng **COMBAT SECTOR** (MAP):

| Phím | Chức năng |
| --- | --- |
| ← / → | Chuyển từng bản đồ |
| O | Tới ORIGINAL_01 trong chế độ hai AI |
| PageUp / PageDown | Lùi/tiến 5 bản đồ |
| Home / End | Tới bản đồ đầu/cuối |

### Trong trận

| Phím | Chức năng |
| --- | --- |
| P | Dừng / tiếp tục |
| N | Dừng và cho AI đi một hành động khi tới lượt AI |
| Tab | Bật/tắt bảng phân tích tìm kiếm trong trận hai AI |
| V | Bật/tắt đường ngắm và dấu di chuyển vừa thực hiện |
| + / − | Đổi tốc độ trình diễn; không đổi tốc độ đạn theo luật hoặc ngân sách tìm kiếm |
| R | Khởi động lại trận |
| Enter | Chơi lại khi trận đã kết thúc |
| Esc | Trở về màn hình cấu hình |
| Q | Thoát chương trình |

Trong SOLO SORTIE, khi tới lượt người chơi và game đang chạy: **mũi tên** di chuyển/đổi
hướng, **Space** bắn, **X** bỏ lượt.

## 4. Bốn cấu hình AI

| Mode trong code | Lớp tìm kiếm | Đánh giá lá chưa kết thúc tại ngưỡng depth |
| --- | --- | --- |
| `minimax` | `Minimax` | `TerminalEvaluator`: 0 trung tính |
| `alphabeta` | `AlphaBeta` | `TerminalEvaluator`: 0 trung tính |
| `heuristic_minimax` | `Minimax` | `HeuristicEvaluator` |
| `heuristic_alphabeta` | `AlphaBeta` | Cùng `HeuristicEvaluator` |

Cả bốn dùng utility terminal theo góc nhìn người tìm kiếm: **thắng +10000, thua
−10000, hòa 0**. Khi gặp terminal trong cây, độ sâu còn lại được cộng/trừ để ưu tiên
thắng sớm, thua muộn. Alpha-Beta cắt nhánh khi `alpha >= beta`; cùng trạng thái,
evaluator và depth phải cho cùng giá trị Minimax, dù nước đồng điểm có thể khác nhau.

Heuristic gồm chênh lệch **HP căn cứ, HP xe, chi phí tới vị trí bắn, hướng ngắm và
nguy cơ/sát thương từ đạn**. Nó xét vật cản và chi phí phá gạch; dự báo đạn trên
bản sao với giả định xe giữ vị trí, không bắn thêm. Đây là ước lượng, không bảo đảm
đường đi hoặc sát thương dự báo sẽ xảy ra. Xem [hàm đánh giá](task2/heuristics.py).

Bản không heuristic có thể liên tục chọn FIRE nếu chưa thấy thắng/thua trong độ
sâu tìm kiếm và các nhánh cùng điểm 0. Đây là hạn chế của baseline giới hạn độ sâu;
điểm 0 ở ngưỡng cắt không chứng minh trạng thái sẽ hòa. Bản thuần vẫn có thể chọn
né hoặc di chuyển nếu cây tìm kiếm nhìn thấy kết quả phân biệt được.

Code hiện tại **không dùng TT, phạt lặp hoặc lệnh ép tank di chuyển**. Bảng Tab hiển
thị giá trị/cận và chuỗi nước dự đoán (PV); chuỗi này không ép đối thủ làm theo.

## 5. Luật và bản đồ

Trong trận hai AI, thứ tự mô hình hóa là **P0 hành động → P1 hành động → cập nhật
đạn**. P1 nhìn thấy trạng thái sau nước P0; đây là game luân phiên thông tin đầy đủ,
không phải hai bên chọn nước đồng thời kín.

| Thực thể | HP khởi tạo | Sát thương mỗi hit |
| --- | ---: | ---: |
| Tank | 6 | 1 |
| Base | 9 | 1 |
| Tường gạch | 3 | 1 |

- Có sáu loại hành động: MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY.
- Di chuyển tối đa một ô; ô bị chặn có thể chỉ đổi hướng. Đạn bay theo hướng xe.
- Đạn đi tối đa **3 ô mỗi cycle**, kiểm tra từng ô và dừng ngay khi trúng vật cản.
- Mất tank hoặc base thì thua. Hai bên cùng mất điều kiện sống trong một cập nhật
  được quy ước hòa. Có sát thương phe mình; thép không phá được.
- Luật game không tự kết thúc vì số cycle. Các quy ước va chạm được ghi trong REPORT.

AI WARGAME có **40 map**: `default`, `open`, `walls`, `defense`, `bullet` và
`original_01` … `original_35`. SOLO SORTIE chỉ dùng năm map cơ sở.

- `levels/`: 35 bản đồ nguồn của Battle City gốc.
- `levels_ai/`: bản chuyển 13×13 mà chế độ hai AI sử dụng, kèm manifest vị trí xe.

Map gốc được thích nghi sang địa hình của mô hình AI, không giữ đầy đủ cơ chế
nước/cỏ/băng. Định dạng, quy tắc chuyển và cách chỉnh map:
[levels_ai/README.md](levels_ai/README.md).

## 6. Nhập AI của nhóm khác

1. Đặt file `.py` trong `task2/` hoặc tạo thư mục `agents/` cạnh `tanks.py`.
2. File cung cấp `create_agent(player_id)` trả về đối tượng có `choose_action`/`act`,
   hoặc cung cấp trực tiếp hàm `choose_action(state)`/`act(state)` ở cấp module.
3. Tại màn hình cấu hình AI WARGAME, nhấn **F5** rồi chọn mục **FILE: tên_file.py**.

Agent trả về hành động hợp lệ dưới dạng `Action`, số enum hoặc tên như `"FIRE"`,
`"MOVE_LEFT"`, `"STAY"`; có thể trả tuple `(action, info_dict)`. Nếu khai báo tham
số tương ứng, loader chuyển tiếp `time_limit_ms` và `history`. Đối tượng có
`reset(player_id)` sẽ được gọi khi tạo agent cho trận.

Ví dụ có sẵn: [task2/external_greedy.py](task2/external_greedy.py). Đây là AI mẫu
để kiểm tra tích hợp, không phải cấu hình thứ năm trong bộ so sánh của đề.
AI bên ngoài phải tự tuân thủ ngân sách; giao diện không cưỡng bức ngắt hàm đang chạy.

## 7. Kiểm thử và thực nghiệm

Chạy kiểm thử tại thư mục gốc:

```bash
python -m unittest discover -s tests -v
```

`tests/test_core.py` có 22 kiểm thử: oracle vét cạn/cây tính tay, so điểm giữa hai
thuật toán cùng evaluator, luật game, tắt PV, tạo evaluator mới cho mỗi phép đo và
phân biệt giới hạn môi trường với terminal thật.

**Đo tìm kiếm trên cùng trạng thái:**

```bash
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output benchmark_results.csv --summary benchmark_summary.csv
```

**Cho các AI đối đầu, đổi bên:**

```bash
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output tournament_results.csv --summary tournament_summary.csv
```

`benchmark.py` tạo engine/evaluator mới cho mỗi lượt đo, không dùng lại cache giữa
các lượt. Benchmark và tournament đều tắt PV; CSV tách `order_evals` và `leaf_evals`.
Không có TT nên khác biệt giữa hai thuật toán cùng evaluator không kèm lợi ích TT.

`--max-cycles` **chỉ dừng bộ chạy thí nghiệm**, không nằm trong trạng thái mà search
đánh giá. Trận chưa có kết quả khi hết ngân sách được ghi `stopped`/`unfinished`,
không tính thành hòa. Giao diện chơi bình thường không tự giới hạn số cycle.

Dữ liệu đã đo nằm trong `experiments/`: 240 lượt snapshot và 60 trận đổi bên trên
năm map cơ sở. Hướng dẫn tái hiện và điều kiện đo:
[experiments/README.md](experiments/README.md). Kết quả trên Linux/Python 3.12.14,
chưa phải máy macOS Intel i5 của đề; không suy ra heuristic luôn thắng hoặc nhanh hơn.

## 8. Cấu trúc mã nguồn

```text
NMTTNT/
├── tanks.py                   # Điểm chạy, menu và tài nguyên Pygame
├── ai_battle.py               # UI, kết nối backend và điều phối trận
├── presentation.py            # Nội suy đạn/hiệu ứng; không chọn hành động AI
├── arena.py                   # Phần mở rộng một người đấu bốn NPC
├── task2/
│   ├── game.py                # Trạng thái, hành động, luật và terminal
│   ├── search.py              # Minimax, Alpha-Beta, depth và deadline
│   ├── heuristics.py          # TerminalEvaluator và HeuristicEvaluator
│   ├── agent.py               # API agent và bộ chạy trận
│   ├── benchmark.py           # Đo bốn cấu hình trên cùng snapshot
│   ├── tournament.py          # Trận đổi bên, thống kê và xuất CSV
│   ├── original_maps.py       # Đọc/chuyển map gốc
│   └── external_greedy.py     # Ví dụ AI ngoài
├── images/                    # Sprite
├── fonts/                     # Font pixel
├── sounds/                    # Âm thanh
├── levels/                    # Map nguồn
├── levels_ai/                 # Map đã chuyển và manifest
├── tests/test_core.py         # Kiểm thử lõi
├── experiments/               # Dữ liệu và điều kiện thực nghiệm
├── requirements.txt
├── README.md
└── REPORT.md
```

`presentation.py` làm đạn hiển thị mượt giữa các ô. Luật di chuyển/va chạm/sát thương
vẫn thuộc `game.py`, còn quyết định thuộc `search.py` và `heuristics.py`. Không xóa
trực tiếp file này vì `ai_battle.py` đang nhập lớp `BulletPlayback` từ đó.

## 9. Nộp bài

Giữ toàn bộ mã nguồn, tài nguyên, `tests/`, `experiments/`, `requirements.txt` và
báo cáo. Không cần nộp `.git/`, `.venv/`, `venv/`, `__pycache__/`, file `.pyc`,
`.DS_Store` hoặc `.hiscore`. Trước khi đóng gói, chạy lại các lệnh kiểm thử và mở game.

Nguồn nền và tài nguyên: [raitisg/battle-city-tanks](https://github.com/raitisg/battle-city-tanks)
và mã nguồn người dùng cung cấp.
