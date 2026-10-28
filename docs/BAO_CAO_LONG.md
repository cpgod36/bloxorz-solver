# BÁO CÁO KỸ THUẬT & ĐÓNG GÓP CÁ NHÂN
## Module Ô Đặc Biệt (Advanced Tiles & Game Mechanics)
### Môn học: Cơ sở Trí tuệ Nhân tạo (CSC14003) — Đồ án 1: Bloxorz Solver

---

**Thông tin sinh viên:**
- **Họ và tên:** Võ Phùng Nhật Long
- **MSSV:** 24120088
- **Lớp:** CSC14003 — Khoa Công nghệ Thông tin, Trường ĐH Khoa học Tự nhiên, ĐHQG-HCM
- **Phần việc đảm nhiệm:** Module `bloxorz/core/`: Các ô đặc biệt (Fragile, Bridges, Soft/Heavy/Split switches, Split/Merge mechanics), tài liệu quy ước `docs/SPECIAL_TILES.md`, và bộ kiểm thử `Source/tests/test_rules.py`.
- **Mức độ hoàn thành:** 100% (Hoàn thành đầy đủ các mốc theo phân công).

---

## 1. Tổng quan Công việc & Lịch trình Thực hiện

Trong khuôn khổ Đồ án 1 môn Cơ sở Trí tuệ Nhân tạo, sinh viên chịu trách nhiệm xây dựng toàn bộ mô hình chuyển trạng thái (Transition Model) và các quy tắc vật lý cho hệ thống ô đặc biệt trên bàn cờ Bloxorz (chi tiết phân công tại [docs/PHAN_CONG.md](PHAN_CONG.md)). Module này đóng vai trò miền bài toán cốt lõi (Core Domain), cung cấp các hàm chuyển tiếp trạng thái chuẩn xác cho các thuật toán tìm kiếm không gian trạng thái (BFS, DFS/IDS, UCS, A\*) và hỗ trợ kết nối hiển thị trên giao diện đồ họa (GUI).

| Thời gian | Nhiệm vụ | Kết quả đạt được | Mã nguồn & Tài liệu |
|:---:|---|:---:|---|
| **18/10** | Xây dựng tài liệu quy ước ô đặc biệt và các trường hợp biên | Hoàn thành | [docs/SPECIAL_TILES.md](SPECIAL_TILES.md) (PR #3 đã merge vào `main`) |
| **22/10** | Cài đặt Ô dễ vỡ (`Fragile`), Cầu (`Bridge`), Công tắc mềm/nặng (`toggle/permanent`), Edge Case 1 | Hoàn thành | Logic tại [rules.py](../Source/bloxorz/core/rules.py), 17 tests tại `test_rules.py` (Nhánh `feat/long-switch-rules`) |
| **23/10** | Cài đặt Công tắc tách (`SPLIT_SWITCH`), Chế độ tách & Tự động ghép khối (`MERGE`) | Hoàn thành | Hoàn thiện [rules.py](../Source/bloxorz/core/rules.py), 29 tests tại `test_rules.py` (Nhánh `feat/long-split-merge`) |
| **28/10** | Chuẩn bị nội dung báo cáo kỹ thuật & hỗ trợ kịch bản video demo | Hoàn thành | Tài liệu `docs/BAO_CAO_LONG.md` |

---

## 2. Mô hình Không gian Trạng thái & Kỹ thuật Nén Bitmask

### 2.1. Biểu diễn trạng thái (`State`)
Không gian trạng thái mở rộng của bài toán được mô hình hóa bằng cấu trúc dữ liệu bất biến (`Immutable NamedTuple`):

$$\text{State} = \langle \text{block}, \text{cubes}, \text{bridges} \rangle$$

- $\text{block}$: Đối tượng $\text{Block}(row, col, orientation)$ biểu diễn khối nguyên $1 \times 1 \times 2$. Nhận giá trị `None` khi ở chế độ phân tách.
- $\text{cubes}$: Cặp tọa độ $((r_1, c_1), (r_2, c_2))$ theo thứ tự $(controlled, other)$ khi ở chế độ phân tách. Nhận giá trị `None` khi ở trạng thái khối nguyên.
- $\text{bridges}$: Số nguyên (`int`) đóng vai trò mặt nạ bit đại diện cho trạng thái đóng/mở của toàn bộ các ô cầu trên bàn cờ.

### 2.2. Kỹ thuật quản lý trạng thái cầu bằng Bitmask ($O(1)$)
- **Vấn đề đặt ra:** Một màn chơi có thể có nhiều ô cầu độc lập. Nếu biểu diễn trạng thái cầu bằng danh sách hoặc tập hợp tọa độ (`set`), trạng thái sẽ là mutable, không thể băm (`__hash__`) để đưa vào tập đóng (`Closed Set`) của BFS/A\*, đồng thời gây tốn bộ nhớ khi thuật toán duyệt hàng chục ngàn nút.
- **Giải pháp:** Sử dụng một số nguyên duy nhất ($B \in \mathbb{N}$) làm mặt nạ nhị phân:
  - Mỗi ô cầu $c$ được ánh xạ tới một vị trí bit duy nhất $i = \text{level.bridge\_bit}[c]$.
  - Bit $i = 1$: Cầu mở (hoạt động như ô sàn `FLOOR` bình thường).
  - Bit $i = 0$: Cầu đóng (hoạt động như ô trống `VOID`, khối chạm vào sẽ rơi xuống vực).

- **Các thao tác cập nhật trạng thái cầu bằng đại số Boolean ($O(1)$):**
  - **Kiểm tra ô cầu mở:**
    $$\text{IsOpen}(c, B) \iff (B \gg \text{bridge\_bit}[c]) \ \& \ 1 = 1$$
  - **Đảo trạng thái (`TOGGLE`):** Dùng phép XOR bitwise:
    $$B_{new} = B \oplus M$$
  - **Mở vĩnh viễn (`OPEN`):** Dùng phép OR bitwise:
    $$B_{new} = B \lor M$$
  - **Đóng vĩnh viễn (`CLOSE`):** Dùng phép AND NOT bitwise:
    $$B_{new} = B \ \& \ (\sim M)$$
  - **Hỗ trợ Multi-bridges:** Một công tắc liên kết tới $k$ ô cầu ($k \ge 1$) được gom vào một mặt nạ chung:
    $$M = \sum_{j=1}^{k} 2^{\text{bridge\_bit}[c_j]}$$
    Nhờ đó, việc đóng/mở đồng thời toàn bộ các ô cầu liên kết luôn diễn ra trong duy nhất $1$ chu kỳ máy ($O(1)$).

---

## 3. Đặc tả Kỹ thuật Cơ chế Ô Đặc biệt

### 3.1. Ô dễ vỡ (`Tile.FRAGILE` — Ký hiệu `F`)
Áp lực cơ học lên mặt sàn tỉ lệ nghịch với diện tích tiếp xúc: $P = \frac{F}{A}$:
- **Khối đứng (`STANDING`):** Toàn bộ trọng lượng dồn vào 1 ô duy nhất ($A = 1$). Áp lực lớn khiến sàn dễ vỡ sụp đổ ngay lập tức $\rightarrow$ bước đi không hợp lệ (`is_legal = False`), khối rơi xuống vực (`None`).
- **Khối nằm ngang/dọc (`HORIZONTAL` / `VERTICAL`):** Trọng lượng phân bổ đều trên 2 ô ($A = 2$, áp lực giảm một nửa) $\rightarrow$ sàn chịu lực an toàn, khối di chuyển bình thường.
- **Khối lập phương $1 \times 1 \times 1$:** Khối lượng giảm một nửa so với khối ban đầu $\rightarrow$ đứng an toàn trên ô dễ vỡ.

- **Quy tắc kiểm tra vi phạm sàn dễ vỡ:**
  $$\text{ViolateFragile}(s) \iff \text{IsStanding}(s) \land \big(\text{Tile}(s.\text{block.cells}()[0]) = \text{FRAGILE}\big)$$
  *(Khi điều kiện trên thỏa mãn, hàm `is_legal` lập tức trả về `False`, nhánh tìm kiếm dừng lại).*

### 3.2. Công tắc mềm (`SOFT_SWITCH` — Ký hiệu `O`) & Công tắc nặng (`HEAVY_SWITCH` — Ký hiệu `X`)
- **Công tắc mềm (`O`):** Kích hoạt khi có bất kỳ phần nào của khối đè lên (đứng hoặc nằm, ngang hoặc dọc, hoặc khối $1 \times 1 \times 1$).
- **Công tắc nặng (`X`):** Đòi hỏi áp lực tập trung tối đa, do đó **chỉ** kích hoạt khi khối nguyên $1 \times 1 \times 2$ ở tư thế đứng thẳng (`STANDING`) hoàn toàn trên ô `X`. Khối nằm đè lên hoặc khối $1 \times 1 \times 1$ đè lên đều không kích hoạt.

- **Quy tắc kích hoạt công tắc $sw$ tại vị trí tiếp xúc:**
  $$\text{Triggered}(sw, s) \iff (sw.\text{kind} = \text{SOFT}) \lor \text{IsStanding}(s)$$

### 3.3. Công tắc tách (`SPLIT_SWITCH` — Ký hiệu `T`) & Cơ chế Dịch chuyển
- **Điều kiện kích hoạt:** Chỉ khối nguyên $1 \times 1 \times 2$ ở tư thế đứng thẳng (`STANDING`) mới kích hoạt được ô `T`. Khối nằm hoặc khối $1 \times 1 \times 1$ đè lên sẽ không có tác dụng.
- **Quá trình xử lý:**
  1. Chuyển đổi cấu trúc: Hủy biểu diễn khối nguyên (`block = None`).
  2. Khởi tạo hai khối lập phương $1 \times 1 \times 1$ tại các vị trí chỉ định: `switch.targets = (t1, t2)`.
  3. Gán quyền điều khiển ưu tiên cho khối tại $t_1$: `state.cubes = (t1, t2)`.

### 3.4. Chế độ Phân tách (Split Mode)
- **Thao tác `Action.SWITCH` (Phím Space):** Đổi quyền điều khiển sang khối còn lại: $(c_1, c_2) \rightarrow (c_2, c_1)$. Thao tác này không thay đổi tọa độ nên không kích hoạt công tắc dưới chân.
- **Di chuyển:** Mỗi lượt chỉ di chuyển khối đang nhận quyền điều khiển (Up, Down, Left, Right). Khối còn lại giữ nguyên vị trí.
- **Ràng buộc của khối $1 \times 1 \times 1$:** Không kích hoạt công tắc nặng `X`, không kích hoạt công tắc tách `T`, và đứng trên ô đích `G` không thể hoàn thành màn chơi (*A single cube never wins*).

### 3.5. Cơ chế Tự động Ghép khối (Cube Merging)
- **Điều kiện kích hoạt:** Sau mỗi bước di chuyển của một khối lập phương, hệ thống kiểm tra khoảng cách Manhattan giữa 2 khối:
  $$d(C_1, C_2) = |r_1 - r_2| + |c_1 - c_2|$$
  - Nếu $d = 1$ (hai khối kề cạnh nhau theo 4 hướng chính): Tự động hợp nhất tức thì thành khối nằm $1 \times 1 \times 2$.
  - Nếu $d \ge 2$ (bao gồm cả trường hợp kề chéo): Giữ nguyên chế độ phân tách.
- **Hình thái khối ghép:** Luôn là khối nằm, không bao giờ xuất hiện tư thế đứng:
  - Cùng hàng kề cột ($r_1 = r_2$): Ghép thành khối nằm ngang $\text{Block}(r_1, \min(c_1, c_2), \text{HORIZONTAL})$.
  - Cùng cột kề hàng ($c_1 = c_2$): Ghép thành khối nằm dọc $\text{Block}(\min(r_1, r_2), c_1, \text{VERTICAL})$.

```text
Thuật toán: TryMerge(c1, c2)
Đầu vào: Tọa độ hai khối lập phương c1 = (r1, c1), c2 = (r2, c2)
Đầu ra: Khối hợp nhất Block hoặc None

1. dr ← |r1 - r2|
2. dc ← |c1 - c2|
3. Nếu dr + dc ≠ 1 thì:
4.     Trả về None                          // Chưa kề cạnh, giữ nguyên split mode
5. Nếu dr = 0 thì:
6.     Trả về Block(r1, min(c1, c2), HORIZONTAL)   // Hợp nhất nằm ngang
7. Ngược lại (dc = 0):
8.     Trả về Block(min(r1, r2), c1, VERTICAL)     // Hợp nhất nằm dọc
```

---

## 4. Xử lý 10 Trường hợp Biên (Edge Cases)

Các trường hợp biên được thống nhất và xử lý trong code theo bảng sau:

| Mã | Tình huống biên | Cách xử lý trong mã nguồn |
|:---:|---|---|
| **EC-01** | Cầu sập dưới chân khối | Khối nằm: nửa thân đè switch mềm, nửa thân đè cầu mở. Switch làm đóng chính cây cầu đó. Trong `apply_effects`, sau khi cập nhật `bridges`, hàm kiểm tra lại `is_passable`. Khối mất điểm tựa $\rightarrow$ rơi xuống vực (`return None`). |
| **EC-02** | Khối đứng yên trên switch ở Split mode | Khối A đứng yên trên switch mềm toggle, khối B bước đi ở ô khác. Trong `pressed_switches`, chỉ kiểm tra ô của khối vừa di chuyển `state.cubes[0]`, bỏ qua `state.cubes[1]`. Switch dưới chân A không bị kích hoạt lại. |
| **EC-03** | Thao tác đổi quyền điều khiển `SWITCH` | Đổi lượt bằng phím Space không dịch chuyển vị trí khối, không gọi `apply_effects`, giữ nguyên trạng thái cầu `bridges`. |
| **EC-04** | Ghép khối trên công tắc mềm | Khối B di chuyển đến ghép với khối A đang đứng sẵn trên switch mềm. Switch dưới chân A không bị kích hoạt lại vì A không phải là khối di chuyển trong lượt đó. |
| **EC-05** | Va chạm giữa hai khối lập phương | `is_legal` kiểm tra `cubes[0] == cubes[1]` $\rightarrow$ `return False`. Thực tế ở khoảng cách 1 chúng đã tự động ghép khối từ bước trước. |
| **EC-06** | Một trong hai khối rơi xuống vực | Khối đang điều khiển bước ra ngoài sàn hoặc rơi vào cầu đóng. Hai khối là thực thể thống nhất, mất 1 khối là thua ngay lập tức (`result = None`). |
| **EC-07** | Nằm đè lên cùng lúc 2 switch mềm | Khối nằm đè lên 2 switch mềm cùng lúc. Kích hoạt tuần tự từ trái qua phải, trên xuống dưới. Nếu cùng toggle 1 cầu, cầu sẽ đảo trạng thái 2 lần ($0 \rightarrow 1 \rightarrow 0$). |
| **EC-08** | Ghép khối ngay trên ô dễ vỡ `FRAGILE` | Khối B bước lên ô `F` kề cạnh khối A. Hai khối lập tức ghép thành khối nằm. Vì khối nằm san đều trọng lượng nên sàn `F` an toàn, không vỡ. |
| **EC-09** | Teleport đáp xuống công tắc mềm | Tọa độ `targets` của switch tách rơi trúng switch mềm. Được tính là sự kiện mới bước vào ô $\rightarrow$ kích hoạt switch mềm đó ngay khi tiếp đất. |
| **EC-10** | Teleport đáp xuống cầu đang đóng | Tọa độ `targets` rơi vào ô cầu đóng. Cầu đóng tương đương ô hư vô $\rightarrow$ khối mất điểm tựa, rơi xuống vực (`result = None`). |

---

## 5. Kết quả Thực nghiệm Kiểm thử Độc lập

Module kiểm thử tự động gồm **29 unit tests** độc lập được viết tại [Source/tests/test_rules.py](../Source/tests/test_rules.py):

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.7.0
collected 111 items

tests\test_bfs.py ........                                               [  7%]
tests\test_geometry.py ...............................                   [ 35%]
tests\test_level.py ......................                               [ 54%]
tests\test_metrics.py .......                                            [ 61%]
tests\test_problem.py ..............                                     [ 73%]
tests\test_rules.py .............................                        [100%]

============================= 111 passed in 0.30s =============================
```

### Phân nhóm 29 bài test của Module Rules:
1. **Ô dễ vỡ & Cầu (5 tests):** Đứng vỡ sàn, nằm ngang an toàn, nằm dọc an toàn, cầu đóng như void, cầu mở như floor.
2. **Công tắc mềm & Nặng (6 tests):** Kích hoạt switch mềm (đứng, nằm ngang, nằm dọc), kích hoạt switch nặng (chỉ khi đứng, nằm không kích hoạt), công tắc điều khiển nhiều cầu cùng lúc (`multi-bridges`).
3. **Hiệu ứng cầu & Sập cầu (6 tests):** Hiệu ứng `open`, `close`, `toggle`, sập cầu do close (EC-01), sập cầu do toggle (EC-01), đè 2 switch cùng lúc (EC-07).
4. **Công tắc tách (4 tests):** Đứng tách, nằm không tách, teleport vào cầu đóng (EC-10), teleport vào switch mềm (EC-09).
5. **Ghép khối (4 tests):** Ghép hàng ngang `HORIZONTAL`, ghép cột dọc `VERTICAL`, kề chéo không ghép, ghép an toàn trên ô dễ vỡ (EC-08).
6. **Khối lập phương & Va chạm (4 tests):** Khối đứng yên không kích hoạt lại switch (EC-02), khối $1 \times 1 \times 1$ không kích hoạt switch nặng/tách, khối $1 \times 1 \times 1$ đứng trên Goal không thắng, kiểm tra va chạm trùng tọa độ (EC-05).
7. **Tích hợp Solver:** `test_bfs_solves_stage_with_split_and_merge` — Thuật toán BFS tìm đường giải thành công trên màn chơi có đầy đủ chu trình: *Lăn tới switch tách $\rightarrow$ Teleport $\rightarrow$ Điều khiển 2 khối qua phím Switch $\rightarrow$ Ghép khối lại $\rightarrow$ Về đích Goal*.

---

## 6. Câu hỏi & Trả lời Vấn đáp (Oral Defense Q&A)

Chuẩn bị cho các buổi vấn đáp ngẫu nhiên của môn học:

- **Câu hỏi 1: Tại sao `apply_effects` không thay đổi trực tiếp thuộc tính của `Level` mà phải trả về một thể hiện `State` mới?**  
  *Trả lời:* `Level` lưu địa hình tĩnh của màn chơi và được chia sẻ dùng chung cho toàn bộ các nút trên cây tìm kiếm. Toàn bộ biến động trạng thái (cầu đóng/mở) được nén trong thuộc tính `bridges` của `State`. Việc giữ `State` là cấu trúc bất biến (`immutable`) giúp loại bỏ hoàn toàn các tác dụng phụ ngoài ý muốn (`side-effects`) giữa các nhánh duyệt, đồng thời cho phép băm giá trị (`__hash__`) để lưu trữ chính xác trong tập đóng (`Closed Set`) của các thuật toán tìm kiếm.
- **Câu hỏi 2: Tại sao hàm `apply_effects` có dòng kiểm tra `if bridges == state.bridges: return state`?**  
  *Trả lời:* Đây là kỹ thuật tái sử dụng đối tượng (`Object Reuse`) để tối ưu hóa bộ nhớ. Đa số các bước lăn của khối diễn ra trên sàn bình thường và không làm thay đổi trạng thái đóng/mở của cầu. Việc trả về ngay đối tượng `state` cũ giúp chương trình không phải cấp phát hàng vạn `NamedTuple` mới lên bộ nhớ heap, giảm tải công việc thu gom rác (`Garbage Collection`) của Python và nâng cao tốc độ mở rộng nút.
- **Câu hỏi 3: Nếu một khối $1 \times 1 \times 1$ bước lên ô đích `Tile.GOAL` thì có tính là chiến thắng không?**  
  *Trả lời:* Không. Đề bài quy định rõ *"A single cube never wins"*. Ô đích chỉ chấp nhận khối nguyên $1 \times 1 \times 2$ ở tư thế đứng thẳng (`STANDING`). Khi đang ở chế độ phân tách, thuộc tính `state.is_standing` luôn trả về `False`, do đó khối $1 \times 1 \times 1$ đứng trên đích sẽ không thỏa điều kiện thắng (`is_goal` trả về `False`).
- **Câu hỏi 4: Tại sao sau khi hợp nhất (`try_merge`), khối luôn ở trạng thái nằm (`HORIZONTAL` hoặc `VERTICAL`) mà không bao giờ ở trạng thái đứng (`STANDING`)?**  
  *Trả lời:* Vì hai khối lập phương $1 \times 1 \times 1$ di chuyển độc lập trên cùng một mặt phẳng sàn 2D. Khi khoảng cách Manhattan bằng 1, chúng tiếp giáp nhau theo cạnh kề (cùng hàng kề cột hoặc cùng cột kề hàng). Muốn tạo thành khối đứng $1 \times 1 \times 2$, một khối lập phương bắt buộc phải xếp chồng lên trên khối kia theo trục cao $Z$ (không gian 3D), điều này không thể xảy ra trong chuyển động lăn trên mặt phẳng của trò chơi. Bất biến này cũng giải thích vì sao hai khối ghép trên ô dễ vỡ `FRAGILE` (EC-08) luôn an toàn tuyệt đối.
- **Câu hỏi 5: Tại sao trong chế độ phân tách (Split mode), hàm `pressed_switches` chỉ kiểm tra khối đang điều khiển `state.cubes[0]` mà bỏ qua khối đứng yên `state.cubes[1]`?**  
  *Trả lời:* Trong Bloxorz, công tắc (đặc biệt là công tắc đảo `toggle`) hoạt động theo sự kiện bước chân (step-on event) — tức là chỉ kích hoạt khi có khối vừa di chuyển vào ô. Nếu mỗi lượt đi của khối điều khiển đều kích hoạt lại công tắc dưới chân của khối đứng yên thì cây cầu liên kết sẽ liên tục bị đảo trạng thái một cách sai quy tắc (vi phạm EC-02). Do đó, khối đứng yên phải hoàn toàn thụ động.

---

## 7. Phụ lục Minh bạch Sử dụng Trí tuệ Nhân tạo (Generative AI Appendix)

Tuân thủ quy định tại Mục 3.6 đề bài và Mục 4 của [SETUP.md](../SETUP.md):

- **Công cụ sử dụng:** Antigravity AI Coding Assistant (mô hình Gemini, phát triển bởi Google DeepMind).
- **Phương thức cộng tác (Pair-Programming):**
  - Sinh viên trực tiếp nghiên cứu đề bài, thiết kế tài liệu quy ước [docs/SPECIAL_TILES.md](SPECIAL_TILES.md), xây dựng giải thuật kiểm tra hợp lệ, cơ chế ghép khối và kiểm soát toàn bộ logic.
  - Sử dụng AI như một trợ lý lập trình: Hỗ trợ sinh nhanh các trường hợp kiểm thử (test cases), rà soát cú pháp toán tử bitwise và kiểm tra chéo các ca biên để đảm bảo không bỏ sót lỗi.
- **Cam kết liêm chính học thuật:** Toàn bộ mã nguồn và test case đều do sinh viên tự kiểm soát, hiểu rõ bản chất từng dòng code và sẵn sàng bảo vệ độc lập trong các buổi vấn đáp của môn học.
