# Kết quả thực nghiệm còn sử dụng

Các CSV là số liệu đo tham khảo trên Python 3.12.14 / Linux x86_64, không phải máy
macOS Intel i5 của đề. Đã gỡ các bản ghi của map không còn dùng và tính lại các
bảng tổng hợp từ bản ghi còn lại; **không đo lại hoặc sửa thời gian từng bản ghi**.
Các đợt đo gốc chạy tuần tự. Thời gian thực tế phụ thuộc máy và tải hệ thống.

## Tìm kiếm cùng độ sâu

`search_fixed_depth.csv`: 336 lượt = 7 map × 2 bên × depth 2/4 × 3 lần đo × 4 cấu hình.
Mọi lượt hoàn thành depth yêu cầu; các cặp cùng evaluator khớp giá trị. File
`search_fixed_depth_summary.csv` lưu median/mean thời gian, nút, evals và cắt tỉa.
Lặp lại cùng trạng thái dùng đo thời gian, không phải các trận đấu độc lập.

## Đấu cùng độ sâu, đổi bên

84 trận trên 7 map: depth 3, giới hạn 60 vòng, không deadline, phạt lặp = 0.
Mọi trận còn lại có faults = 0. Các cấu hình chơi với nhiều đối thủ.

| Cấu hình | Trận | Thắng | Thua | Hòa | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 42 | 1 | 23 | 18 | 0.99 | 50.09 |
| heuristic_alphabeta | 42 | 23 | 1 | 18 | 2.107 | 62.23 |
| heuristic_minimax | 42 | 23 | 1 | 18 | 5.256 | 222.38 |
| minimax | 42 | 1 | 23 | 18 | 2.484 | 208.02 |

Chỉ số trung bình trong trận phụ thuộc các trạng thái mỗi bên đi qua; dùng
benchmark snapshot để đối chiếu chi phí tìm kiếm trên cùng trạng thái.

## Đấu cùng ngân sách thời gian

12 trận trên H_DODGE, đổi bên: 30 ms/nước, depth tối đa 6, giới hạn 20 vòng.
Overtime đếm thời gian gọi agent vượt 33 ms, gồm cả chi phí gọi hàm.

| Cấu hình | Thắng | Thua | Hòa | Mean depth | Mean ms/nước | Overtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 0 | 1 | 5 | 5.88 | 17.677 | 1 |
| heuristic_alphabeta | 3 | 0 | 3 | 5.14 | 27.04 | 2 |
| heuristic_minimax | 1 | 0 | 5 | 3.49 | 28.355 | 0 |
| minimax | 0 | 3 | 3 | 4.19 | 28.495 | 1 |

## Chạy lại

```sh
python task2/benchmark.py --scenarios default open walls defense bullet h_detour h_dodge --players both --depths 2 4 --repeats 3 --output experiments/search_fixed_depth.csv --summary experiments/search_fixed_depth_summary.csv
python task2/tournament.py --scenarios default open walls defense bullet h_detour h_dodge --depth 3 --max-cycles 60 --output experiments/tournament_fixed_depth.csv --summary experiments/tournament_fixed_depth_summary.csv
python task2/tournament.py --scenarios h_dodge --depth 6 --time-limit-ms 30 --max-cycles 20 --output experiments/tournament_equal_time.csv --summary experiments/tournament_equal_time_summary.csv
```

35 map ORIGINAL được nhập sau đợt đo, không nằm trong các CSV tham khảo này.
`--scenarios all` hiện gồm 42 map (7 map cũ và 35 map nhập). Các tỷ lệ chỉ áp dụng
map, vị trí, độ sâu và giới hạn đã ghi; không khẳng định heuristic luôn thắng
hoặc luôn nhanh hơn. Tìm kiếm hữu hạn không bảo đảm tối ưu cả trận.
