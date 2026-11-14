# Kết quả chạy tham khảo

Các file CSV chứa kết quả thực tế của bản cập nhật hiện tại. Môi trường: Python 3.12.14,
Linux x86_64; không phải cấu hình macOS Intel i5 của đề. Thời gian phụ thuộc máy và tải hệ thống.
Các lệnh đo chạy tuần tự. Không dùng số liệu này để khẳng định tối ưu hơn mọi phiên bản cũ.

## So sánh tìm kiếm cùng độ sâu

`search_fixed_depth.csv`: 384 lần tìm kiếm = 8 map × 2 bên × 2 độ sâu (2,4) ×
3 lần đo × 4 cấu hình. Mỗi lần đều hoàn thành độ sâu yêu cầu. Cặp plain MM/AB và
cặp heuristic MM/AB khớp giá trị trong tất cả các nhóm. Lặp lại ở đây dùng đo
thời gian, không phải các trận đấu độc lập. `search_fixed_depth_summary.csv`
lưu median/mean thời gian, số nút, số đánh giá và cắt tỉa.

## Đấu cùng độ sâu, đổi bên

96 trận trên 8 map; depth 3 cho mọi bên; giới hạn 60 vòng; không deadline;
phạt lặp = 0. Các nhóm trong bảng có chơi lẫn nhau, vì vậy không diễn giải mỗi
hàng như chỉ đấu với một đối thủ cố định. Mọi trận có faults = 0.

| Cấu hình | Trận | Thắng | Thua | Hòa | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 48 | 1 | 27 | 20 | 0.988 | 50.84 |
| heuristic_alphabeta | 48 | 28 | 2 | 18 | 2.106 | 62.41 |
| heuristic_minimax | 48 | 28 | 2 | 18 | 5.228 | 222.29 |
| minimax | 48 | 1 | 27 | 20 | 2.474 | 211.45 |

Các chỉ số trung bình trong trận còn phụ thuộc các trạng thái mỗi agent đi qua;
dùng benchmark snapshot cùng trạng thái ở phần đầu để so sánh chi phí tìm kiếm trực tiếp.

## Đấu cùng ngân sách thời gian

24 trận trên H_DODGE và ASYMMETRIC, đổi bên; 30 ms mỗi nước, depth tối đa 6,
giới hạn 20 vòng. Độ sâu thực tế khác nhau là kết quả của giao thức cùng thời gian;
không trộn số liệu này với so sánh cùng độ sâu. Overtime đếm các nước vượt 33 ms
(tính cả chi phí gọi agent), không giấu những lần vượt soft deadline.

| Cấu hình | Thắng | Thua | Hòa | Mean depth | Mean ms/nước | Overtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 0 | 1 | 11 | 5.92 | 17.244 | 1 |
| heuristic_alphabeta | 4 | 1 | 7 | 5.11 | 27.475 | 5 |
| heuristic_minimax | 2 | 1 | 9 | 3.45 | 28.512 | 3 |
| minimax | 0 | 3 | 9 | 4.15 | 28.435 | 2 |

## Chạy lại từ thư mục chứa tanks.py

```sh
python task2/benchmark.py --scenarios all --players both --depths 2 4 --repeats 3 --output experiments/search_fixed_depth.csv --summary experiments/search_fixed_depth_summary.csv
python task2/tournament.py --scenarios default open walls defense bullet h_detour h_dodge asymmetric --depth 3 --max-cycles 60 --output experiments/tournament_fixed_depth.csv --summary experiments/tournament_fixed_depth_summary.csv
python task2/tournament.py --scenarios h_dodge asymmetric --depth 6 --time-limit-ms 30 --max-cycles 20 --output experiments/tournament_equal_time.csv --summary experiments/tournament_equal_time_summary.csv
```

Kết quả này chỉ nói về các trạng thái xuất phát, map, độ sâu và giới hạn vòng đã
chọn. Các map minh họa có tình huống thiết kế để làm rõ evaluator, không phải mẫu
ngẫu nhiên của mọi map. Số liệu không chứng minh heuristic luôn thắng hoặc luôn
nhanh hơn. Tìm kiếm sâu hữu hạn không bảo đảm tối ưu cả trận.
