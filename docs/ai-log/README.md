# Log sử dụng AI

Báo cáo **bắt buộc** có phụ lục mô tả cách nhóm dùng AI và các prompt đã dùng. Mỗi người ghi log vào file riêng: `cao.md`, `duc.md`, `long.md`, `nghia.md`, `minh.md`. Cuối dự án, Cao tổng hợp các file này thành phụ lục.

Ghi sau mỗi việc **đáng kể**: viết một module, sửa một bug khó, thiết kế heuristic... Không cần ghi các câu hỏi vặt.

## Mẫu

```markdown
## 2026-10-18 — BFS solver

- **Công cụ:** Claude Code / ChatGPT / Copilot / ...
- **Prompt chính:**
  > Viết BFS solver cho Bloxorz dùng interface Problem trong bloxorz/core, đếm expanded nodes khi pop khỏi frontier...
- **AI đã làm:** viết `solvers/bfs.py` và test trên 3 màn nhỏ.
- **Mình đã làm / kiểm tra:** đọc lại toàn bộ code, sửa chỗ đếm node bị đếm 2 lần, tự kiểm tra độ dài lời giải bằng tay trên màn g1_basic_01.
```
