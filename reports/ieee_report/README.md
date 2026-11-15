# Báo cáo LaTeX theo mẫu IEEE

Dùng `IEEEtran.cls` lấy trực tiếp từ `IEEE_Conference_Template.zip` bạn gửi.
Giữ bố cục conference hai cột, cỡ chữ mặc định 10 pt và khổ A4; dùng XeLaTeX để hỗ trợ tiếng Việt Unicode.

## Cấu trúc

```text
ieee_report/
├── main.tex                 # File tổng: tiêu đề, thành viên, input, tài liệu tham khảo
├── IEEEtran.cls             # Class IEEE gốc từ mẫu được cung cấp
├── tasks/
│   ├── task1.tex            # Khung Bài toán 1, chờ thành viên bổ sung
│   ├── task2.tex            # Bài toán 2 — Battle City, đã viết đầy đủ
│   └── task3.tex            # Khung Bài toán 3, chờ thành viên bổ sung
├── figures/                 # Ảnh UI thực tế và biểu đồ dùng trong Bài 2
├── data/                    # Bốn CSV tham khảo và cấu hình môi trường
├── preview.pdf              # Bản biên dịch để xem trước
└── README.md
```

Có **ba file nội dung tương ứng ba bài toán**. `main.tex` là file điều phối để ghép chúng thành một báo cáo; không phải bài toán thứ tư.
Chưa có đề/nội dung Bài 1 và 3 nên hai file này chỉ để khung, không tự đặt thuật toán hoặc số liệu.

## Mở bằng Overleaf

1. Chọn **New Project → Upload Project**, tải ZIP lên và mở project.
2. Trong **Settings/Menu**, đặt **Main document = main.tex** và **Compiler = XeLaTeX**.
3. Chọn **Recompile**. Nếu tải riêng thư mục từ GitHub, cần tải đủ cả class, tasks và figures.

Để biên dịch trên máy có TeX Live/MiKTeX:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

Hoặc chạy `xelatex main.tex` hai lần để cập nhật số hình, bảng và trích dẫn.
Font Times tương thích là TeX Gyre Termes; có fallback Liberation Serif khi không có font này.

## Chỗ cần điền khi ghép bài nhóm

- Điền họ tên/MSSV, lớp/nhóm, trường/khoa và giảng viên trong `main.tex`.
- Thành viên khác chỉ viết phần nội dung vào `tasks/task1.tex` và `tasks/task3.tex`; không thêm `documentclass` hoặc `begin{document}` vào các file con.
- Sau khi có Bài 1 và 3, bổ sung tóm tắt/từ khóa chung ở `main.tex`. Tóm tắt hiện tại chỉ mô tả phần Battle City.
- Dùng nhãn `t1:...`, `t2:...`, `t3:...` để tránh trùng nhãn hình, bảng và phương trình.
- Tài liệu tham khảo dùng chung ở cuối `main.tex`; thêm các nguồn của Bài 1 và 3 tại đó.
- Các lời nhắc ở Bài 1 và 3 cần được thay bằng nội dung thật trước khi nộp báo cáo nhóm.

## Nội dung và số liệu Bài 2

Phần Battle City có mô hình zero-sum, sáu hành động, HP và luật đạn,
terminal/utility, giả định luân phiên, bốn cấu hình, công thức heuristic,
OOP, UI Pygame, giao thức agent ngoài, thiết kế đo công bằng, bảng/biểu đồ,
kiểm thử, giới hạn, kết luận và lệnh tái hiện.

Số liệu lấy từ CSV đã có của dự án, không sinh số liệu giả:

- 240 lượt tìm kiếm trên năm kịch bản, hai bên, depth 2/4, ba lần lặp và bốn mode.
- Bảng snapshot lấy **trung bình trực tiếp từ CSV thô**, 30 lượt cho mỗi mode/depth.
- 120 cặp cùng evaluator khớp giá trị.
- 60 trận đổi bên, depth 3: 44 trận có người thắng, tám hòa thật và tám chưa kết thúc.
- Giới hạn 60 cycle chỉ thuộc bộ chạy thí nghiệm, không thuộc luật hoặc utility.
- Môi trường đã đo: Linux x86_64, Python 3.12.14; chưa phải máy macOS Intel i5 của đề.

Thư mục `data/` là bản sao nguồn số liệu để đối chiếu, không cần để LaTeX biên dịch.
Biểu đồ và ảnh đã được đóng gói trong `figures/`. `preview.pdf` sẽ cần biên dịch lại khi chỉnh nội dung.
Bộ này chỉ thêm tài liệu; không thay đổi thuật toán hoặc mã game.
