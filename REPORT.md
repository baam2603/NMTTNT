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

## 2. Bốn cấu hình và hàm đánh giá đã cải thiện

| Cấu hình | Đánh giá trạng thái chưa kết thúc ở độ sâu giới hạn | Cắt tỉa |
| --- | --- | --- |
| Minimax (BASIC) | HP + khoảng cách Manhattan tới căn cứ địch | Không |
| Alpha-Beta (BASIC) | Cùng đánh giá cơ bản | Có |
| Heuristic Minimax | HP + đường tới vị trí bắn + hướng ngắm + đạn | Không |
| Heuristic Alpha-Beta | Cùng đánh giá nâng cao | Có |

**BASIC cũng là heuristic theo định nghĩa.** Tên BASIC phân biệt đánh giá rẻ với
đánh giá nâng cao, không đồng nghĩa “không heuristic”. `TerminalEvaluator` được giữ
làm đối chứng đúng nghĩa: chỉ thắng/thua/hòa có utility, chưa kết thúc trả 0; truyền
qua `choose_action(..., evaluator=TerminalEvaluator())` hoặc `SearchAgent`.
Không thêm hành động di chuyển ngẫu nhiên hay ưu tiên giả để che việc đồng điểm.

Gọi M là 100 × chênh lệch HP căn cứ + 80 × chênh lệch HP xe, theo góc nhìn MAX:

- **BASIC:** M + 10 × (khoảng cách Manhattan của địch tới căn cứ mình − của mình
  tới căn cứ địch). Nhờ đó hành động tiến triển có thể tốt hơn đứng bắn khi HP bằng
  nhau. Khoảng cách này không biết đi vòng thép và không dự báo đạn ngoài search.
- **Nâng cao:** M + 10 × lợi thế chi phí tới vị trí bắn + 30 × lợi thế ngắm bắn
  + 60 × lợi thế sát thương đạn dự báo. Không cộng thêm Manhattan của BASIC.

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
né/bắn chặn. Cả hai mức đánh giá giới hạn [-9900,9900], đổi góc nhìn thì đổi dấu,
terminal thắng/thua/hòa vẫn ±10000/0. Phạt lặp mặc định bằng 0.

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

33 kiểm thử phát triển được chạy ngoài gói nộp gọn: 24 kiểm thử nền được cập nhật
oracle theo evaluator BASIC mới và 9 kiểm thử hồi quy cho cải tiến. Bao gồm cây tính
tay max(min(3,5),min(2,9))=3; vét cạn độc lập trên 40 map/hai bên; cận Alpha-Beta,
PV, TT, deadline, khóa thời gian; va chạm/HP/hòa, nhập AI ngoài, chuyển 35 map và
không sửa trạng thái đầu vào. Hồi quy mới kiểm tra tiến tới mục tiêu thay vì đồng
điểm FIRE, chọn thắng ngay, tránh tự bắn căn cứ và né đạn chí mạng; hướng/gạch/thép
trong chi phí tới vị trí bắn; dự báo đạn, cache và utility terminal trội hơn ước lượng.

Kiểm tra Pygame xác nhận menu, một người/bốn NPC, trận hai AI, dừng/đi từng lượt,
Tab phân tích và map gốc. 240 lượt benchmark cùng độ sâu cũng khớp giá trị ở mọi
cặp Minimax/Alpha-Beta dùng cùng evaluator. Trên snapshot ORIGINAL_20 ban đầu,
Alpha-Beta BASIC và nâng cao đều chọn MOVE_UP cho P0/MOVE_DOWN cho P1 ở depth 4.
Điều này không bảo đảm mọi trạng thái khác đều phải di chuyển.

## 6. Kết quả đo lại sau thay đổi

Dữ liệu, môi trường và lệnh tái hiện: [experiments/README.md](experiments/README.md).
Bốn CSV fixed-depth đã được **đo lại cho evaluator mới**, không dùng số liệu cũ để
mô tả bản mới. Môi trường Python 3.12.14/Linux x86_64, chưa phải macOS Intel i5 của đề.

### Tìm kiếm cùng độ sâu

`search_fixed_depth.csv`: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần × 4 cấu hình.
DEFAULT, OPEN, WALLS, DEFENSE và BULLET; mọi lượt đạt độ sâu yêu cầu. Cặp cùng
evaluator khớp giá trị; CSV ghi tên evaluator và tổng hợp median/mean, nút, đánh giá,
cắt tỉa. Đây là phép đo snapshot/cache mới, không phải các trận độc lập. Đánh giá
nâng cao có thêm chi phí, không khẳng định nhanh hơn BASIC hoặc bản cũ.

### Đối đầu bốn cấu hình hiện tại, đổi bên

60 trận trên 5 map; depth 3, giới hạn 60 vòng, không deadline, phạt lặp 0; không
agent fault. Mỗi cấu hình đấu nhiều đối thủ. Bảng dưới chỉ áp dụng bộ tình huống này.

| Cấu hình | Trận | Thắng | Thua | Hòa | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 30 | 7 | 23 | 0 | 1.025 | 61.95 |
| heuristic_alphabeta | 30 | 19 | 3 | 8 | 2.877 | 56.86 |
| heuristic_minimax | 30 | 19 | 3 | 8 | 7.128 | 230.30 |
| minimax | 30 | 7 | 23 | 0 | 2.477 | 222.02 |

Thời gian trong trận còn phụ thuộc trạng thái đã đi qua và cache được tái sử dụng;
dùng benchmark snapshot để so chi phí tìm kiếm trên cùng trạng thái. Chưa xuất bản
số liệu đối đầu cùng ngân sách thời gian; `--time-limit-ms` vẫn hỗ trợ phép đo này.

### Trước/sau với cùng một đối thủ cố định

`behavior_before_after.csv`: 48 trận = 2 phiên bản × 3 map (DEFAULT, WALLS,
ORIGINAL_20) × 4 cấu hình × 2 bên. Cùng GreedyAgent, depth 3, tối đa 60 vòng,
không deadline/phạt lặp; GreedyAgent và engine không thay đổi giữa hai phiên bản.
Bản trước là commit `3ef0963`; bản sau là profile `after_basic_firing_route_v1`.

| Cấu hình | Trước: thắng/thua/hòa | Sau: thắng/thua/hòa | Số lần di chuyển trước → sau |
| --- | --- | --- | ---: |
| Minimax | 0/2/4 | 4/2/0 | 0 → 50 |
| Alpha-Beta | 0/2/4 | 4/2/0 | 0 → 50 |
| Heuristic Minimax | 5/1/0 | 5/1/0 | 57 → 47 |
| Heuristic Alpha-Beta | 5/1/0 | 5/1/0 | 57 → 47 |

Số di chuyển cộng trên 6 trận mỗi hàng, chỉ đếm đổi ô, không đếm xoay. Trận hai bản
có thể dài khác nhau; số di chuyển cao hơn không tự chứng minh chất lượng cao hơn.
Kết quả cho thấy BASIC giải quyết được hiện tượng đứng bắn ở bộ thử; chưa chứng
minh nâng cao tăng tỷ lệ thắng so bản nâng cao cũ. Các tình huống xác định và chỉ
một đối thủ tham chiếu không đủ để suy ra tỷ lệ thắng tổng quát hay tối ưu cả trận.

## 7. Nguồn bản đồ

- DEFAULT, OPEN, WALLS, DEFENSE, BULLET: các tình huống cơ sở để kiểm tra tìm kiếm,
  vật cản, phòng thủ và đạn.
- ORIGINAL_01 … ORIGINAL_35: 26×26 nguồn gộp thành 13×13; nước thành thép, cỏ/băng
  thành trống, ưu tiên ô cản khi nhóm hỗn hợp. Thêm căn cứ trên cho trận hai bên.
  [Quy tắc và định dạng](levels_ai/README.md).

Phần một người đấu bốn NPC là mở rộng: mỗi NPC dự đoán qua bản chiếu hai xe,
coi đồng đội như vật cản. Các phân tích zero-sum và số liệu ở đây tập trung hai AI.
