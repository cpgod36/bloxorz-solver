# Lõi game (`bloxorz.core`): hướng dẫn dùng

Tài liệu dành cho cả nhóm. Người chịu trách nhiệm: **Cao**. Code nằm ở `Source/bloxorz/core/`.

```python
from bloxorz.core import BloxorzProblem, load_level, Action, format_actions

problem = BloxorzProblem(load_level("levels/g1_basic_01.json"))
state = problem.initial_state
for action, nxt in problem.successors(state):   # các nước đi hợp lệ, thứ tự U, D, L, R (+ S)
    ...
problem.is_goal(state)
```

---

## 1. Định dạng màn chơi (JSON)

```json
{
  "name": "Tên màn (tuỳ chọn, mặc định là tên file)",
  "grid": [
    "S#O-=#",
    "##X--#",
    "#T#FFG"
  ],
  "switches": [
    {"pos": [0, 2], "effect": "toggle", "bridges": [[0, 3], [0, 4]]},
    {"pos": [1, 2], "effect": "open",   "bridges": [[1, 3], [1, 4]]},
    {"pos": [2, 1], "targets": [[0, 0], [2, 0]]}
  ]
}
```

| Ký tự | Ô | Ghi chú |
|---|---|---|
| `.` | Void | Không có ô sàn |
| `#` | Sàn | |
| `S` | Sàn, vị trí bắt đầu | Đúng 1 ô. Khối bắt đầu ở tư thế đứng |
| `G` | Lỗ đích | Đúng 1 ô |
| `F` | Ô dễ vỡ (fragile) | |
| `-` | Cầu, **đóng** lúc đầu | |
| `=` | Cầu, **mở** lúc đầu | |
| `O` | Công tắc mềm (soft) | Cần một mục trong `switches` |
| `X` | Công tắc nặng (heavy) | Cần một mục trong `switches` |
| `T` | Công tắc tách (split) | Cần một mục trong `switches` |

- Tọa độ ghi dạng `[hàng, cột]`, bắt đầu từ 0, hàng 0 ở trên cùng.
- Các hàng ngắn hơn sẽ được tự đệm thêm `.` ở cuối, nên không cần gõ dấu chấm thừa.
- **Công tắc soft/heavy** có hai trường:
  - `effect`: `toggle` (lật trạng thái), `open` hoặc `close` (cố định trạng thái).
  - `bridges`: danh sách ô cầu mà công tắc điều khiển.
- **Công tắc split** có trường `targets`: 2 ô nơi hai khối lập phương xuất hiện. Hai ô phải khác nhau, không phải void và **không được kề cạnh nhau** (nếu kề nhau thì hai khối sẽ ghép lại ngay; xem `docs/SPECIAL_TILES.md`, mục 4.10). Kề chéo thì được.
- Loại công tắc lấy theo ký tự trong `grid`, nên trong `switches` không cần ghi lại loại.
- File sai định dạng sẽ báo lỗi `LevelFormatError` kèm vị trí cụ thể.

Ví dụ đầy đủ: `Source/tests/fixtures/classic_01.json` (màn 1 game gốc, tối ưu 7 nước `RDDRRDR`) và `Source/tests/fixtures/all_tiles.json` (có đủ mọi loại ô, **chỉ để test bộ đọc**, không giải được).

---

## 2. Trạng thái (`State`)

```python
State(block, cubes, bridges)     # NamedTuple: bất biến, hash được, dùng thẳng làm key của set/dict
```

| Trường | Ý nghĩa |
|---|---|
| `block` | `Block(row, col, orientation)` khi khối còn nguyên, `None` khi đã tách |
| `cubes` | `((r, c), (r, c))` khi đã tách: **phần tử đầu là khối đang điều khiển**. `None` khi khối còn nguyên |
| `bridges` | Số nguyên bitmask: bit `i` bằng 1 nghĩa là cầu `level.bridge_cells[i]` đang mở |

- Cách neo vị trí: `Block` được neo ở **ô trên cùng bên trái**.
  - `STANDING` chiếm ô `(r, c)`.
  - `HORIZONTAL` chiếm hai ô `(r, c)` và `(r, c+1)`.
  - `VERTICAL` chiếm hai ô `(r, c)` và `(r+1, c)`.
- Cùng vị trí khối nhưng trạng thái cầu khác nhau thì là **hai trạng thái khác nhau**. Đề yêu cầu điều này.
- Khi đã tách, hành động `SWITCH` chỉ đơn giản đổi thứ tự hai phần tử trong `cubes`.
- Các tiện ích:
  - `state.cells()` trả về các ô đang bị chiếm.
  - `state.is_split` và `state.is_standing` cho biết khối đang tách hay đang đứng.
  - `state.bridge_open(i)` cho biết cầu thứ `i` có đang mở không.

---

## 3. Hành động và bảng chuyển tư thế

`Action.UP / DOWN / LEFT / RIGHT / SWITCH` (giá trị `"U" "D" "L" "R" "S"`).

| Tư thế \ Hướng | Up | Down | Left | Right |
|---|---|---|---|---|
| Standing `(r,c)` | V `(r-2,c)` | V `(r+1,c)` | H `(r,c-2)` | H `(r,c+1)` |
| Horizontal `(r,c)` | H `(r-1,c)` | H `(r+1,c)` | S `(r,c-1)` | S `(r,c+2)` |
| Vertical `(r,c)` | S `(r-1,c)` | S `(r+2,c)` | V `(r,c-1)` | V `(r,c+1)` |

Khi đã tách, mỗi khối lập phương chỉ đi 1 ô mỗi bước. Code: `geometry.TRANSITIONS`, `roll()`, `step()`.

---

## 4. Interface `BloxorzProblem`

| Thành phần | Trả về |
|---|---|
| `initial_state` | Trạng thái ban đầu |
| `actions(state)` | Bộ hành động theo **thứ tự cố định** U, D, L, R (thêm S khi đã tách) |
| `result(state, action)` | Trạng thái kế tiếp, hoặc **`None` nếu khối rơi** (nước đi không hợp lệ) |
| `successors(state)` | `list[(action, next_state)]` chỉ gồm các nước hợp lệ, giữ đúng thứ tự trên |
| `is_goal(state)` | `True` khi khối còn nguyên, **đứng**, và nằm trên ô đích |

Các hàm hỗ trợ:
- `replay(problem, actions)`: trả về danh sách trạng thái đi qua, dùng cho GUI phát lại lời giải. Báo lỗi `IllegalMoveError` nếu có bước làm khối rơi.
- `parse_actions("RDDR")` chuyển chuỗi thành danh sách hành động; `format_actions(actions)` làm ngược lại.

**Chi phí không định nghĩa trong `core`.** Mỗi solver tự nhận hàm chi phí của mình (phần của Minh).

### Ghi chú cho từng người
- **Nghĩa (BFS/DFS):**
  - Chỉ cần `initial_state`, `successors`, `is_goal`.
  - `State` hash được nên dùng thẳng làm key của tập visited.
- **Minh (UCS/A\*):**
  - Hàm chi phí dạng `cost(state, action, next_state)`.
  - Heuristic đọc `state.cells()`, `state.is_standing` và `problem.level.goal`.
- **Đức (GUI):**
  - Vẽ bàn bằng `level.grid` và `level.tile((r, c))`. Màu cho cầu lấy theo `state.bridges`.
  - Khi người chơi bấm phím, gọi `problem.result()`:
    - Nếu nhận về `None` thì người chơi **thua**.
    - Nếu `is_goal` đúng thì người chơi **thắng**.
  - Chỉ cho phép phím Space khi `state.is_split`.
- **Long (ô đặc biệt):** xem mục 5.

---

## 5. Phần việc của Long trong `rules.py`

`problem.result()` xử lý một nước đi theo 3 bước:
1. Tính vị trí mới bằng `roll` (khối nguyên) hoặc `step` (khối lập phương).
2. Gọi `rules.is_legal()`. Nếu không hợp lệ thì trả về `None`.
3. Gọi `rules.apply_effects()` để các ô phản ứng.

Những phần **đã làm**, vì đề đã nói rõ:
- Ra ngoài bàn, ô trống, hoặc cầu đang đóng: nước đi không hợp lệ.
- Khối nguyên **đứng** trên ô dễ vỡ: nước đi không hợp lệ.
- `pressed_switches()` xác định công tắc nào được kích hoạt:
  - Công tắc soft: bất kỳ phần nào của khối, hoặc một khối lập phương, đè lên là kích hoạt.
  - Công tắc heavy/split: chỉ khi khối nguyên đứng trên đó.

Những phần **Long cần làm** (các chỗ đánh dấu `TODO(Long)`):
- `apply_effects()`:
  - Cập nhật `bridges` theo `switch.effect` và `switch.bridge_mask`.
  - Tách khối tại `switch.targets`.
  - Ghép hai khối lập phương khi chúng kề nhau thành khối nằm.
- Quyết định và ghi lại các điểm đề chưa nói rõ:
  - Khối lập phương đơn đứng trên ô dễ vỡ thì sao (game gốc cho phép)?
  - Công tắc đóng đúng cây cầu mà khối đang đứng thì sao?

Hiện tại, màn nào có công tắc sẽ báo `NotImplementedError` khi khối chạm công tắc. Đây là chủ ý, để thấy ngay chỗ chưa làm thay vì cho kết quả sai mà không ai biết.

---

## 6. Test

```bash
cd Source
python -m pytest          # pytest.ini đã cấu hình sẵn đường dẫn
```

Các file test: `tests/test_geometry.py` (đủ 12 ô của bảng chuyển tư thế, lăn ngược thì về vị trí cũ), `tests/test_level.py` (bộ đọc màn và 17 trường hợp file lỗi), `tests/test_problem.py` (rơi, thắng, ô dễ vỡ, cầu, `SWITCH`, `replay`).
