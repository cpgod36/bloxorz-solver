# Log sử dụng AI — Phan Chí Cao

## 2026-10-12 — Phân tích đề

- **Công cụ:** Claude Code (Claude Opus 5.5)
- **Prompt chính:**
  > chuyển file yêu cầu này thành markdown rồi phân tích những việc cần làm giúp tôi nhé
- **AI đã làm:** chuyển `AI - Project 1.pdf` sang Markdown, tóm tắt thang điểm, liệt kê các việc cần làm và những điểm đề bài chưa nói rõ.
- **Mình đã làm / kiểm tra:** đối chiếu bản Markdown với PDF gốc.

## 2026-10-15 — Phân công, repo, quy trình làm việc

- **Công cụ:** Claude Code (Claude Opus 5.5)
- **Prompt chính:**
  > đây là nhóm của tôi nhé … (danh sách 5 thành viên)
  > hoán đổi việc của long và đức đi
  > deadline chính xác là trước 1/11/2026 nhé.
  > giờ thì tạo repo thôi
  > giờ chúng ta viết một file setup để hướng dẫn quy trình làm việc cho mỗi người đi, viết cho agent của họ nữa …
- **AI đã làm:** đề xuất phân công + lịch theo ngày (`docs/PHAN_CONG.md`), tạo repo GitHub private và khung `Source/`, viết `SETUP.md`, `AGENTS.md`, template PR, mẫu log AI.
- **Mình đã làm / kiểm tra:** đổi phân công giữa Đức và Long, chốt deadline, quyết định không dùng branch protection (gói Free).

## 2026-10-15 — Lõi game: state, bảng chuyển tư thế, interface, loader

- **Công cụ:** Claude Code (Claude Opus 5.5)
- **Prompt chính:**
  > ok, làm phần của tôi luôn đi
- **AI đã làm:** viết `bloxorz/core/` gồm `geometry.py` (bảng chuyển tư thế), `state.py`, `level.py` (định dạng JSON + kiểm tra lỗi), `rules.py` (luật hợp lệ, chỗ nối cho Long), `problem.py` (`BloxorzProblem`, `replay`); 64 unit test; tài liệu `docs/CORE.md`. Kiểm chứng bằng màn 1 game gốc: lời giải tối ưu 7 nước `RDDRRDR`.
- **Mình đã làm / kiểm tra:** _(điền sau khi tự đọc lại code: tự lăn tay lời giải, đọc bảng chuyển tư thế, chạy pytest)_
