# Tank Battle — Mô hình và thực nghiệm đối kháng

## 1. Công thức hóa zero-sum

Hai người chơi P0/P1 biết toàn bộ trạng thái, luật xác định, không có yếu tố ngẫu nhiên.

| Thành phần | Mô hình |
| --- | --- |
| Trạng thái | Thép, gạch và HP; hai tank (ô, hướng, HP); hai base; đạn (ô, hướng, chủ); bên tới lượt |
| Hành động | MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY; chỉ trả hành động hợp lệ |
| Chuyển trạng thái | Áp dụng trên bản sao; di chuyển tối đa một ô, bắn theo hướng xe; cập nhật va chạm |
| Terminal | Có tank hoặc base bị phá; không phụ thuộc số cycle đã trôi qua |
| Utility | Theo góc nhìn người tìm kiếm: thắng +10000, thua −10000, hai bên cùng mất điều kiện sống thì hòa 0 |

Đổi người đánh giá thì đổi dấu utility/heuristic. Khi gặp terminal trong cây, phần
thưởng độ sâu còn lại ưu tiên thắng sớm/thua muộn, áp dụng giống nhau cho cả bốn cấu hình.
Tank/base/gạch có HP khởi tạo 6/9/3; một hit gây 1 damage. Sau mỗi cycle, đạn tiến
3 ô tối đa, kiểm tra từng ô và dừng ngay khi trúng vật cản. Thép không phá được.
Số cycle là bộ đếm phục vụ hiển thị, không tham gia utility hoặc điều kiện terminal.

## 2. Giả định mô hình hóa được khai báo

Đề chưa quy định hết thứ tự xử lý và các va chạm phụ. Bản này chọn:

| Chỗ cần quy ước | Cách thực hiện |
| --- | --- |
| Lượt trong một cycle | P0 hành động, P1 nhìn trạng thái sau P0 rồi hành động, sau đó cập nhật đạn. Đây là mô hình luân phiên thông tin đầy đủ, không phải chọn nước đồng thời kín |
| Đổi hướng | Ô đích trống: đổi hướng và đi một ô; ô bị chặn: có thể chỉ xoay tại chỗ |
| Đạn gặp đạn | Cùng ô hoặc hoán đổi ô trong một bước thì triệt tiêu |
| Tank vào ô có đạn | Mất HP bằng số đạn trong ô, các đạn đó biến mất |
| Cả hai bên bị phá trong cùng cập nhật | Hòa nếu cả hai cùng mất tank hoặc base |
| Bắn vào phe mình | Có sát thương tank/base; gạch không thuộc phe |
| Map nhập có nước/cỏ/băng | Chuyển sang địa hình của mô hình: nước chặn như thép, cỏ/băng thành trống; xem levels_ai/README |

Hành động quay về hướng đang nhìn mà bị chặn không tạo thay đổi, nên được thay bằng
STAY trong tập hành động hợp lệ. Bắn được mô phỏng theo cùng luật ở mọi cấu hình.
Những giả định trên thống nhất giữa search, UI và bộ chạy thí nghiệm.

## 3. Đúng bốn cấu hình tìm kiếm

| Cấu hình | Lá chưa kết thúc ở ngưỡng cắt | Cắt tỉa Alpha-Beta |
| --- | --- | --- |
| Minimax | 0, không heuristic | Không |
| Alpha-Beta | 0, không heuristic | Có |
| Heuristic Minimax | H(s) | Không |
| Heuristic Minimax + Alpha-Beta | Cùng H(s) | Có |

Minimax lấy MAX ở lượt mình, MIN ở lượt địch. Alpha-Beta trả cùng giá trị khi cùng
trạng thái, evaluator và depth, nhưng bỏ nhánh khi alpha >= beta. Các nước đồng
điểm có thể được chọn khác nhau. Một depth là một hành động của một bên.

Hai bản thuần dùng TerminalEvaluator: thắng/thua/hòa có utility, lá chưa kết thúc
ở ngưỡng cắt nhận 0 trung tính. Đây là baseline giới hạn độ sâu, không phải vét cạn
tới terminal toàn bộ ván. Điểm 0 không chứng minh trạng thái sẽ hòa. Nếu chưa thấy
thắng/thua, các nước có thể đồng điểm và FIRE được giữ theo thứ tự cố định. Nếu nhìn
thấy nguy cơ thua hoặc cơ hội thắng, bản thuần vẫn có thể di chuyển/né/bắn phù hợp.

Hai bản heuristic dùng:

`H(s) = 100 ΔHP_base + 80 ΔHP_tank + 10 Δđường_bắn + 30 Δngắm + 60 Δđạn`.

Mỗi Δ là lợi thế của mình so với đối thủ. Đường bắn dùng Dijkstra ngược tới vị trí
có thể bắn về base địch, xét hướng, thép và chi phí phá gạch. Ngắm xét vật đầu tiên
trên tia và phe của mục tiêu. Đạn được dự báo trên bản sao tối đa 3 cycle, giả định
xe giữ nguyên vị trí/không bắn thêm, dùng chính luật va chạm của engine. Đây là ước
lượng, không bảo đảm đối thủ không né hay đường phá gạch hoàn thành đúng số lượt đó.
Điểm chưa kết thúc giới hạn [-9900,9900] để utility terminal luôn trội hơn.

Bản nộp chỉ có bốn mode trong bảng, không dùng bảng chuyển vị TT hay phạt lặp.
Cache đường đi chỉ là cache tính heuristic theo địa hình/HP gạch/base, giới hạn 512
mục; không phải TT của tìm kiếm. Agent sống tái dùng cache trong trận để chạy nhanh,
reset khi tạo agent mới. Mỗi phép đo snapshot dùng evaluator mới hoàn toàn.

## 4. Chạy thời gian thực và giao diện

Có deadline thì tìm sâu dần từ 1 tới depth chọn; lấy kết quả hoàn tất cuối, luôn có
hành động hợp lệ dự phòng. Đây là ngân sách mềm: không cưỡng bức ngắt một evaluator
hay AI ngoài đang chạy. Không deadline thì hoàn tất đúng depth yêu cầu.

Pygame chạy AI ở luồng riêng, phát hoạt ảnh đạn từ dữ liệu riêng. Tab hiển thị độ
sâu thực, thời gian, nút, cắt tỉa, điểm/cận từng nước và PV. PV là chuỗi dự đoán,
không ép đối thủ làm theo. `=` là giá trị chính xác; `<=` là cận trên do cắt tỉa.

Cơ chế nhập nhóm khác: đặt .py trong task2/ hoặc agents/, nhấn F5. Hỗ trợ
`create_agent(player_id)` trả đối tượng có act, hoặc module có choose_action/act.
Loader chuyển tiếp time_limit_ms/history nếu hàm hỗ trợ, gọi reset nếu có; nước
trả về có thể là Action, số enum hoặc tên, được kiểm tra hợp lệ trước khi áp dụng.
Ví dụ: task2/external_greedy.py. AI ngoài tự tuân thủ ngân sách thời gian.

## 5. Giới hạn môi trường không phải luật hòa

GameState không có max_cycles và is_terminal chỉ xét phá hủy. UI chơi bình thường
không tự kết thúc sau 300 cycle. Người dùng có thể dừng hoặc thoát.

Tournament dùng --max-cycles để tránh thí nghiệm chạy vô hạn. play_match cũng có
max_plies (mặc định 400) và max_cycles tùy chọn; đây là giới hạn của bộ chạy, không
được gửi vào trạng thái search. Tournament dùng max_plies=None và max_cycles đã chọn.
Trận hết ngân sách mà chưa có phá hủy được ghi status=stopped, winner=unfinished,
reason=experiment_cycle_limit, không tính vào hòa hoặc thắng/thua. Nếu phá hủy ở
cycle cuối thì ghi kết quả thật. Hòa chỉ dành cho phá hủy hai bên cùng lúc.

## 6. Thí nghiệm công bằng

Cùng 5 map DEFAULT, OPEN, WALLS, DEFENSE, BULLET, cùng vị trí/HP và luật. Snapshot
đo cả hai bên, depth 2/4, mỗi cấu hình lặp 3 lần; thứ tự mode xáo bằng seed 42.
Mỗi phép đo tạo engine/evaluator mới: không dùng lại cache giữa các lần đo.

Cả Minimax và Alpha-Beta không có TT. PV tắt hoàn toàn bằng track_pv=False: không
lưu best-move hay tính khóa PV ở các nút, không dựng chuỗi dự đoán. Cùng cách sắp
xếp con tại gốc cho hai thuật toán. Chi phí này có trong time_ms và được tách rõ:

- order_evals: số lần gọi evaluator để sắp xếp gốc.
- leaf_evals: số lần đánh giá lá/terminal trong cây.
- total_evals = order_evals + leaf_evals.
- nodes: số lần vào nút tìm kiếm, gồm gốc; generated gồm cả con tạo khi sắp xếp.
- Thời gian/nút khi có deadline tính cả vòng bị ngắt; bảng lựa chọn thuộc vòng hoàn tất cuối.

Với terminal-only, sắp xếp thường không giúp phân biệt vì điểm bằng 0; vẫn áp dụng
cùng quy tắc và ghi riêng chi phí. Không so raw score giữa hai evaluator như cùng
thang chất lượng. Thí nghiệm tournament đổi bên, cùng depth 3, dừng sau 60 cycle
ở môi trường; PV cũng tắt. Thời gian trong trận phụ thuộc các trạng thái đã đi qua
và cache trong trận, nên dùng snapshot để so chi phí trên cùng trạng thái.

Dữ liệu/môi trường/lệnh: [experiments/README.md](experiments/README.md).
Máy đo Python 3.12.14/Linux x86_64, chưa phải macOS 13.7.8 Intel i5 của đề.

### Kết quả đã đo

240 lượt snapshot hoàn thành đúng độ sâu, 120 cặp Minimax/Alpha-Beta cùng evaluator
khớp giá trị. File CSV ghi riêng số lần đánh giá gốc và đánh giá lá.

60 trận đối đầu có 8 trận bị dừng vì hết ngân sách, không gán hòa; 8 trận hòa thật
do phá hủy đồng thời. Không có lỗi agent. Bảng tổng hợp theo từng mode:

| Mode | Trận | Thắng | Thua | Hòa thật | Chưa kết thúc | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 30 | 3 | 19 | 0 | 8 | 1.073 | 55.9 |
| heuristic_alphabeta | 30 | 19 | 3 | 8 | 0 | 4.94 | 59.21 |
| heuristic_minimax | 30 | 19 | 3 | 8 | 0 | 12.666 | 231.63 |
| minimax | 30 | 3 | 19 | 0 | 8 | 3.383 | 240.98 |

## 7. Kiểm chứng và giới hạn

22 kiểm thử có thể chạy bằng `python -m unittest discover -s tests -v`, gồm:

- Cây tính tay max(min(3,5),min(2,9))=3, oracle vét cạn độc lập trên 40 map/hai bên;
  so điểm, nước tối ưu, cận và PV của cả hai cặp Minimax/Alpha-Beta.
- Tắt PV không đổi điểm/nước và không tạo khóa PV; engine/evaluator mới mỗi lần đo;
  thống kê đủ order_evals/leaf_evals; đúng bốn mode và đúng evaluator.
- Luật di chuyển, HP, va chạm đạn từng ô, đạn gặp nhau, tank đi vào đạn, sát thương
  phe mình và phá hủy đồng thời. Bản terminal-only né khi cây nhìn thấy thua.
- Số cycle lớn không tạo terminal; cap của môi trường không tạo hòa; phá hủy cuối
  cycle được ưu tiên; thống kê unfinished riêng; UI mặc định không có cap.

Kiểm tra phát triển bổ sung xác nhận nhập AI ngoài, 35 map, nội suy không sửa trạng
thái, Pygame một người/bốn NPC và hai AI, pause/step/Tab, tài nguyên và âm thanh.

Tìm kiếm hữu hạn không bảo đảm tối ưu cả trận. Hình ảnh tank đứng bắn không tự
chứng minh search sai hoặc đúng; dùng oracle/cây tính tay để kiểm chứng cơ chế.
Một tập map xác định không đủ khẳng định heuristic luôn thắng. Phần một người/bốn
NPC dùng bản chiếu hai xe và không thuộc mô hình zero-sum hai AI của phép đo trên.
