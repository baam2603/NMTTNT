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

## 2. Bốn cấu hình: không heuristic và có heuristic

| Cấu hình | Đánh giá trạng thái chưa kết thúc tại ngưỡng độ sâu | Cắt tỉa |
| --- | --- | --- |
| Minimax | 0, không dùng heuristic | Không |
| Alpha-Beta | 0, cùng utility với Minimax | Có |
| Heuristic Minimax | HP + đường tới vị trí bắn + hướng ngắm + đạn | Không |
| Heuristic Alpha-Beta | Cùng heuristic | Có |

Hai cấu hình **không heuristic** mặc định dùng `TerminalEvaluator`: thắng/thua/hòa
nhận +10000/−10000/0; trạng thái chưa kết thúc tại ngưỡng cắt nhận **0 trung tính**.
Không dùng HP, Manhattan, đường đi, ngắm hay nguy cơ đạn để chấm các trạng thái đó.
`BasicEvaluator` đã được gỡ để bản nộp chỉ còn phân biệt không/có heuristic.

Đây là baseline **giới hạn độ sâu**, không phải Minimax vét cạn tới terminal toàn
bộ ván đấu. Điểm trung tính 0 không chứng minh trạng thái sẽ hòa. Khi chưa nhìn
thấy thắng/thua trong cây, mọi nước có thể đồng điểm; thứ tự cố định có FIRE đầu
nên tank có thể đứng bắn. Không dùng điều khiển ngẫu nhiên hoặc kịch bản di chuyển
để che giới hạn này. Terminal ở trong cây vẫn được nhận biết và ưu tiên thắng
sớm/thua muộn bằng phần thưởng độ sâu còn lại; cả bốn cấu hình áp dụng giống nhau.

Hai cấu hình **có heuristic** dùng `HeuristicEvaluator`. Với M = 100 × chênh lệch HP
căn cứ + 80 × chênh lệch HP xe, tính theo góc nhìn MAX, điểm chưa kết thúc là:

`H = M + 10 × lợi thế chi phí tới vị trí bắn + 30 × lợi thế ngắm + 60 × lợi thế đạn`.

Dijkstra ngược chạy trên `(ô, hướng)`, bắt đầu từ các vị trí có thể bắn về căn cứ
địch. Chi phí ước lượng gồm một lần FIRE, thời gian bay, HP gạch chắn; đi một ô tốn
một hành động và tự đổi hướng, chỉ xoay tại chỗ khi ô phía trước bị chặn. Khi phải
vào ô gạch, ước lượng cộng HP gạch, lượt xoay nếu cần và một lượt di chuyển. Thép và
cả hai căn cứ không được đi xuyên; đường ngắm không xuyên thép/căn cứ phe mình.
Đây là mô hình tĩnh thư giãn: bỏ qua vị trí xe đang di chuyển, thời gian đợi đạn phá
gạch và thay đổi địa hình khi lập đường. Va chạm chiến thuật vẫn do engine thật
trong cây tìm kiếm quyết định. Do đó chi phí này không phải số lượt thắng chính xác.

Điểm ngắm dò vật đầu tiên, phân biệt địch/phe mình và giảm giá trị khi bị gạch chắn.
Dự báo đạn dùng engine va chạm trên **bản sao** tối đa 3 vòng, giả định xe giữ vị
trí và không sinh thêm đạn. Xét gạch, đạn gặp/đổi ô, sát thương phe mình, HP thấp và
chiết khấu theo thời gian; không coi đây là sát thương chắc chắn vì đối thủ có thể
né/bắn chặn. Điểm heuristic chưa kết thúc giới hạn [-9900,9900] để utility terminal trội hơn;
đổi góc nhìn thì đổi dấu, terminal thắng/thua/hòa vẫn ±10000/0. Phạt lặp mặc định bằng 0.

## 3. Tối ưu và thống kê

- Alpha-Beta loại các nhánh không thể cải thiện lựa chọn; bảng chuyển vị lưu
  exact/lower/upper bound và độ sâu. Khóa tìm kiếm gồm số vòng còn lại; khóa lặp
  chỉ xét vị trí vật lý để phát hiện quay lại vị trí cũ.
- Sắp xếp hành động gốc, ưu tiên nước tốt từ lần tìm sâu trước.
- Có deadline: tìm sâu dần, trả kết quả hoàn tất cuối và luôn có nước hợp lệ dự phòng.
  Deadline kiểm tra trước các nút/evaluator, là ngân sách mềm, không cưỡng bức ngắt
  một evaluator hay AI ngoài đang chạy. Chế độ đo có ngân sách ghi cả lần vượt.
- SearchAgent tái sử dụng evaluator/cache Dijkstra giữa các lượt; TT được xóa mỗi lượt.
  Cache đường đi giới hạn 512 mục, khóa gồm địa hình, HP gạch và vị trí căn cứ,
  không phụ thuộc vị trí xe; khi gạch đổi HP phải tính lại.
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

## 5. Kiểm chứng

33 kiểm thử phát triển chạy ngoài gói nộp gọn: 24 kiểm thử nền và 9 kiểm thử hồi
quy được cập nhật theo cấu hình không/có heuristic. Bao gồm cây tính tay
max(min(3,5),min(2,9))=3; vét cạn độc lập trên 40 map/hai bên với đúng từng evaluator;
cận Alpha-Beta, PV, TT, deadline, khóa thời gian; va chạm/HP/hòa, nhập AI ngoài,
chuyển 35 map và không sửa trạng thái đầu vào.

Hồi quy xác nhận Minimax/Alpha-Beta mặc định dùng terminal-only: thay HP hoặc địa
hình trong trạng thái chưa kết thúc vẫn cho điểm 0; hai bản còn lại dùng heuristic.
Cả bốn nhận biết thắng ngay, tránh tự bắn căn cứ chí mạng và né đạn gây thua nếu
cây đủ sâu nhìn thấy kết quả. Kiểm tra thêm hướng/gạch/thép trong đường tới vị trí
bắn, dự báo va chạm đạn, cache, zero-sum và utility terminal trội hơn heuristic.

Pygame đã kiểm tra menu, một người/bốn NPC, hai AI, dừng/đi từng lượt, Tab và map
gốc. Bảng Tab ghi rõ NO HEURISTIC hoặc HEURISTIC; không đổi luật game/hoạt ảnh.
240 lượt benchmark khớp giá trị ở mọi cặp Minimax/Alpha-Beta cùng evaluator.

## 6. Kết quả đo lại cho cấu hình không/có heuristic

Dữ liệu, môi trường và lệnh tái hiện: [experiments/README.md](experiments/README.md).
Các CSV hiện tại được **đo lại** cho terminal-only và heuristic, không dùng kết quả
của bản BASIC để mô tả bản này. Python 3.12.14/Linux x86_64, chưa phải máy macOS
Intel i5 của đề; thời gian chỉ là tham khảo trên môi trường đo.

### Tìm kiếm cùng độ sâu

`search_fixed_depth.csv`: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần × 4 cấu hình.
DEFAULT, OPEN, WALLS, DEFENSE và BULLET; mọi lượt đạt độ sâu yêu cầu. Cặp dùng cùng
evaluator khớp giá trị. CSV có `evaluator=terminal_only/heuristic`, thời gian, số nút,
lá, đánh giá, cắt tỉa, TT và độ sâu; file summary có median/mean. Lặp snapshot phục
vụ đo thời gian, không tạo ra các trận độc lập. Heuristic tốn thêm chi phí đánh giá.

### Đối đầu bốn cấu hình, đổi bên

60 trận = 5 map × 6 cặp × 2 bên, depth 3, tối đa 60 vòng, không deadline/phạt lặp.
Bảng được lấy từ `tournament_fixed_depth_summary.csv`:

| Cấu hình | Trận | Thắng | Thua | Hòa | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 30 | 3 | 19 | 8 | 0.994 | 55.22 |
| heuristic_alphabeta | 30 | 19 | 3 | 8 | 3.933 | 59.06 |
| heuristic_minimax | 30 | 19 | 3 | 8 | 9.428 | 231.63 |
| minimax | 30 | 3 | 19 | 8 | 2.65 | 238.68 |

Thời gian trong trận phụ thuộc trạng thái mỗi agent đi qua và cache giữa các lượt;
dùng benchmark snapshot để so chi phí trên cùng trạng thái. Không có agent fault.
Các tỷ lệ chỉ áp dụng các map, vị trí, depth và giới hạn đã ghi. Alpha-Beta cắt tỉa
không làm utility tốt hơn Minimax cùng evaluator/độ sâu; lợi ích là giảm tìm kiếm.
Chưa công bố số liệu cùng ngân sách thời gian; `--time-limit-ms` hỗ trợ giao thức đó.

### Cùng một đối thủ tham chiếu

`behavior_fixed_opponent.csv`: 24 trận = 3 map (DEFAULT, WALLS, ORIGINAL_20) ×
4 cấu hình × 2 bên, cùng GreedyAgent, depth 3, tối đa 60 vòng, không deadline/phạt
lặp. Cột movements chỉ đếm đổi ô, rotations là xoay tại chỗ, fires/stays là bắn/bỏ lượt.

| Cấu hình | Trận | Thắng | Thua | Hòa | Số lần đổi ô | Số lần bắn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 6 | 0 | 2 | 4 | 0 | 302 |
| heuristic_alphabeta | 6 | 5 | 1 | 0 | 47 | 63 |
| heuristic_minimax | 6 | 5 | 1 | 0 | 47 | 63 |
| minimax | 6 | 0 | 2 | 4 | 0 | 302 |

Tank terminal-only có thể không di chuyển khi chưa có nhánh thắng/thua phân biệt
được trong độ sâu tìm kiếm. Đó là giới hạn của thông tin đánh giá ở baseline này;
không kết luận sai Minimax chỉ từ hình ảnh đứng bắn. Kiểm chứng thuật toán dựa vào
vét cạn độc lập/cây tính tay, không dựa riêng vào tỷ lệ thắng. Các trận xác định
với một đối thủ tham chiếu không đủ để khẳng định hiệu quả trên mọi map.

## 7. Nguồn bản đồ

- DEFAULT, OPEN, WALLS, DEFENSE, BULLET: các tình huống cơ sở để kiểm tra tìm kiếm,
  vật cản, phòng thủ và đạn.
- ORIGINAL_01 … ORIGINAL_35: 26×26 nguồn gộp thành 13×13; nước thành thép, cỏ/băng
  thành trống, ưu tiên ô cản khi nhóm hỗn hợp. Thêm căn cứ trên cho trận hai bên.
  [Quy tắc và định dạng](levels_ai/README.md).

Phần một người đấu bốn NPC là mở rộng: mỗi NPC dự đoán qua bản chiếu hai xe,
coi đồng đội như vật cản. Các phân tích zero-sum và số liệu ở đây tập trung hai AI.
