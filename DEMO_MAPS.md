# Hai map minh họa tác dụng của heuristic

Chọn **AI BATTLE → MAP → H_DETOUR hoặc H_DODGE**.
Để so sánh trên giao diện, đặt độ sâu hai bên bằng **4**, giữ nguyên thuật toán
của P1 (ví dụ ALPHA-BETA), chạy lần đầu với P0 là MINIMAX, rồi Esc về setup,
đổi riêng P0 sang HEURISTIC MINIMAX và bắt đầu lại để đặt lại trạng thái map.
Lặp lại với P0 ALPHA-BETA / HEURISTIC ALPHA-BETA.
Giảm tốc bằng phím `-` hoặc dùng P/N để xem từng lượt.
Map cũng xuất hiện ở chế độ 1 người, nhưng nên dùng AI BATTLE để đối chiếu hai evaluator.

Đối chiếu **nước đầu của P0 từ cùng trạng thái**; giữ cố định P1, độ sâu và tốc độ.
Giao diện có ngân sách 60 ms nên hãy kiểm tra DEPTH thực tế đạt được; nếu máy chậm,
giảm cả hai bên xuống độ sâu 2. Lệnh bên dưới không giới hạn thời gian và tìm đủ độ sâu.

## H_DETOUR — tìm đường vòng qua tường thép

Hai hàng tường thép đặt so le. Tường thấp mở lối bên trái, tường cao mở lối bên phải.
Xe P0 bắt đầu sát phía dưới tường thấp, hướng lên. Bắn không phá được thép.
Căn cứ đối thủ còn cách 21 bước theo ước lượng đường đi, vượt chân trời tìm kiếm 4 lượt.

Khi các lá chưa kết thúc trận, evaluator terminal-only cho điểm 0 và thuật toán
chọn FIRE theo thứ tự phá hòa hiện có. Heuristic nhận ra đi trái sẽ giảm chi phí
đường đi về căn cứ đối phương, dù phải vòng qua các hàng thép.

Với P1 cố định bỏ lượt để quan sát riêng đường đi, sau sáu lượt P0:

- MINIMAX: FIRE sáu lần, vẫn ở `(5, 4)`.
- HEURISTIC MINIMAX: trái bốn ô, lên hai ô, đến `(3, 0)` qua lối mở.

Tọa độ tính từ 0. Phép quan sát P1 bỏ lượt dùng trong lệnh so sánh; đây không phải
chế độ bổ sung trong giao diện AI đấu AI.

## H_DODGE — né đạn để giữ HP

P0 có 6 HP, đứng tại `(7, 4)`, hướng trái. Đạn của P1 tại `(5, 4)` hướng xuống.
Nếu P0 bắn theo hướng hiện tại, đạn đó không chặn được viên đạn đang tới và P0
mất 1 HP khi đạn tiến ở cuối vòng. Di chuyển sang trái giúp P0 giữ nguyên 6 HP.

Mất 1 HP chưa làm trận kết thúc nên evaluator terminal-only vẫn cho điểm 0.
Heuristic có chấm HP, nguy cơ đạn và vị trí, nhờ đó phân biệt được hai lựa chọn.
Map minh họa **toàn bộ heuristic hiện có**, không phải chỉ riêng trọng số đạn.

## Kết quả nước đầu ở độ sâu 4

Cùng trạng thái ban đầu, không giới hạn thời gian, không history/phạt lặp:

| Map | MINIMAX / ALPHA-BETA | HEURISTIC MINIMAX / HEURISTIC ALPHA-BETA | Quan sát |
| --- | --- | --- | --- |
| H_DETOUR | FIRE | MOVE_LEFT | Chi phí đường đi giữ ở 21 so với giảm xuống 20 |
| H_DODGE | FIRE | MOVE_LEFT | Sau vòng đạn: còn 5 HP so với giữ 6 HP |

Không so sánh trị số score của hai evaluator như cùng một thang điểm.
Các ví dụ này thể hiện khác biệt lựa chọn ở độ sâu giới hạn, không khẳng định
heuristic luôn thắng, luôn chạy nhanh hơn hoặc luôn tạo ít nút hơn.
Các thuật toán tìm kiếm và trọng số heuristic không được chỉnh sửa.

## Tự chạy so sánh

Từ thư mục chứa `tanks.py`:

```sh
python task2/compare_heuristics.py --depth 4
python -m unittest discover -s tests -p "test_*.py"
```

Lệnh so sánh in nước đầu, HP sau vòng với P1 bỏ lượt, chi phí đường đi và số nút
của cả bốn thuật toán. Kiểm thử né đạn còn xét mọi nước đáp hợp lệ của P1.
Có thể thu số liệu benchmark đầy đủ cho hai map vào file riêng:

```sh
python task2/benchmark.py --scenarios h_detour h_dodge --players 0 --depths 2 4 --repeats 3 --output demo_results.csv --summary demo_summary.csv
```
