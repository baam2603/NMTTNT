# NMTTNT — Tank Battle / Adversarial Search

Bản mã nguồn gọn để nộp bài, dùng Python/Pygame. Minimax/Alpha-Beta dùng đánh giá
cơ bản hoặc nâng cao; giữ quy tắc game, giao diện classic và hoạt ảnh đạn.
Mô hình zero-sum, giải thích thuật toán và kết quả: [REPORT.md](REPORT.md).

## Cài đặt và chạy

Cần Python 3.10 trở lên. Mở terminal tại thư mục chứa `tanks.py`:

```sh
python -m pip install -r requirements.txt
python tanks.py
```

Giữ nguyên các thư mục tài nguyên khi nộp/chạy; chỉ lấy bốn file thuật toán sẽ không
chạy được giao diện. Game tải `images/sprites.gif`, font và âm thanh khi khởi tạo.

## Các file chính

| File | Vai trò |
| --- | --- |
| `task2/search.py` | Minimax, Alpha-Beta, bảng chuyển vị, tìm sâu dần |
| `task2/heuristics.py` | Utility thắng/thua và đánh giá heuristic |
| `task2/game.py` | Trạng thái, hành động, chuyển trạng thái, đạn, HP, kết thúc |
| `task2/agent.py` | SearchAgent, API agent và điều phối trận |
| `tanks.py` | Điểm chạy chương trình, menu classic và khởi tạo tài nguyên |
| `ai_battle.py` | UI chọn thuật toán/map, trận AI và bảng phân tích |
| `presentation.py` | Hoạt ảnh đạn; không điều khiển quyết định của AI |
| `task2/benchmark.py` | Đăng ký map và đo bốn cấu hình trên cùng trạng thái |
| `task2/tournament.py` | Đối đầu đổi bên theo cùng độ sâu/cùng thời gian |
| `task2/original_maps.py` | Chuyển/đọc 35 map gốc |
| `task2/external_greedy.py` | AI mẫu để thử nhập thuật toán ngoài qua F5 |
| `arena.py` | Phần mở rộng một người đấu 4 NPC |

## Các thư mục cần giữ

```text
fonts/          Font pixel
images/         Chỉ còn sprites.gif được game sử dụng
sounds/         Âm thanh được nạp khi mở game
levels/         Nguồn 35 map gốc, phục vụ bộ chuyển đổi
levels_ai/      35 map đã chuyển + manifest, được AI BATTLE sử dụng
experiments/    CSV và môi trường đo để đối chiếu yêu cầu thực nghiệm
```

`levels/` cần cho việc chuyển lại bản đồ; game AI đọc bản chuyển trong `levels_ai/`.
Quy tắc nước/cỏ/băng và vị trí xe: [levels_ai/README.md](levels_ai/README.md).
Cách đọc số liệu và chạy lại thí nghiệm: [experiments/README.md](experiments/README.md).

## Chế độ và điều khiển

- **AI BATTLE:** hai AI; chọn MINIMAX (BASIC), ALPHA-BETA (BASIC), HEURISTIC
  MINIMAX hoặc HEURISTIC ALPHA-BETA. Nhấn B ở setup chọn 60/120/250 ms hoặc FULL DEPTH.
- **1 PLAYER:** bàn phím đấu 4 NPC. Phần này dùng bản chiếu hai xe cho mỗi NPC;
  không phải tìm kiếm đối kháng đầy đủ năm tác nhân. Các map gốc nhập dành riêng cho AI BATTLE.
- Setup: lên/xuống chọn dòng, trái/phải đổi giá trị, Enter bắt đầu, Esc quay lại.
- Dòng MAP: O tới ORIGINAL_01, PageUp/PageDown nhảy 5 map, Home/End tới đầu/cuối.
- Trong trận: P dừng, N đi một hành động, Tab phân tích, V đường ngắm, +/- tốc độ,
  R chơi lại, Esc về setup. Hoạt ảnh lượt đã áp dụng được phát hết khi dừng.
- Người chơi: mũi tên di chuyển/xoay, Space bắn, X bỏ lượt.
- F5 ở setup quét AI ngoài trong `task2/` hoặc thư mục `agents/` do bạn tạo.

## Đo lại bốn cấu hình

```sh
python task2/benchmark.py --scenarios default open walls --players both --depths 2 4 --repeats 3 --output benchmark_results.csv --summary benchmark_summary.csv
python task2/tournament.py --scenarios default open walls --depth 3 --max-cycles 40 --output tournament_results.csv --summary tournament_summary.csv
```

Các map kiểm tra gồm DEFAULT, OPEN, WALLS, DEFENSE và BULLET.
ORIGINAL_01 … ORIGINAL_35 dùng địa hình chuyển từ map gốc.
Giữ cùng điều kiện và đổi bên để so sánh. Hai bản BASIC dùng HP + khoảng cách
Manhattan tới căn cứ địch; hai bản nâng cao thêm đường tới vị trí bắn có xét hướng,
chi phí phá gạch, đường ngắm và dự báo đạn. BASIC cũng là heuristic theo định nghĩa;
không gọi nó là “không heuristic”. Nhấn Tab để thấy evaluator, điểm/cận và độ sâu thực.

Bản terminal-only cũ vẫn dùng được làm đối chứng qua API, không đổi luật tìm kiếm:

```python
# Chạy tại thư mục task2/, hoặc thêm task2/ vào sys.path.
from game import GameState
from search import choose_action
from heuristics import TerminalEvaluator

action, info = choose_action(GameState.from_layout(), depth=4, mode="alphabeta",
                             evaluator=TerminalEvaluator())
```

Bản đối chứng trả 0 ở trạng thái chưa kết thúc nên vẫn có thể chọn FIRE khi đồng
điểm. BASIC còn hạn chế khi gặp đường vòng/thép; bản nâng cao tốn thêm chi phí đánh
giá. Không cấu hình nào bảo đảm thắng hoặc luôn phải di chuyển mỗi lượt.

## Nguồn gốc

Phát triển từ [raitisg/battle-city-tanks](https://github.com/raitisg/battle-city-tanks)
và mã nguồn/AI người dùng cung cấp. Tài nguyên gốc được giữ để chạy chương trình.
