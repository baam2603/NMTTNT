# Map Battle City gốc đã chuyển sang định dạng AI

Có **35 map**, chọn trong **AI BATTLE → MAP → ORIGINAL_01 … ORIGINAL_35**.
Khi đang chọn dòng MAP, nhấn **O** để tới ORIGINAL_01, trái/phải đổi màn;
PageUp/PageDown nhảy 5 map, Home/End tới map đầu/cuối. Thanh bên ghi LV01 … LV35.


## Định dạng và vị trí xuất phát

- `01.txt` … `35.txt`: mỗi file 13 dòng × 13 cột, đúng định dạng GameState đang dùng.
- `manifest.json`: tên file nguồn, mã kiểm tra nội dung, vị trí/hướng xe và thông tin chuyển đổi.
- `levels/1` … `levels/35` vẫn nguyên vẹn, không bị sửa hay ghi đè.

| Ký hiệu sau chuyển | Ý nghĩa |
| --- | --- |
| `.` | Ô trống |
| `W` | Gạch 3 HP |
| `S` | Thép không phá được |
| `a` | Căn cứ P0, 9 HP |
| `b` | Căn cứ P1, 9 HP |

Tọa độ `(hàng,cột)` tính từ 0:

| Thành phần | Vị trí | Hướng |
| --- | --- | --- |
| Xe P0 / 1P | `(12,4)` — phía dưới trái | Lên |
| Xe P1 / 2P | `(0,12)` — góc trên phải | Xuống |
| Căn cứ P0 | `(12,6)` — giữa cạnh dưới | — |
| Căn cứ P1 | `(0,6)` — giữa cạnh trên | — |

Hai xe cùng 6 HP, không cùng hàng/cột. Căn cứ trên được bổ sung vì game đối kháng
của bạn cần hai căn cứ, trong khi map gốc chỉ dành sẵn chỗ cho căn cứ phía dưới.
Không cần xóa chướng ngại vật ở bốn vị trí này trên cả 35 map.

## Quy tắc chuyển đổi

Nguồn gốc dùng 26 × 26 ô nhỏ, mỗi ô 16 pixel. Xe gốc chiếm khoảng 2 × 2 ô nhỏ.
Vì xe AI chiếm một ô, bộ chuyển gộp **2 × 2 → 1**, tạo lưới 13 × 13.
Bàn 416 pixel hiện tại có ô 32 pixel khi chơi các map này.

| Ký hiệu nguồn | Chuyển thành |
| --- | --- |
| `#` — gạch | `W` |
| `@` — thép | `S` |
| `~` — nước | `S` |
| `%` — cỏ | `.` |
| `-` — băng | `.` |
| `.` — trống | `.` |

Trong một nhóm hỗn hợp, thứ tự ưu tiên là **thép/nước > gạch > trống**.
Mỗi ô gạch mới có 3 HP theo luật AI, không cộng HP của bốn ô nguồn.

Đây là **bản thích nghi địa hình**, không giữ nguyên toàn bộ cơ chế game gốc:
engine hiện tại chưa có nước/cỏ/băng. Nước thành thép sẽ chặn cả xe **và đạn**,
khác nước gốc cho đạn đi qua; không có che khuất bởi cỏ hay trượt trên băng.
Những ô hỗn hợp có thể trở thành chướng ngại vật toàn ô sau khi gộp.
Các loại địa hình được chuyển rõ sang W/S/trống để hình vẽ và va chạm thống nhất.

Tất cả map có đường hình học tới căn cứ đối phương nếu cho phép phá gạch; không
bảo đảm đường đi hoàn toàn trống hay hai vị trí có lợi thế ngang nhau. Riêng
ORIGINAL_34, P0 cần phá gạch trước khi di chuyển; ba lần bắn lên trên mở được lối.
Giữ cùng điều kiện và đổi thuật toán giữa P0/P1 khi so sánh.

Các map nhập này hiện phục vụ **hai AI đấu nhau**. Chế độ một người/4 NPC giữ
8 map trước đó: một số map gốc không đủ chỗ trống để đặt cả bốn NPC gần điểm sinh,
nên không tự xóa tường hoặc đổi luật để ép thêm xe.

## Chỉnh sửa và chuyển lại

Bạn có thể sửa W/S/`.`/a/b trong file TXT rồi bắt đầu lại trận. Vị trí xe và hướng
đọc từ `tank_pos`/`directions` trong manifest; vị trí căn cứ đọc từ a/b trong TXT.
`base_pos` trong manifest ghi lại vị trí lúc chuyển để đối chiếu.
Mã SHA-256 trong manifest ghi nội dung lúc chuyển; loader vẫn đọc bản TXT đã sửa nếu định dạng hợp lệ.

Chuyển lại toàn bộ map nguồn (sẽ ghi lại TXT/manifest, không sửa thư mục nguồn):

```sh
python task2/original_maps.py --convert
```

Xuất sang thư mục riêng:

```sh
python task2/original_maps.py --convert --source-dir levels --output-dir my_levels_ai
```

UI đọc `levels_ai/` mặc định. Nội dung nguồn và TXT được ghi mã SHA-256 theo UTF-8,
xuống dòng LF để có thể kiểm tra trên cả Windows/macOS/Linux.

Benchmark dùng đúng thuật toán hiện tại:

```sh
python task2/benchmark.py --scenarios original_01 original_19 original_35 --players both --depths 2 4 --repeats 3 --output original_results.csv --summary original_summary.csv
```

`--scenarios all` nay gồm 43 map (8 map cũ + 35 map gốc). Dữ liệu tham khảo cũ
trong experiments/ vẫn chỉ thuộc 8 map đã ghi trong báo cáo; không tự coi đó là
số liệu của các map mới.
