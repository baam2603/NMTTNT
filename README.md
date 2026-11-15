# Tank Battle — Adversarial Search

Bản nộp Python/Pygame với đúng bốn cấu hình: Minimax, Alpha-Beta, Heuristic Minimax
và Heuristic Minimax kết hợp Alpha-Beta. Mô hình, giả định và số liệu: [REPORT.md](REPORT.md).

## Chạy chương trình

Cần Python 3.10 trở lên. Tại thư mục chứa `tanks.py`:

```sh
python -m pip install -r requirements.txt
python tanks.py
```

Giữ các thư mục `images/`, `fonts/`, `sounds/`, `levels/`, `levels_ai/` khi chạy.
Map gốc được chuyển cho trận hai AI trong `levels_ai/`; quy tắc chuyển tại
[levels_ai/README.md](levels_ai/README.md).

## Bốn cấu hình

| Mode | Đánh giá trạng thái chưa kết thúc tại ngưỡng độ sâu | Cắt tỉa |
| --- | --- | --- |
| minimax | 0 trung tính, không heuristic | Không |
| alphabeta | 0 trung tính, không heuristic | Có |
| heuristic_minimax | HP + đường tới vị trí bắn + ngắm + đạn | Không |
| heuristic_alphabeta | Cùng heuristic | Có |

Hai bản thuần dùng `TerminalEvaluator`, hai bản còn lại dùng `HeuristicEvaluator`.
Tất cả dùng utility terminal +10000/−10000/0 và ưu tiên thắng sớm/thua muộn bằng độ
sâu còn lại. Đây là tìm kiếm giới hạn độ sâu; điểm 0 ở ngưỡng cắt không chứng minh hòa.
Bản thuần có thể chọn FIRE nhiều lần khi các nhánh đồng điểm. Không ép xe di chuyển.

Không dùng TT hoặc phạt lặp. Giao diện có thể ghi chuỗi nước dự đoán (PV);
benchmark và tournament tắt PV để không tính
chi phí phục vụ UI vào so sánh tìm kiếm.

## Điều khiển

- **AI BATTLE:** hai AI, mặc định Alpha-Beta thuần đấu Heuristic Alpha-Beta.
- Setup: lên/xuống chọn dòng, trái/phải đổi agent/depth/map, Enter bắt đầu, Esc về menu.
- B: chọn 60/120/250 ms mỗi nước hoặc FULL DEPTH. FULL DEPTH là hoàn tất depth đã
  chọn, không phải tìm hết cả ván. Depth tính theo một hành động của một bên.
- Dòng MAP: O tới ORIGINAL_01; PageUp/PageDown nhảy 5 map; Home/End tới đầu/cuối.
- Trong trận: P dừng, N đi một hành động, Tab phân tích, V đường ngắm, +/- tốc độ,
  R chơi lại, Esc về setup. Hoạt ảnh đạn không thay đổi trạng thái gửi cho AI.
- F5 quét AI ngoài trong `task2/` hoặc `agents/`; cách tích hợp ở REPORT.
- **1 PLAYER** là phần mở rộng bàn phím đấu 4 NPC: mũi tên, Space bắn, X bỏ lượt.
  Mỗi NPC dùng bản chiếu hai xe; không thuộc phép đo đối kháng hai AI của báo cáo.

Luật game kết thúc khi tank hoặc base bị phá; UI không tự tuyên hòa sau 300 cycle.
Giới hạn `--max-cycles` của tournament chỉ dừng thí nghiệm và ghi **unfinished**,
không sửa luật hay trạng thái terminal mà search nhìn thấy.

## Kiểm thử và đo lại

```sh
python -m unittest discover -s tests -v
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output benchmark_results.csv --summary benchmark_summary.csv
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output tournament_results.csv --summary tournament_summary.csv
```

Mỗi phép đo snapshot tạo engine/evaluator mới, PV tắt, không TT. CSV tách
`order_evals` và `leaf_evals`. Trận hết ngân sách môi trường được thống kê riêng
với hòa do hai bên cùng bị phá. Dữ liệu đã đo: [experiments/README.md](experiments/README.md).

## Các file để đọc khi vấn đáp

| File | Vai trò |
| --- | --- |
| `task2/game.py` | Trạng thái, hành động, chuyển trạng thái, đạn, HP, thắng/thua |
| `task2/search.py` | Minimax, Alpha-Beta, giới hạn độ sâu/thời gian và PV cho UI |
| `task2/heuristics.py` | Utility terminal và hàm heuristic |
| `task2/agent.py` | SearchAgent, API agent và bộ chạy trận có giới hạn môi trường |
| `ai_battle.py` | Pygame UI trận AI, nhập AI ngoài, bảng phân tích |
| `tanks.py` | Điểm chạy, menu classic, tải tài nguyên |
| `presentation.py` | Hoạt ảnh đạn, tách khỏi tìm kiếm |
| `task2/benchmark.py` / `task2/tournament.py` | Hai giao thức thí nghiệm |
| `tests/test_core.py` | Oracle vét cạn, luật game, công bằng khi đo |

35 map gốc được đọc/chuyển bởi `task2/original_maps.py`. `task2/external_greedy.py`
là ví dụ nhập AI ngoài. `arena.py` dành riêng phần mở rộng một người/bốn NPC.

Nguồn nền/tài nguyên: [raitisg/battle-city-tanks](https://github.com/raitisg/battle-city-tanks)
và mã nguồn người dùng cung cấp.
