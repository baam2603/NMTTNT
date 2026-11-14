# Tank Battle — Mô hình và kết quả tìm kiếm đối kháng

## 1. Mô hình zero-sum cho hai AI

- Người chơi P0/P1 biết toàn bộ trạng thái; luật không có yếu tố ngẫu nhiên.
- Trạng thái: địa hình/gạch và HP, thép, hai xe (ô, hướng, HP), hai căn cứ,
  đạn (ô, hướng, chủ sở hữu), bên tới lượt, vòng hiện tại và giới hạn vòng.
- Tập hành động hợp lệ lấy từ MOVE_UP/DOWN/LEFT/RIGHT, FIRE, STAY.
- MOVE đổi hướng và đi một ô nếu trống; khi bị chặn có thể chỉ xoay.
- Sau lượt P1, đạn đi tối đa 3 ô, kiểm tra từng ô, dừng ngay khi trúng vật cản.
  Xe/căn cứ/gạch ban đầu có 6/9/3 HP; mỗi hit gây 1 sát thương. Có sát thương phe mình.
- Thép chặn đạn và không phá được. Hai đạn gặp nhau/đổi ô sẽ triệt tiêu theo luật engine.
- Mất xe hoặc căn cứ thì thua; hai bên bị hạ đồng thời là hòa. Hết 300 vòng là hòa
  nếu không có bên bị hạ; phá hủy ở vòng cuối được ưu tiên trước hòa do hết vòng.
- Utility theo góc nhìn người tìm kiếm: thắng +10000, thua -10000, hòa 0.
  Đổi người đánh giá thì đổi dấu. Độ sâu còn lại ưu tiên thắng sớm/thua muộn.

Minimax lấy MAX ở lượt của mình, MIN ở lượt đối thủ. Một depth là một hành động,
không phải một vòng gồm hai lượt. Tìm kiếm sâu hữu hạn không bảo đảm tối ưu cả trận.

## 2. Bốn cấu hình

| Cấu hình | Đánh giá trạng thái chưa kết thúc ở độ sâu giới hạn | Cắt tỉa |
| --- | --- | --- |
| Minimax | 0 | Không |
| Alpha-Beta | 0 | Có |
| Heuristic Minimax | HP + đường đi + hướng bắn + đạn | Không |
| Heuristic Alpha-Beta | Cùng heuristic | Có |

Heuristic dùng chênh lệch hai bên: HP căn cứ ×100, HP xe ×80, lợi thế đường đi ×10,
lợi thế hướng bắn ×30, lợi thế đạn ×60. Dijkstra ước lượng đường đi có chi phí
phá gạch. Hướng bắn dò vật đầu tiên; nguy cơ/khả năng gây sát thương của đạn là
ước lượng. Điểm chưa kết thúc được giới hạn [-9900,9900] để utility kết thúc luôn
chiếm ưu tiên. Hai góc nhìn có điểm đối dấu. Phạt lặp mặc định bằng 0 cho mọi cấu hình.

Các trạng thái chưa kết thúc của bản plain cùng 0; FIRE thường được giữ khi phá hòa.
Xe đứng bắn vì đồng điểm vẫn có thể là kết quả đúng của tìm kiếm, dù chất lượng
chơi yếu. Không bổ sung điều khiển di chuyển giả vào hai baseline này.

## 3. Tối ưu và thống kê

- Alpha-Beta loại các nhánh không thể cải thiện lựa chọn; bảng chuyển vị lưu
  exact/lower/upper bound và độ sâu. Khóa tìm kiếm gồm số vòng còn lại; khóa lặp
  chỉ xét vị trí vật lý để phát hiện quay lại vị trí cũ.
- Sắp xếp hành động gốc, ưu tiên nước tốt từ lần tìm sâu trước.
- Có deadline: tìm sâu dần, trả kết quả hoàn tất cuối và luôn có nước hợp lệ dự phòng.
  Deadline kiểm tra trước các nút/evaluator, là ngân sách mềm, không cưỡng bức ngắt
  một evaluator hay AI ngoài đang chạy. Chế độ đo có ngân sách ghi cả lần vượt.
- SearchAgent tái sử dụng evaluator/cache Dijkstra giữa các lượt; TT được xóa mỗi lượt.
- Thử hành động trên bản sao, không sửa trạng thái thật.
- Đếm đủ `evals = order_evals + leaf_evals`. Tổng thời gian/nút tính cả vòng tìm kiếm
  bị ngắt; các dòng lựa chọn trên UI thuộc lần hoàn tất cuối.

Cùng trạng thái/evaluator/độ sâu: Alpha-Beta phải khớp giá trị Minimax; các nước
đồng điểm có thể được chọn khác nhau. Không so raw score giữa hai evaluator như
cùng một thang đo chất lượng.

## 4. UI và nhập thuật toán nhóm khác

Pygame vẽ giao diện classic. Tab hiển thị hành động, điểm/cận, số nút, cắt tỉa,
TT và chuỗi nước dự đoán. `=` là giá trị chính xác, `<=` là cận trên từ cắt tỉa.
Chuỗi dự đoán không ép đối thủ thực hiện: mỗi bên tìm kiếm lại khi tới lượt.
Hoạt ảnh đạn chạy trên các bản sao riêng, không chuyển trạng thái phát lại cho agent.

Đặt file .py trong task2/ hoặc agents/, nhấn F5. Có thể cung cấp
`create_agent(player_id)` trả đối tượng có `act`, hoặc hàm `choose_action(state)` /
`act(state)`. Nếu hỗ trợ, loader chuyển tiếp `time_limit_ms`, `history` và gọi reset.
Nước trả về có thể là Action, số enum hoặc tên; engine kiểm tra lại tính hợp lệ.
File `task2/external_greedy.py` là ví dụ thử tích hợp. AI ngoài tự tuân thủ ngân sách.

## 5. Kiểm chứng trước đóng gói

Bản mã nguồn sau dọn được chạy lại bộ kiểm thử phát triển đã lưu ngoài gói nộp:
24 kiểm thử, gồm cây tính tay max(min(3,5),min(2,9))=3; vét cạn độc lập;
đối chiếu Minimax/Alpha-Beta; kiểm tra cận, PV, deadline, khóa thời gian, va chạm,
HP và hòa; nhập AI ngoài; chuyển 35 map; nội suy và không sửa trạng thái đầu vào.
Kiểm tra Pygame cũng xác nhận menu, chế độ một người/hai AI, dừng/đi từng lượt,
phân tích và chọn map gốc. File test phát triển không nằm trong bản nộp gọn.

## 6. Kết quả tham khảo

Dữ liệu, môi trường và lệnh tái hiện: [experiments/README.md](experiments/README.md).
Đã bỏ số liệu của các map được gỡ và tổng hợp lại; giữ nguyên giá trị đo còn lại.
Môi trường tham khảo là Python 3.12.14/Linux x86_64, chưa phải máy macOS Intel i5 của đề.

### Tìm kiếm cùng độ sâu

`search_fixed_depth.csv`: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần đo × 4 cấu hình.
Các map là DEFAULT, OPEN, WALLS, DEFENSE và BULLET. Mọi lượt hoàn thành độ sâu yêu
cầu; cặp cùng evaluator khớp giá trị. `search_fixed_depth_summary.csv` chứa thời
gian median/mean, số nút, đánh giá và cắt tỉa. Lặp cùng trạng thái phục vụ đo thời
gian, không phải các trận độc lập.

### Đối đầu cùng độ sâu, đổi bên

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


## 7. Nguồn bản đồ

- DEFAULT, OPEN, WALLS, DEFENSE, BULLET: các tình huống cơ sở để kiểm tra tìm kiếm,
  vật cản, phòng thủ và đạn.
- ORIGINAL_01 … ORIGINAL_35: 26×26 nguồn gộp thành 13×13; nước thành thép, cỏ/băng
  thành trống, ưu tiên ô cản khi nhóm hỗn hợp. Thêm căn cứ trên cho trận hai bên.
  [Quy tắc và định dạng](levels_ai/README.md).

Phần một người đấu bốn NPC là mở rộng: mỗi NPC dự đoán qua bản chiếu hai xe,
coi đồng đội như vật cản. Các phân tích zero-sum và số liệu ở đây tập trung hai AI.
