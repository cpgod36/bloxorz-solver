# Hướng dẫn cài đặt & quy trình làm việc

Đọc hết file này một lần trước khi bắt đầu code. Nếu bạn dùng AI agent (Claude Code, Codex, Cursor, Copilot...), agent sẽ tự đọc [AGENTS.md](AGENTS.md). **Bạn vẫn phải đọc file này**, vì có những việc agent không làm thay bạn được.

---

## 1. Cài đặt lần đầu

**Cần có:** Python **3.10+**, Git, tài khoản GitHub đã được mời vào repo.

```bash
git clone https://github.com/cpgod36/bloxorz-solver.git
cd bloxorz-solver

# Khai báo tên/email để commit hiện đúng người (dùng email của tài khoản GitHub)
git config user.name "Họ Tên Của Bạn"
git config user.email "email-github-cua-ban@example.com"

cd Source
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

python -m pytest tests            # chạy được (kể cả khi chưa có test) là cài đặt OK
```

Mọi lệnh Python về sau đều chạy **trong thư mục `Source/`** và trong venv đã kích hoạt.

---

## 2. Vùng code của từng người

Mỗi người **chịu trách nhiệm chính** cho vùng của mình. Muốn sửa vùng của người khác thì nhắn người đó trước, hoặc tag họ review PR.

| Người | Vùng code |
|---|---|
| **Cao** | `bloxorz/core/` phần lõi: state, bảng chuyển tư thế, interface `Problem`, load màn JSON |
| **Long** | `bloxorz/core/` phần ô đặc biệt: fragile, bridge, switch, split/merge |
| **Đức** | `bloxorz/gui/`, `main.py`, `Source/README.md` |
| **Nghĩa** | `bloxorz/solvers/` BFS, DFS/IDS, metrics; `benchmark/` |
| **Minh** | `bloxorz/solvers/` UCS, A\*, heuristic, hàm chi phí; `levels/` |

**Interface lõi** (cách biểu diễn `State`, hàm `successors`, `is_goal`, định dạng JSON) do Cao chốt. Muốn đổi interface thì **báo cả nhóm trước**, vì đổi một chỗ sẽ làm hỏng code của 4 người còn lại.

---

## 3. Quy trình hằng ngày

```bash
# 1. Cập nhật main mới nhất
git switch main
git pull

# 2. Tạo branch cho việc mình làm
git switch -c feat/bfs-solver        # tên branch: feat/..., fix/..., docs/..., test/...

# 3. Code, chạy test, commit nhỏ và thường xuyên
python -m pytest tests
git add <các file đã sửa>
git commit -m "feat(solvers): add BFS solver"

# 4. Đẩy lên và mở Pull Request
git push -u origin feat/bfs-solver
gh pr create --fill                  # hoặc mở PR trên web GitHub
```

### Quy ước commit
Dạng `loại(phạm-vi): mô tả ngắn` bằng tiếng Anh:
- **Loại:** `feat`, `fix`, `test`, `docs`, `refactor`, `chore`
- **Phạm vi:** `core`, `tiles`, `gui`, `solvers`, `levels`, `benchmark`, `docs`
- **Ví dụ:** `fix(tiles): heavy switch must not trigger when lying`

### Pull Request
- Mỗi PR chỉ làm **một việc**. PR nhỏ thì review nhanh và ít xung đột.
- Điền checklist trong template PR.
- Cần **ít nhất 1 người khác** đọc và approve trước khi merge. Mặc định người review là Cao. Nếu PR đụng vùng của ai thì tag thêm người đó.
- Merge bằng **Squash and merge**, sau đó xóa branch.
- **Không push thẳng lên `main`**, **không `git push --force`** lên `main`. Repo không có cơ chế chặn tự động, nên mọi người phải tự giác.

### Khi `main` đã thay đổi trong lúc bạn đang làm
```bash
git switch main && git pull
git switch feat/ten-branch
git merge main                       # gặp xung đột thì sửa, rồi git add + git commit
```
Nếu không chắc cách gỡ xung đột ở vùng code của người khác, **hỏi người đó**. Đừng tự chọn bừa một bên.

---

## 4. Dùng AI agent

AI được phép dùng, nhưng **bạn phải hiểu và giải thích được mọi dòng code mình nộp**. Giảng viên có quyền gọi vấn đáp ngẫu nhiên. Nếu agent viết code, hãy yêu cầu nó giải thích lại cho đến khi bạn tự trình bày được.

Một số lưu ý thêm:
- Cho agent biết bạn là ai và đang làm việc gì, ví dụ: *"Mình là Nghĩa, đang làm BFS theo docs/PHAN_CONG.md"*. Nhờ vậy agent sẽ giữ đúng vùng code của bạn.
- **Đọc diff trước khi commit.** Agent đôi khi sửa lan sang file không liên quan.
- Đề bắt buộc **tự cài đặt thuật toán tìm kiếm**. Không để agent dùng thư viện giải sẵn như `networkx`, `simpleai`, `aima`...

---

## 5. Thế nào là xong một việc

- [ ] Code chạy được, `python -m pytest tests` pass.
- [ ] Có test cho phần mới (bắt buộc với `core/` và `solvers/`).
- [ ] PR đã được review và merge vào `main`.
- [ ] Đã cập nhật tiến độ với nhóm. Lịch và mốc xem tại [docs/PHAN_CONG.md](docs/PHAN_CONG.md).
