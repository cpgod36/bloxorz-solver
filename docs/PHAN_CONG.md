# Phân công & Lịch làm việc — Bloxorz Solver

**Deadline:** trước 01/11/2026 · **Mục tiêu nộp:** T6 30/10/2026 · **Dự phòng:** T7 31/10

## Phân công

| Thành viên | Code | Báo cáo / Video |
|---|---|---|
| **Phan Chí Cao** (24120026, leader) | Kiến trúc tổng; `State` + bảng chuyển tư thế + unit test; interface `Problem`/`successors`/`is_goal`; định dạng JSON; tích hợp, review | Phát biểu bài toán (state, action, transition, goal, chống lặp); bảng phân công + % đóng góp; ghép báo cáo; đóng gói nộp bài |
| **Trần Văn Đức** (24120042) | GUI pygame: vẽ bàn/khối, chơi bằng phím, nút New Game / Restart / chọn màn / Solve ×4; chạy solver trên thread riêng; animation phát lại lời giải | Quay + dựng video (phụ đề/thuyết minh); `README.md` |
| **Võ Phùng Nhật Long** (24120088) | Ô đặc biệt: fragile, bridge, switch soft/heavy/split, toggle/permanent, tách/ghép khối | Mô tả luật ô đặc biệt + quy ước nhóm tự chọn; test cho từng loại ô |
| **Hoàng Trọng Nghĩa** (24120103) | BFS, DFS/IDS; module metrics (time, `tracemalloc`, expanded nodes, solution length); `benchmark.py` xuất CSV | Mô tả BFS/DFS; bảng số liệu + biểu đồ matplotlib |
| **Lâm Duy Minh** (24120091) | UCS (chi phí không đồng nhất), A\* (heuristic, xử lý teleport); bộ màn JSON 4 nhóm độ khó | Mô tả UCS/A\*, giải thích hàm chi phí, chứng minh admissible/consistent; nhận xét ưu/nhược điểm |

## Lịch

### Giai đoạn 1 — Nền móng (15/10 – 18/10)

| Hạn | Ai | Việc |
|---|---|---|
| **T7 17/10** | **Cao** | Chốt `State`, bảng chuyển tư thế + test, interface `Problem`, định dạng JSON (**mốc chặn**) |
| CN 18/10 | Long | Tài liệu quy ước ô đặc biệt (các điểm đề chưa rõ) |
| CN 18/10 | Đức | Khung GUI: vẽ bàn, khối, chơi bằng phím (luật cơ bản) |
| CN 18/10 | Nghĩa | BFS + module metrics chạy trên màn cơ bản |
| CN 18/10 | Minh | 4–5 màn JSON nhóm 1; nháp hàm chi phí UCS |

### Giai đoạn 2 — Hoàn thiện tính năng (19/10 – 25/10)

| Hạn | Ai | Việc |
|---|---|---|
| T5 22/10 | Long | Fragile, bridge, switch soft/heavy (toggle/permanent) |
| T6 23/10 | Long | Split switch, tách/ghép khối, test đầy đủ |
| T5 22/10 | Nghĩa | DFS/IDS; `benchmark.py` xuất CSV |
| T6 23/10 | Minh | UCS + A\* chạy đúng với ô đặc biệt |
| T7 24/10 | Minh | Bộ test đủ 4 nhóm (3–5 màn/nhóm) |
| T7 24/10 | Đức | Nút Solve ×4, thread riêng, animation, hiển thị metrics |
| **CN 25/10** | **Cả nhóm** | **Đóng băng tính năng**: sau mốc này chỉ sửa lỗi |

### Giai đoạn 3 — Thực nghiệm, báo cáo, video (26/10 – 30/10)

| Hạn | Ai | Việc |
|---|---|---|
| T2 26/10 | Nghĩa | Chạy benchmark toàn bộ, gửi CSV |
| T3 27/10 | Nghĩa | Bảng + biểu đồ |
| T4 28/10 | Mọi người | Nộp phần báo cáo của mình cho Cao |
| T4 28/10 | Đức | Quay video thô (Long hỗ trợ màn switch/split) |
| T5 29/10 | Cao | Ghép báo cáo hoàn chỉnh |
| T5 29/10 | Đức | Dựng video, phụ đề, upload YouTube (public); hoàn thiện README + requirements |
| **T6 30/10** | **Cả nhóm** | Đọc chéo báo cáo, chạy thử từ máy sạch; Cao đóng gói + **nộp bài** |
| T7 31/10 | | Dự phòng |

## Họp tiến độ (15 phút)

18/10 · 22/10 · 25/10 · 28/10

## Nộp bài

`24120026_24120042_24120088_24120103_24120091.zip`

```
24120026_24120042_24120088_24120103_24120091/
├── Source/       (main.py, README.md, requirements.txt, ...)
└── Report.pdf    (có link video YouTube)
```

Mỗi người phải hiểu toàn bộ dự án, vì giảng viên có thể gọi vấn đáp ngẫu nhiên.
