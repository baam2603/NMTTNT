# Kết quả thực nghiệm còn sử dụng

Các CSV là số liệu đo tham khảo trên Python 3.12.14 / Linux x86_64, không phải máy
macOS Intel i5 của đề. Đã gỡ bản ghi của các map không còn dùng và tính lại bảng
tổng hợp. **Giá trị thời gian trong các bản ghi còn lại không được đo lại hoặc sửa.**
Các đợt đo gốc chạy tuần tự; thời gian thực tế phụ thuộc máy và tải hệ thống.

## Tìm kiếm cùng độ sâu

`search_fixed_depth.csv`: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần đo × 4 cấu hình.
Các map là DEFAULT, OPEN, WALLS, DEFENSE và BULLET. Mọi lượt hoàn thành độ sâu yêu
cầu; cặp cùng evaluator khớp giá trị. `search_fixed_depth_summary.csv` chứa thời
gian median/mean, số nút, đánh giá và cắt tỉa. Lặp cùng trạng thái phục vụ đo thời
gian, không phải các trận độc lập.

## Đối đầu cùng độ sâu, đổi bên

60 trận trên 5 map; depth 3, giới hạn 60 vòng, không deadline, phạt lặp = 0.
Các cấu hình chơi với nhiều đối thủ. Không có agent fault trong các bản ghi còn lại.

| Cấu hình | Trận | Thắng | Thua | Hòa | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 30 | 1 | 15 | 14 | 1.078 | 51.09 |
| heuristic_alphabeta | 30 | 15 | 1 | 14 | 2.4 | 63.11 |
| heuristic_minimax | 30 | 15 | 1 | 14 | 5.764 | 221.63 |
| minimax | 30 | 1 | 15 | 14 | 2.668 | 212.09 |

Thời gian trung bình trong trận còn phụ thuộc trạng thái mỗi agent đi qua; dùng
benchmark snapshot để đối chiếu chi phí tìm kiếm trên cùng trạng thái.
Các dữ liệu đối đầu cùng ngân sách thời gian trước đây chỉ thuộc map đã gỡ nên
không còn được đưa vào gói nộp. Chương trình vẫn hỗ trợ giao thức này qua
`--time-limit-ms`; không trình bày số liệu chưa đo cho các map đang dùng.

## Chạy lại

```sh
python task2/benchmark.py --scenarios default open walls defense bullet --players both --depths 2 4 --repeats 3 --output experiments/search_fixed_depth.csv --summary experiments/search_fixed_depth_summary.csv
python task2/tournament.py --scenarios default open walls defense bullet --depth 3 --max-cycles 60 --output experiments/tournament_fixed_depth.csv --summary experiments/tournament_fixed_depth_summary.csv
```

Ví dụ đo thêm cùng ngân sách thời gian trên các map còn lại:

```sh
python task2/tournament.py --scenarios default open walls --depth 6 --time-limit-ms 30 --max-cycles 20 --output equal_time_results.csv --summary equal_time_summary.csv
```

35 map ORIGINAL được nhập sau đợt đo, không nằm trong các CSV tham khảo này.
`--scenarios all` hiện gồm 40 map (5 map kiểm tra + 35 map nhập). Các tỷ lệ chỉ áp
dụng map, vị trí, độ sâu và giới hạn đã ghi; không khẳng định heuristic luôn thắng
hoặc luôn nhanh hơn. Tìm kiếm hữu hạn không bảo đảm tối ưu cả trận.
