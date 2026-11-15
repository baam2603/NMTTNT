# NMTTNT — Tank Battle / Adversarial Search

Bản mã nguồn Python/Pygame với Minimax/Alpha-Beta dùng đánh giá cơ bản hoặc
nâng cao. Có thêm hai cấu hình terminal-only để đối chứng không heuristic đúng
nghĩa. Giữ giao diện classic và hoạt ảnh đạn.
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

- **AI BATTLE:** mặc định ALPHA-BETA (BASIC) đấu HEURISTIC ALPHA-BETA. Có bốn lựa
  chọn chính và hai lựa chọn CONTROL: TERMINAL MINIMAX/ALPHA-BETA. Nhấn B ở setup
  chọn 60/120/250 ms hoặc FULL DEPTH. Dòng gợi ý và Tab ghi rõ evaluator.
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
Giữ cùng map, vị trí, độ sâu hoặc ngân sách thời gian và đổi bên để so sánh.
Nhấn Tab để xem evaluator, điểm/cận, số nút và độ sâu thực đã hoàn tất.

| Cấu hình trên UI | Điểm chưa kết thúc ở ngưỡng cắt | Cắt tỉa |
| --- | --- | --- |
| MINIMAX (BASIC) | HP + khoảng cách Manhattan tới căn cứ địch | Không |
| ALPHA-BETA (BASIC) | Cùng đánh giá cơ bản | Có |
| HEURISTIC MINIMAX | HP + đường tới vị trí bắn + ngắm + đạn | Không |
| HEURISTIC ALPHA-BETA | Cùng đánh giá nâng cao | Có |
| CONTROL: TERMINAL MINIMAX | 0 trung tính, không heuristic | Không |
| CONTROL: TERMINAL ALPHA-BETA | 0 trung tính, không heuristic | Có |

**BASIC cũng là heuristic đơn giản.** Không gọi hai bản BASIC là “không heuristic”.
Minimax/Alpha-Beta là cơ chế tìm kiếm; evaluator là thông tin đánh giá tại ngưỡng
cắt. BASIC giúp phân biệt mất HP hoặc tiến tới mục tiêu; nâng cao thêm thông tin
vật cản, vị trí bắn và đạn. Mọi cấu hình giữ utility terminal +10000/−10000/0 và
ưu tiên thắng sớm/thua muộn bằng độ sâu còn lại. Không ép di chuyển/ngẫu nhiên.

Để trình bày đối chứng **không/có heuristic**, chọn hai CONTROL và hai HEURISTIC;
không cần sửa code. Ví dụ đo đúng bốn cấu hình này:

```sh
python task2/benchmark.py --modes terminal_minimax terminal_alphabeta heuristic_minimax heuristic_alphabeta --scenarios default open walls --players both --depths 2 4 --repeats 3
python task2/tournament.py --modes terminal_minimax terminal_alphabeta heuristic_minimax heuristic_alphabeta --scenarios default open walls --depth 3 --max-cycles 40
```

Terminal-only không xét HP/khoảng cách khi chưa kết thúc; điểm 0 ở ngưỡng cắt không
chứng minh hòa. Nó vẫn có thể đứng bắn khi đồng điểm, nhưng né nếu tìm thấy nguy cơ
thua trong cây. BASIC còn có thể mắc ở vật cản vì Manhattan không biết đi vòng;
đánh giá nâng cao cũng chỉ là ước lượng. Không cấu hình nào bảo đảm tối ưu cả trận.
Các bộ dữ liệu cơ bản/nâng cao và terminal-only được ghi riêng, cùng điều kiện.

## Nguồn gốc

Phát triển từ [raitisg/battle-city-tanks](https://github.com/raitisg/battle-city-tanks)
và mã nguồn/AI người dùng cung cấp. Tài nguyên gốc được giữ để chạy chương trình.
