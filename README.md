# Bloxorz Solver — CSC14003 Project 1

Đồ án 1 môn Cơ sở Trí tuệ Nhân tạo (CSC14003), FIT – HCMUS.
Tái hiện game **Bloxorz** có GUI và giải tự động bằng **BFS, DFS/IDS, UCS, A\***.

**Deadline:** trước 01/11/2026 (mục tiêu nộp 30/10/2026).

## Thành viên

| MSSV | Họ tên | Phụ trách chính |
|---|---|---|
| 24120026 | Phan Chí Cao (leader) | State, transition, interface, tích hợp, báo cáo tổng |
| 24120042 | Trần Văn Đức | GUI, video, README |
| 24120088 | Võ Phùng Nhật Long | Ô đặc biệt (fragile, bridge, switch, split) |
| 24120103 | Hoàng Trọng Nghĩa | BFS, DFS/IDS, metrics, benchmark, biểu đồ |
| 24120091 | Lâm Duy Minh | UCS, A\*, bộ màn test |

Chi tiết phân công và lịch: [docs/PHAN_CONG.md](docs/PHAN_CONG.md) · Đề bài: [docs/AI - Project 1.md](docs/AI%20-%20Project%201.md)

## Cấu trúc thư mục

```
Source/                 # thư mục nộp bài
├── main.py             # entry point (mở GUI)
├── bloxorz/
│   ├── core/           # state, bảng chuyển tư thế, luật chơi, ô đặc biệt, load màn
│   ├── gui/            # giao diện pygame
│   └── solvers/        # bfs, dfs/ids, ucs, astar, metrics
├── levels/             # màn chơi JSON (dùng chung cho mọi solver)
├── benchmark/          # script chạy thực nghiệm, vẽ biểu đồ
├── tests/              # unit test
├── README.md           # hướng dẫn chạy (nộp kèm)
└── requirements.txt
docs/                   # đề bài, phân công, tài liệu nội bộ (không nộp)
```

## Cài đặt và chạy

```bash
cd Source
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python main.py
python -m pytest tests
```

## Quy ước làm việc

- Không commit thẳng lên `main`. Mỗi việc một branch: `feat/<tên-việc>`, `fix/<tên-lỗi>`.
- Mở Pull Request vào `main`, cần ít nhất 1 người review (mặc định là leader).
- Chạy `python -m pytest tests` trước khi mở PR.
- **Không tự viết lại thuật toán tìm kiếm bằng thư viện có sẵn**: đề bắt buộc tự cài đặt.
