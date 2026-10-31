# Bloxorz Solver

Đồ án 1 môn Cơ sở Trí tuệ Nhân tạo (CSC14003), Nhóm 14. Chương trình cài đặt lại trò chơi Bloxorz có giao diện đồ họa, gồm đủ các ô đặc biệt (ô dễ vỡ, cầu, công tắc mềm, nặng, tách), và giải các màn bằng năm thuật toán tìm kiếm tự cài đặt: BFS, DFS, IDS, UCS, A\*.

## Yêu cầu

- Python 3.10 trở lên.
- Các thư viện trong `requirements.txt`: `pygame` (giao diện), `matplotlib` (biểu đồ thực nghiệm), `pytest` (kiểm thử).

## Cài đặt

Mọi lệnh trong tài liệu này chạy từ thư mục `Source/`.

```bash
cd Source
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux / macOS
pip install -r requirements.txt
```

## Chạy trò chơi

```bash
python main.py
```

## Hướng dẫn sử dụng

### Giao diện

Bên trái là bàn chơi. Thanh bên phải gồm bốn khu vực:

1. **Chọn màn:** `< Prev` / `Next >` chuyển màn, `New Game` quay về màn đầu tiên, `Restart` chơi lại màn hiện tại.
2. **Giải tự động:** bốn nút `Solve BFS`, `Solve DFS`, `Solve UCS`, `Solve A*`.
3. **Solver Metrics:** thông số của lần giải gần nhất, gồm thuật toán, độ dài lời giải, số nút mở rộng, thời gian tìm kiếm và chi phí của lời giải.
4. **Legend & Controls:** chú giải các loại ô và phím điều khiển.

### Điều khiển

| Phím | Tác dụng |
|---|---|
| Mũi tên hoặc W / A / S / D | Lăn khối lên / trái / xuống / phải |
| Space | Đổi khối lập phương được điều khiển (khi khối đang tách) |
| R | Chơi lại màn hiện tại |
| Esc | Thoát chương trình |

### Luật chơi

- Khối hộp 1×1×2 có ba tư thế: đứng, nằm ngang, nằm dọc. Mỗi lần lăn, khối đổi tư thế theo hướng lăn.
- **Thắng** khi khối ở tư thế **đứng thẳng** trên ô đích (lỗ sâu có viền xanh lơ). Khối nằm vắt qua ô đích, hoặc một khối lập phương đơn đứng trên ô đích, đều không thắng.
- **Thua** khi có bất kỳ phần nào của khối nằm ngoài bàn, trên ô trống, hoặc trên cầu đang đóng; hoặc khi khối **đứng** trên ô dễ vỡ. Khi thua, bấm `R` hoặc nút `Restart` để chơi lại.

### Các ô đặc biệt

| Ô | Hình dạng trong game | Quy tắc |
|---|---|---|
| Ô dễ vỡ | Ô màu cam | Vỡ khi khối đứng thẳng trên đó. Khối nằm hoặc khối lập phương đơn đi qua an toàn. |
| Cầu | Ô xanh (mở) / ô rỗng (đóng) | Cầu đóng được coi như ô trống. Cầu đóng/mở nhờ công tắc. |
| Công tắc mềm | Ký hiệu `O` | Kích hoạt khi bất kỳ phần nào của khối đè lên. |
| Công tắc nặng | Ký hiệu `X` | Chỉ kích hoạt khi khối đứng thẳng trên đó. |
| Công tắc tách | Ký hiệu `( )` | Khi khối đứng thẳng trên đó, khối tách thành hai khối lập phương ở hai vị trí định sẵn. Dùng phím Space để đổi khối điều khiển. Hai khối tự ghép lại thành khối nằm khi đi tới hai ô kề cạnh nhau. |

Công tắc mềm và công tắc nặng có thể đảo, mở hoặc đóng cầu, tùy từng màn.

### Giải bằng thuật toán

Bấm một trong bốn nút Solve. Thuật toán chạy trên luồng riêng nên giao diện không bị treo. Khi có kết quả, lời giải được phát lại bằng hoạt ảnh trên bàn chơi, và thông số hiện ở khu vực Solver Metrics.

IDS không có nút trên giao diện. IDS được chạy và so sánh trong phần thực nghiệm bên dưới.

## Chạy thực nghiệm

Chạy cả năm thuật toán trên 16 màn và xuất kết quả ra tệp CSV. Mỗi lượt chạy trong một tiến trình con, giới hạn 30 giây:

```bash
python -m benchmark.benchmark --output benchmark/results/ket_qua.csv
```

Sinh bảng (`report_tables.md`) và biểu đồ từ tệp CSV:

```bash
python -m benchmark.report benchmark/results/ket_qua.csv
python -m benchmark.illustrations
```

Kết quả được ghi vào `benchmark/results/`. Dùng `python -m benchmark.benchmark --help` để xem các tùy chọn khác, như chọn thuật toán, đổi giới hạn thời gian hoặc số lần lặp.

## Chạy kiểm thử

```bash
python -m pytest tests
```

## Cấu trúc thư mục

```
Source/
├── main.py             Chạy giao diện
├── bloxorz/
│   ├── core/           Trạng thái, luật chơi, bộ đọc màn, giao diện bài toán
│   ├── solvers/        BFS, DFS, IDS, UCS, A*, hàm chi phí, heuristic, đo hiệu năng
│   └── gui/            Giao diện Pygame
├── benchmark/          Chạy thực nghiệm, sinh bảng và biểu đồ
├── levels/             16 màn chơi JSON, chia 4 nhóm độ khó
├── tests/              Kiểm thử tự động
└── requirements.txt
```

## Định dạng màn chơi

Mỗi màn là một tệp JSON trong `levels/`, gồm lưới ký tự `grid` và danh sách công tắc `switches`:

| Ký tự | Ô |
|---|---|
| `.` | Ô trống |
| `#` | Sàn |
| `S` | Vị trí bắt đầu (khối đứng) |
| `G` | Ô đích |
| `F` | Ô dễ vỡ |
| `-` / `=` | Cầu đóng / mở lúc đầu |
| `O` / `X` / `T` | Công tắc mềm / nặng / tách |

Tên tệp có dạng `g<nhóm>_<chủ đề>_<số>.json`: `g1_basic` (cơ bản), `g2_fragile` (ô dễ vỡ), `g3_switch` (công tắc và cầu), `g4_combined` (kết hợp). Mô tả đầy đủ định dạng xem mục 3.1 của báo cáo.

## Video demo

https://youtu.be/Mz166a4SrWQ
