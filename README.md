# NMTTNT — Battle City AI

Game xe tăng dùng Python/Pygame, gồm hai chế độ:

- **01 PLAYER:** người chơi dùng bàn phím đấu với **4 NPC trên cùng bản đồ**.
  NPC 1 dùng Minimax; NPC 2 dùng Heuristic Minimax; NPC 3 dùng Alpha-Beta;
  NPC 4 dùng Heuristic Alpha-Beta.
- **AI BATTLE:** chọn hai AI để đấu với nhau, không có lựa chọn Human.

## Cài đặt và chạy

Cần Python 3.10 trở lên. Giải nén mã nguồn, mở terminal trong thư mục chứa `tanks.py`:

```sh
python -m pip install -r requirements.txt
python tanks.py
```

Mũi tên: di chuyển/xoay; Space: bắn; X: bỏ lượt.
Trận đấu vận hành theo lượt. P tạm dừng, R chơi lại, Esc quay lại thiết lập.

Chi tiết luật trận, lớp kết nối và cách kiểm tra: [AI_BATTLE_README.md](AI_BATTLE_README.md).
Bốn file lõi trong `task2/` được giữ nguyên từ bản ZIP đầu vào.
Ở trận 1 chọi 4, mỗi NPC dùng bản chiếu trạng thái hai xe để giữ nguyên thuật toán gốc;
các NPC khác được xem là vật cản khi lập kế hoạch. Đây không phải tìm kiếm đầy đủ năm tác nhân.

## Map so sánh trước và sau heuristic

Trong AI BATTLE, chọn **H_DETOUR** (đường vòng) hoặc **H_DODGE** (né đạn).
Xem cách chạy và kết quả đối chiếu tại [DEMO_MAPS.md](DEMO_MAPS.md).

```sh
python task2/compare_heuristics.py --depth 4
```

## Map bất đối xứng

Chọn **AI BATTLE → MAP → ASYMMETRIC** để dùng map 11 × 11, xe P0 dưới trái
và xe P1 trên phải, khác cả hàng lẫn cột. Xem [sơ đồ và vị trí xuất phát](ASYMMETRIC_MAP.md).

## Kiểm tra

```sh
python tests/smoke_modes.py
```

## Nguồn gốc

Phát triển từ [raitisg/battle-city-tanks](https://github.com/raitisg/battle-city-tanks)
và bản mã nguồn/AI do người dùng cung cấp.
