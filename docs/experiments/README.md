# Số liệu thực nghiệm

Số liệu, bảng và hình dùng trong phần thực nghiệm của báo cáo ([docs/report/Nghia_BFS_DFS_IDS_Thuc_nghiem.md](../report/Nghia_BFS_DFS_IDS_Thuc_nghiem.md), mục 9).

| Tệp | Nội dung | Sinh bởi |
|---|---|---|
| `benchmark_full_20261026.csv` | 80 lượt chạy: 16 màn × 5 giải thuật | `benchmark.benchmark` |
| `report_tables.md` | Bảng theo từng màn và bảng trung bình nhân theo nhóm | `benchmark.report` |
| `fig_metrics_by_group.png`, `fig_cost_ratio.png`, `fig_hardest_levels.png` | Hình 5, 7, 6 | `benchmark.report` (đọc CSV) |
| `fig_level_groups.png`, `fig_exploration_order.png`, `fig_bfs_layers.png`, `fig_ids_passes.png` | Hình 1, 2, 3, 4 | `benchmark.illustrations` (chạy lại solver, không đọc CSV) |

## Lần chạy benchmark

- **Người chạy:** Hoàng Trọng Nghĩa, lúc 20:05 ngày 26/10/2026 (cột `timestamp` trong CSV).
- **Máy:** Intel Core i3-1115G4 @ 3,0 GHz (4 luồng), khoảng 8 GB RAM, Linux, Python 3.14.7.
- **Commit:** CSV không ghi commit. Lúc chạy, `main` đang ở `a2b54aa`. Các cột tất định (`solution_length`, `expanded_nodes`, `solution_cost`) chạy lại khớp **80/80 dòng** trên cả `a2b54aa` và `04f98b6` (main ngày 29/10).
- **Cấu hình:** mặc định của `benchmark.py`: giới hạn 30 giây mỗi lượt; lượt dưới 1 giây chạy 3 lần lấy trung vị thời gian (cột `time_repeats`); bộ nhớ đỉnh đo ở một lần chạy riêng có bật `tracemalloc`.

Thời gian và bộ nhớ phụ thuộc máy chạy. Chạy lại trên máy khác sẽ ra số khác, nhưng thứ tự giữa các giải thuật giữ nguyên.

## Tái tạo

Chạy từ thư mục `Source/` với môi trường ảo của dự án:

```
python -m benchmark.benchmark --output benchmark/results/<tên>.csv
python -m benchmark.report ../docs/experiments/benchmark_full_20261026.csv --out ../docs/experiments
python -m benchmark.illustrations --out ../docs/experiments
```

Bảng và hình trong thư mục này được sinh bằng hai lệnh sau, trên commit `04f98b6`.
