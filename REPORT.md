# Tank Battle — Mô hình và thực nghiệm đối kháng

## 1. Mô hình zero-sum

Hai người chơi P0 và P1 biết toàn bộ trạng thái. Luật là xác định, không có yếu tố ngẫu nhiên.

| Thành phần        | Mô hình                                                                              |
| ----------------- | ------------------------------------------------------------------------------------ |
| Trạng thái        | Thép, gạch (có HP), 2 tank (ô, hướng, HP), 2 base, đạn (ô, hướng, chủ), bên đến lượt |
| Hành động         | MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY (chỉ trả hành động hợp lệ)     |
| Chuyển trạng thái | Thực hiện trên bản sao: đi tối đa 1 ô, bắn theo hướng xe, rồi cập nhật đạn           |
| Terminal          | Có tank hoặc base bị phá (không phụ thuộc số cycle)                                  |
| Utility           | Thắng +10000, thua −10000, hai bên cùng mất thì hòa 0                                |

- Utility và heuristic tính theo góc nhìn của người đang tìm kiếm (đổi người thì đổi dấu).
- Khi gặp terminal, độ sâu còn lại được cộng thêm để ưu tiên **thắng sớm, thua muộn** (áp dụng cho cả 4 cấu hình).
- HP khởi tạo: tank 6, base 9, gạch 3. Mỗi lần trúng đạn mất 1 HP. Thép không bị phá.
- Sau mỗi cycle, đạn bay tối đa 3 ô, kiểm tra từng ô và dừng khi trúng vật cản.
- Số cycle chỉ để hiển thị, không ảnh hưởng utility hay điều kiện terminal.

## 2. Các giả định đã chọn

Đề chưa quy định hết các tình huống nên nhóm chọn như sau (search, giao diện và bộ thí nghiệm dùng chung):

| Tình huống             | Cách xử lý                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------------------- |
| Thứ tự trong một cycle | P0 đi trước, P1 nhìn trạng thái sau P0 rồi đi, cuối cùng cập nhật đạn (luân phiên, biết đầy đủ thông tin) |
| Đổi hướng              | Ô đích trống: đổi hướng và đi 1 ô. Ô bị chặn: chỉ xoay tại chỗ                                            |
| Đạn gặp đạn            | Cùng ô hoặc hoán đổi ô thì cả hai triệt tiêu                                                              |
| Tank đi vào ô có đạn   | Mất HP bằng số đạn trong ô, các đạn đó biến mất                                                           |
| Cả hai cùng bị phá     | Tính là hòa                                                                                               |
| Bắn trúng phe mình     | Vẫn gây sát thương cho tank/base                                                                          |
| Map có nước/cỏ/băng    | Nước chặn như thép; cỏ/băng thành ô trống                                                                 |

Hành động quay về hướng đang nhìn mà bị chặn không thay đổi gì, nên được thay bằng STAY.

## 3. Bốn cấu hình tìm kiếm

| Cấu hình                       | Giá trị tại lá chưa kết thúc | Cắt tỉa Alpha-Beta |
| ------------------------------ | ---------------------------- | ------------------ |
| Minimax                        | 0                            | Không              |
| Alpha-Beta                     | 0                            | Có                 |
| Heuristic Minimax              | H(s)                         | Không              |
| Heuristic Minimax + Alpha-Beta | H(s)                         | Có                 |

Độ sâu tính theo ply: 1 depth là 1 hành động của một bên. Alpha-Beta cho cùng giá trị với Minimax
(cùng trạng thái, evaluator, depth) nhưng bỏ nhánh khi alpha ≥ beta. Các nước đồng điểm có thể
được chọn khác nhau.

**Hai bản thuần (Minimax, Alpha-Beta)** dùng `TerminalEvaluator`: chỉ có thắng/thua/hòa mới có điểm,
lá chưa kết thúc ở ngưỡng cắt nhận 0. Điểm 0 không có nghĩa là trạng thái sẽ hòa. Nếu chưa thấy
thắng/thua, các nước đồng điểm nên FIRE được giữ theo thứ tự cố định. Khi thấy nguy cơ thua hoặc
cơ hội thắng trong cây, bản thuần vẫn biết né hoặc bắn.

**Hai bản heuristic** dùng cùng một hàm đánh giá:

```
H(s) = 100·ΔHP_base + 80·ΔHP_tank + 10·Δđường_bắn + 30·Δngắm + 60·Δđạn
```

Mỗi Δ là lợi thế của mình trừ đối thủ:

- **Đường bắn:** Dijkstra ngược từ vị trí bắn được base địch, có xét hướng, thép và chi phí phá gạch.
- **Ngắm:** xét vật đầu tiên trên đường đạn và phe của mục tiêu.
- **Đạn:** dự báo tối đa 3 cycle trên bản sao, giả định xe đứng yên và không bắn thêm.

Đây chỉ là ước lượng, không bảo đảm đối thủ không né. Điểm chưa kết thúc bị giới hạn trong
[−9900, 9900] để điểm terminal luôn lớn hơn.

**Không dùng** bảng chuyển vị (TT) hay phạt lặp. Cache đường đi chỉ phục vụ tính heuristic
(tối đa 512 mục, theo địa hình/HP gạch/base), không phải TT của tìm kiếm. Cache được dùng lại
trong một trận và reset khi tạo agent mới.

## 4. Chạy thời gian thực và giao diện

- **Có deadline:** tìm sâu dần từ 1 đến depth đã chọn, lấy kết quả của vòng hoàn tất cuối cùng,
  luôn có hành động hợp lệ dự phòng. Deadline là ngân sách mềm, không ép dừng giữa chừng.
- **Không deadline:** chạy đúng depth yêu cầu.
- **Giao diện Pygame:** AI chạy ở luồng riêng. Tab hiển thị độ sâu thực, thời gian, số nút,
  số lần cắt tỉa, điểm từng nước và PV (chuỗi dự đoán, không ép đối thủ làm theo).
  Ký hiệu `=` là giá trị chính xác, `<=` là cận trên do cắt tỉa.
- **AI của nhóm khác:** đặt file `.py` vào `task2/` hoặc `agents/`, nhấn F5. Cần có
  `create_agent(player_id)` hoặc hàm `choose_action`/`act`. Nước đi trả về được kiểm tra hợp lệ
  trước khi áp dụng (ví dụ: `task2/external_greedy.py`).

## 5. Giới hạn môi trường (không phải luật hòa)

- Trạng thái game không có giới hạn cycle; terminal chỉ xét việc phá hủy. Giao diện bình thường
  không tự kết thúc ván.
- Khi chạy thí nghiệm, `Tournament` dùng `--max-cycles` để tránh chạy vô hạn. Giới hạn này thuộc
  bộ chạy, không được đưa vào trạng thái tìm kiếm.
- Trận hết ngân sách mà chưa có phá hủy được ghi là `unfinished`
  (`reason=experiment_cycle_limit`), **không tính là hòa** và không tính thắng/thua.
- Hòa thật chỉ xảy ra khi hai bên cùng bị phá hủy cùng lúc.

## 6. Thiết kế thí nghiệm

**Benchmark (cùng trạng thái, cùng độ sâu):**

- 5 map: DEFAULT, OPEN, WALLS, DEFENSE, BULLET. Đo cả hai bên, depth 2 và 4, lặp 3 lần.
- Thứ tự các mode được xáo bằng seed 42.
- Mỗi lượt đo tạo engine và evaluator mới, không dùng lại cache.
- Không dùng TT, tắt PV (`track_pv=False`), sắp xếp nước đi tại gốc giống nhau cho hai thuật toán.
- Các chỉ số ghi lại:
  - `nodes`: số lần vào nút tìm kiếm (gồm gốc).
  - `order_evals`: số lần gọi evaluator để sắp xếp gốc.
  - `leaf_evals`: số lần đánh giá lá/terminal.
  - `total_evals = order_evals + leaf_evals`.
  - `time_ms` đã gồm cả chi phí sắp xếp gốc.
- Không so điểm thô giữa hai evaluator khác nhau như cùng một thang chất lượng.

**Đối đầu (tournament):** đổi bên, depth 3, dừng sau 60 cycle, tắt PV. Thời gian trong trận phụ thuộc
các trạng thái đã đi qua và cache nên không dùng để so chi phí. Việc đó dùng benchmark.

Chi tiết dữ liệu, môi trường và lệnh chạy: [experiments/README.md](experiments/README.md).
Máy đo: Python 3.12.14, Linux x86_64 (chưa phải macOS 13.7.8 Intel i5 như đề).

### Kết quả đã đo

- **Benchmark:** 240 lượt đo hoàn thành đúng độ sâu; 120 cặp Minimax/Alpha-Beta cùng evaluator
  cho giá trị khớp nhau.
- **Đối đầu:** 60 trận, trong đó 8 trận chưa kết thúc (hết ngân sách), 8 trận hòa thật do phá hủy
  đồng thời, không có lỗi agent.

| Mode                | Trận | Thắng | Thua | Hòa thật | Chưa kết thúc | Mean ms/nước | Mean nút/nước |
| ------------------- | ---: | ----: | ---: | -------: | ------------: | -----------: | ------------: |
| alphabeta           |   30 |     3 |   19 |        0 |             8 |        1.073 |          55.9 |
| heuristic_alphabeta |   30 |    19 |    3 |        8 |             0 |         4.94 |         59.21 |
| heuristic_minimax   |   30 |    19 |    3 |        8 |             0 |       12.666 |        231.63 |
| minimax             |   30 |     3 |   19 |        0 |             8 |        3.383 |        240.98 |

Mỗi trận có 2 mode tham gia nên mỗi hàng cấu hình có 30 trận, không phải 120 trận độc lập.

## 7. Kiểm chứng và giới hạn

Chạy 22 kiểm thử bằng lệnh `python -m unittest discover -s tests -v`:

- Cây tính tay `max(min(3,5), min(2,9)) = 3`.
- Oracle vét cạn độc lập trên 40 map, hai bên: so điểm, nước tối ưu, cận và PV giữa Minimax và Alpha-Beta.
- Tắt PV không đổi điểm hay nước đi; mỗi lần đo dùng engine/evaluator mới; thống kê đủ
  `order_evals`/`leaf_evals`; đúng 4 mode và đúng evaluator.
- Luật game: di chuyển, HP, va chạm đạn, đạn gặp nhau, tank đi vào đạn, sát thương phe mình,
  phá hủy đồng thời. Bản terminal-only biết né khi cây thấy thua.
- Số cycle lớn không tạo terminal; giới hạn môi trường không tạo hòa; thống kê `unfinished` riêng.

**Giới hạn:**

- Tìm kiếm có giới hạn độ sâu nên không bảo đảm tối ưu cả ván.
- Hình ảnh tank đứng bắn không tự chứng minh search đúng hay sai; dùng oracle và cây tính tay để kiểm chứng.
- Tập map cố định không đủ để kết luận heuristic luôn thắng.
- Chế độ một người chơi với bốn NPC dùng bản chiếu hai xe, không thuộc mô hình zero-sum hai AI của phép đo trên.
