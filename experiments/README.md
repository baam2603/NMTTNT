# Thực nghiệm bốn cấu hình của đề

Profile `assignment_four_modes_v1`. Chỉ giữ số liệu của Minimax, Alpha-Beta,
Heuristic Minimax và Heuristic Minimax + Alpha-Beta. Hai bản thuần dùng terminal-only;
hai bản heuristic dùng cùng hàm H. Không TT, PV tắt trong cả hai giao thức.
Cấu hình/hash nguồn/môi trường trong environment.json; đo trên Linux x86_64,
Python 3.12.14, chưa phải máy macOS Intel i5 của đề.

## Snapshot cùng trạng thái, cùng depth

search_fixed_depth.csv: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần × 4 mode;
search_fixed_depth_summary.csv: 80 nhóm. Mỗi phép đo tạo engine/evaluator mới;
cache có thể được dùng trong một lần tìm kiếm, không được dùng lại giữa các lần đo.
Seed 42 xáo thứ tự mode. Mọi lượt đạt depth yêu cầu; từng cặp cùng evaluator khớp điểm.

CSV tách order_evals và leaf_evals, tổng total_evals, nút, lá, nhánh cắt và depth_reached.
track_pv=False là điều kiện đo, không phải tuỳ chọn được bật riêng cho Alpha-Beta.
Lặp cùng snapshot phục vụ đo thời gian, không tạo các trận độc lập.

```sh
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output experiments/search_fixed_depth.csv --summary experiments/search_fixed_depth_summary.csv
```

## Trận đối đầu đổi bên

tournament_fixed_depth.csv: 60 trận = 5 map × 6 cặp × 2 bên; depth 3, không deadline,
dừng thí nghiệm sau 60 cycle; tournament_fixed_depth_summary.csv tổng hợp kết quả.
max_cycles thuộc bộ chạy, không thuộc GameState/search. Hết ngân sách mà chưa có
kết quả được ghi stopped/unfinished, không tính hòa. Hòa chỉ là phá hủy đồng thời.
CSV ghi cả leaf_evals/order_evals; không có agent fault trong bộ đo đã xuất bản.

```sh
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output experiments/tournament_fixed_depth.csv --summary experiments/tournament_fixed_depth_summary.csv
```

Các agent reset ở đầu trận; cache heuristic tái dùng trong trận. Thời gian trong
trận phụ thuộc trạng thái đã đi qua, không thay thế benchmark cùng snapshot.
Các kết quả chỉ áp dụng map, vị trí, depth và ngân sách đã ghi; không khẳng định
heuristic luôn nhanh hơn/thắng hoặc terminal-only phải luôn đứng bắn.

Có thể chạy thêm cùng ngân sách thời gian (chưa xuất bản số liệu cho giao thức này):

```sh
python task2/tournament.py --scenarios default open walls --depth 6 --time-limit-ms 60 --max-cycles 60 --output equal_time_results.csv --summary equal_time_summary.csv
```

benchmark.py --scenarios all gồm 40 map: 5 tình huống cơ sở và 35 map chuyển từ gốc.
Kết quả và các giả định chi tiết trong [REPORT.md](../REPORT.md).
