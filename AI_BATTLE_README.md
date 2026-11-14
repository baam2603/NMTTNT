# Battle City — 1 người đấu 4 NPC và AI đấu AI

## Chạy game

Cài Python 3.10 trở lên. Mở terminal tại thư mục chứa `tanks.py`:

```sh
python -m pip install -r requirements.txt
python tanks.py
```

## Hai chế độ trên menu

- **01 PLAYER:** dùng bàn phím đấu đồng thời với 4 NPC trên cùng bản đồ.
  P0 cố định là người chơi. P1 cố định là đội 4 NPC; không phải danh sách chọn từng NPC.
  NPC 1: Minimax; NPC 2: Heuristic Minimax; NPC 3: Alpha-Beta;
  NPC 4: Heuristic Alpha-Beta. Số trên xe trùng số trong bảng bên phải.
  SEARCH DEPTH phía đội NPC áp dụng cho cả bốn xe.
- **AI BATTLE:** chọn hai AI, độ sâu riêng từng bên và bản đồ. Không có tùy chọn Human.
  Vẫn có thể nạp AI bên ngoài bằng F5 như giao diện cũ.

Chế độ 2 người chơi bàn phím đã được bỏ khỏi menu.
Giữ màu sắc, sprite, kích thước cửa sổ và bố cục giao diện hiện có.

## Điều khiển

Setup: lên/xuống chọn dòng, trái/phải đổi giá trị, Enter bắt đầu, Esc về menu.
Trận 1 người: phím mũi tên di chuyển/xoay, Space bắn, X bỏ lượt.
Mỗi vòng gồm lượt người chơi và lần lượt 4 NPC còn sống, sau đó đạn di chuyển.
Cả bốn NPC hiện diện và hoạt động trong cùng một trận, không phải bốn trận riêng.
NPC bị hạ sẽ được bỏ qua lượt; thắng khi hạ toàn bộ NPC hoặc phá căn cứ đội NPC.
Người chơi thua khi xe hoặc căn cứ của mình bị phá. Đội NPC dùng chung một căn cứ.
Luật sát thương giữ cả va chạm đạn với đồng đội như engine gốc.

B ở setup đổi ngân sách chung. Trong trận: P tạm dừng, N đi từng hành động AI,
Tab phân tích tìm kiếm (AI BATTLE), V bật/tắt hướng súng, +/- đổi tốc độ, R chơi lại, Esc về setup.
Khi tạm dừng, bàn phím di chuyển/bắn cũng được khóa; nhấn P để tiếp tục.

## Thuật toán và các cập nhật

Giữ bản chất bốn cấu hình; cập nhật các file lõi để đồng bộ hòa theo vòng,
kiểm tra thời gian, cache evaluator và đếm thống kê. Phạt lặp mặc định bằng 0
cho phép so sánh cùng hàm mục tiêu. [Chi tiết và cách xem UI](ADVERSARIAL_SEARCH.md).
`ai_battle.py` nối giao diện với API `Agent.act` hiện có.
`arena.py` bổ sung trạng thái 5 xe và mở rộng xử lý va chạm đạn cho 5 xe.

Vì thuật toán gốc chỉ tìm kiếm giữa 2 phe/2 xe, mỗi NPC lập kế hoạch từ một
bản chiếu gồm chính nó và người chơi; các NPC khác được xem là vật cản tĩnh,
đạn NPC quy về cùng phe và hai căn cứ được giữ nguyên. NPC không dự đoán các
nước đi tương lai của đồng đội. Đây là xấp xỉ ở lớp kết nối để giữ nguyên
thuật toán; không phải tìm kiếm đối kháng đầy đủ với 5 tác nhân. Trận thực
vẫn xử lý cả năm xe, lượt từng NPC và mọi viên đạn trên bản đồ thật.

## Kiểm tra

```sh
python tests/smoke_modes.py
```

Bộ kiểm tra dùng SDL dummy (không mở cửa sổ): spawn trên 5 bản đồ, sát thương
vào xe thứ 5, bỏ qua NPC chết, thắng theo đội, chạy vòng lặp bàn phím thật
với 4 NPC và chạy chế độ AI đấu AI. Ảnh kiểm tra được lưu vào thư mục tạm.
