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

## 2. Thiết kế: tách cơ chế tìm kiếm và hàm đánh giá

Minimax và Alpha-Beta quyết định bằng cây MAX/MIN. Để hoạt động khi giới hạn độ sâu,
chúng cần một quy tắc chấm lá chưa kết thúc. Chương trình cung cấp bốn cấu hình chính
với hai mức đánh giá, cùng hai đối chứng terminal-only có thể chọn ngay trên UI/CLI.

| Mode | Đánh giá lá chưa kết thúc | Cắt tỉa | Vai trò |
| --- | --- | --- | --- |
| minimax | HP + Manhattan tới căn cứ địch | Không | Minimax BASIC |
| alphabeta | Cùng BASIC | Có | Alpha-Beta BASIC |
| heuristic_minimax | HP + đường tới vị trí bắn + ngắm + đạn | Không | Nâng cao |
| heuristic_alphabeta | Cùng nâng cao | Có | Nâng cao |
| terminal_minimax | 0 trung tính | Không | Đối chứng không heuristic |
| terminal_alphabeta | 0 trung tính | Có | Đối chứng không heuristic |

**BASIC cũng là heuristic đơn giản.** Không coi BASIC là “không heuristic” và không
khẳng định đề buộc mọi lá chưa kết thúc nhận 0. Nếu cần trình bày phép so sánh nghiêm
ngặt không/có heuristic, dùng hai terminal_* và hai heuristic_*. Tên mode vẫn được
giữ trong từng CSV để không ghép nhầm dữ liệu của các evaluator.

Gọi M = 100 × chênh lệch HP căn cứ + 80 × chênh lệch HP xe, theo góc nhìn MAX:

- BASIC = M + 10 × (Manhattan của địch tới căn cứ mình − của mình tới căn cứ địch).
  Có tín hiệu cho tiến triển và tổn thất HP, nhưng không giải bài toán đi vòng thép.
- Nâng cao = M + 10 × lợi thế chi phí tới vị trí bắn + 30 × lợi thế ngắm
  + 60 × lợi thế đạn. Không cộng thêm Manhattan của BASIC.
- Terminal-only chỉ dùng utility thắng/thua/hòa +10000/−10000/0. Ở ngưỡng cắt chưa
  kết thúc trả 0 trung tính; điểm này không chứng minh kết quả cuối cùng là hòa.

BASIC và nâng cao giới hạn điểm chưa kết thúc trong [-9900,9900]. Cả sáu cấu hình
giữ cùng luật, utility terminal và phần thưởng độ sâu còn lại để thắng sớm/thua muộn.
Tìm kiếm hữu hạn không đồng nghĩa Minimax vét cạn toàn bộ ván đấu. Khi các nhánh cùng
điểm, dùng thứ tự cố định; không có kịch bản/ngẫu nhiên ép tank phải di chuyển.

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

## 5. Kiểm chứng thiết kế

39 kiểm thử phát triển chạy ngoài gói nộp gọn: 24 kiểm thử nền, 9 kiểm thử evaluator
và 6 kiểm thử tích hợp thiết kế. Oracle vét cạn độc lập trên 40 map/hai bên được mở
rộng cho cả ba cặp evaluator. Bao gồm cây tính tay max(min(3,5),min(2,9))=3; cận
Alpha-Beta, PV, TT, deadline, khóa thời gian; va chạm/HP/hòa, nhập AI ngoài, chuyển
35 map và không sửa trạng thái đầu vào. Cặp Minimax/Alpha-Beta phải khớp giá trị,
không nhất thiết cùng nước khi đồng điểm.

Tình huống hồi quy ở depth 4: xe 6 HP gặp đạn sắp trúng, BASIC chọn né để giữ đủ HP,
terminal-only chọn FIRE vì mất 1 HP vẫn chưa làm đổi utility 0. Khi xe còn 1 HP,
terminal-only cũng chọn né vì đã nhìn thấy thua. Kiểm tra riêng tiến tới mục tiêu,
thắng ngay, tự bắn căn cứ chí mạng, hướng/gạch/thép, dự báo va chạm đạn, cache,
zero-sum và terminal trội hơn ước lượng.

Pygame kiểm tra cả sáu lựa chọn, tạo agent/áp dụng nước đi, gợi ý loại evaluator và
bảng Tab; mặc định BASIC Alpha-Beta đấu nâng cao Alpha-Beta. Hai CONTROL dùng đúng
TerminalEvaluator như API truyền evaluator trực tiếp. Bộ kiểm tra nền xác nhận một
người/bốn NPC, hai AI, dừng/đi từng lượt và map gốc. Bố cục và hoạt ảnh không đổi.

## 6. Thực nghiệm cơ bản/nâng cao và đối chứng terminal-only

Dữ liệu/môi trường/lệnh tái hiện: [experiments/README.md](experiments/README.md).
Profile `basic_advanced_terminal_controls_v2`, Python 3.12.14/Linux x86_64, chưa phải
máy macOS Intel i5 của đề. Số liệu được đo lại cho thiết kế hiện tại. Mọi phép đo
không deadline/phạt lặp, trừ khi có ghi khác. Không có agent fault trong các trận.

### Snapshot cùng độ sâu

- `search_fixed_depth.csv`: 240 lượt = 5 map × 2 bên × depth 2/4 × 3 lần × 4 mode
  chính. Summary 80 nhóm, kiểm chứng 120 cặp Minimax/Alpha-Beta cùng evaluator.
- `search_terminal_control.csv`: 120 lượt với cùng map/bên/depth/lần lặp, chỉ hai
  terminal_*. Summary 40 nhóm, kiểm chứng 60 cặp terminal Minimax/Alpha-Beta.

Map DEFAULT, OPEN, WALLS, DEFENSE, BULLET; mọi lượt đạt độ sâu yêu cầu. Cột evaluator
phân biệt basic/heuristic/terminal_only. File summary có median/mean, nút/lá, đánh
giá và cắt tỉa. Lặp snapshot phục vụ đo thời gian, không tạo các trận độc lập.

### Đối đầu bốn cấu hình chính, đổi bên

`tournament_fixed_depth.csv`: 60 trận = 5 map × 6 cặp × 2 bên, depth 3, tối đa
60 vòng. Cơ bản so với nâng cao:

| Mode | Trận | Thắng | Thua | Hòa | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 30 | 7 | 23 | 0 | 1.011 | 61.95 |
| heuristic_alphabeta | 30 | 19 | 3 | 8 | 2.953 | 56.86 |
| heuristic_minimax | 30 | 19 | 3 | 8 | 6.907 | 230.3 |
| minimax | 30 | 7 | 23 | 0 | 2.438 | 222.02 |

### Đối chứng không/có heuristic đúng nghĩa, đổi bên

`tournament_terminal_control.csv`: 60 trận, cùng map/bên/depth/giới hạn, chỉ dùng
terminal_minimax, terminal_alphabeta, heuristic_minimax, heuristic_alphabeta.
Đây là bộ kết quả dành cho phần so sánh terminal-only với heuristic:

| Mode | Trận | Thắng | Thua | Hòa | Mean ms/nước | Mean nút/nước |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristic_alphabeta | 30 | 19 | 3 | 8 | 3.714 | 59.06 |
| heuristic_minimax | 30 | 19 | 3 | 8 | 8.532 | 231.63 |
| terminal_alphabeta | 30 | 3 | 19 | 8 | 0.909 | 55.22 |
| terminal_minimax | 30 | 3 | 19 | 8 | 2.409 | 238.68 |

Thời gian trong trận phụ thuộc trạng thái đã đi qua và cache; dùng snapshot để so
chi phí cùng trạng thái. Alpha-Beta giữ giá trị Minimax cùng evaluator/depth, giảm
nhánh chứ không tự tạo hàm đánh giá thông minh hơn. Heuristic tốn thêm chi phí;
không khẳng định luôn nhanh hơn hoặc luôn thắng. Chưa công bố số liệu cùng ngân
sách thời gian; `--time-limit-ms` vẫn hỗ trợ giao thức đó.

### Cùng đối thủ GreedyAgent

`behavior_fixed_opponent.csv`: 36 trận = 3 map (DEFAULT, WALLS, ORIGINAL_20) × 6
cấu hình × 2 bên; depth 3, tối đa 60 vòng. Movements chỉ đếm đổi ô, rotations là
xoay tại chỗ, fires/stays là bắn/bỏ lượt; các trận có thể dài khác nhau.

| Mode | Trận | Thắng | Thua | Hòa | Số lần đổi ô | Số lần bắn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alphabeta | 6 | 4 | 2 | 0 | 50 | 81 |
| heuristic_alphabeta | 6 | 5 | 1 | 0 | 47 | 63 |
| heuristic_minimax | 6 | 5 | 1 | 0 | 47 | 63 |
| minimax | 6 | 4 | 2 | 0 | 50 | 81 |
| terminal_alphabeta | 6 | 0 | 2 | 4 | 0 | 302 |
| terminal_minimax | 6 | 0 | 2 | 4 | 0 | 302 |

BASIC đã phân biệt được tiến triển và mất HP trong các tình huống đã thử; terminal-only
có thể đứng bắn vì đồng điểm. Việc đổi ô nhiều hơn không tự chứng minh chơi tốt hơn.
Một tập tình huống xác định với một đối thủ không cho tỷ lệ thắng tổng quát. Kiểm
chứng cơ chế tìm kiếm dựa vào oracle/cây tính tay, không dựa riêng vào hình ảnh hay
thắng/thua. Mọi cấu hình đều chỉ nhìn trước hữu hạn, không bảo đảm tối ưu cả trận.

## 7. Nguồn bản đồ

- DEFAULT, OPEN, WALLS, DEFENSE, BULLET: các tình huống cơ sở để kiểm tra tìm kiếm,
  vật cản, phòng thủ và đạn.
- ORIGINAL_01 … ORIGINAL_35: 26×26 nguồn gộp thành 13×13; nước thành thép, cỏ/băng
  thành trống, ưu tiên ô cản khi nhóm hỗn hợp. Thêm căn cứ trên cho trận hai bên.
  [Quy tắc và định dạng](levels_ai/README.md).

Phần một người đấu bốn NPC là mở rộng: mỗi NPC dự đoán qua bản chiếu hai xe,
coi đồng đội như vật cản. Các phân tích zero-sum và số liệu ở đây tập trung hai AI.
