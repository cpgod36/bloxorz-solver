# Tài liệu Quy ước Ô Đặc biệt & Các Quyết định Luật chơi (Bloxorz)

> **Tài liệu thuộc phạm vi phụ trách:** Võ Phùng Nhật Long (MSSV: 24120088)  
> **Mốc hoàn thành:** Giai đoạn 1 — Hạn Chủ Nhật 18/10/2026 (theo [docs/PHAN_CONG.md](PHAN_CONG.md))  
> **Mục đích:** Đặc tả chi tiết, chính xác cơ chế hoạt động của toàn bộ các ô đặc biệt, công tắc, chế độ tách/ghép khối, và làm rõ các điểm đề bài chưa nói rõ (Edge Cases) làm cơ sở triển khai tại [Source/bloxorz/core/rules.py](../Source/bloxorz/core/rules.py).

---

## 1. Bảng tổng quan phân loại ô & Ký hiệu

Mỗi ô trên bàn cờ Bloxorz thuộc một trong các loại ô sau. Ký hiệu trong bảng ma trận JSON tuân thủ chuẩn của dự án (xem [docs/CORE.md](CORE.md)):

| Ký tự JSON | Tên ô (`Tile`) | Biểu tượng trực quan | Mô tả tóm tắt |
|:---:|---|:---:|---|
| `.` | `Tile.VOID` | Khoảng trống | Ô hư vô, không có sàn đỡ. Chạm vào là khối rơi ngay lập tức. |
| `#` | `Tile.FLOOR` | Ô sàn thường | Sàn vững chắc, khối 1x1x2 và khối 1x1x1 di chuyển/đứng/nằm bình thường. |
| `S` | `Tile.FLOOR` | Ô xuất phát | Ô sàn thường đặc biệt nơi khối 1x1x2 bắt đầu ở tư thế đứng (`STANDING`). |
| `G` | `Tile.GOAL` | Lỗ đích | Mục tiêu của màn chơi. Chỉ khối 1x1x2 đứng thẳng lên đây mới chiến thắng. |
| `F` | `Tile.FRAGILE` | Ô dễ vỡ (Cam) | Chịu lực yếu: chỉ đỡ được khối nằm hoặc khối 1x1x1. Khối 1x1x2 đứng lên sẽ làm vỡ sàn và rơi. |
| `-` | `Tile.BRIDGE` | Cầu đóng | Trạng thái ban đầu đóng. Hoạt động như ô `VOID` (chạm vào là rơi). |
| `=` | `Tile.BRIDGE` | Cầu mở | Trạng thái ban đầu mở. Hoạt động như ô `FLOOR` (đi qua an toàn). |
| `O` | `Tile.SOFT_SWITCH` | Hình tròn / Chữ O | Công tắc mềm (nhẹ). Mọi vật thể đè lên đều kích hoạt được. |
| `X` | `Tile.HEAVY_SWITCH` | Chữ X | Công tắc nặng. Chỉ khối nguyên 1x1x2 ở tư thế đứng mới kích hoạt được. |
| `T` | `Tile.SPLIT_SWITCH` | Dấu ngoặc `( )` | Công tắc chia đôi (Teleport/Split). Chỉ khối 1x1x2 đứng mới kích hoạt được. |

---

## 2. Đặc tả Hình học & Trọng lượng của Khối

### 2.1. Khối nguyên 1x1x2
- **Tư thế Standing (Đứng):** Chiếm đúng 1 ô `(r, c)`. Toàn bộ 100% trọng lượng khối dồn vào ô duy nhất này.
- **Tư thế Horizontal (Nằm ngang):** Chiếm 2 ô kề nhau theo hàng `(r, c)` và `(r, c + 1)`. Trọng lượng được san đều 50% - 50% cho 2 ô.
- **Tư thế Vertical (Nằm dọc):** Chiếm 2 ô kề nhau theo cột `(r, c)` và `(r + 1, c)`. Trọng lượng được san đều 50% - 50% cho 2 ô.

### 2.2. Khối lập phương 1x1x1 (Sau khi tách — Cubes)
- **Nguồn gốc:** Sinh ra khi khối 1x1x2 ở tư thế đứng kích hoạt công tắc tách `( )` (`T`). Khối phân rã và dịch chuyển thành hai khối 1x1x1 độc lập tại hai tọa độ `targets = (t1, t2)`.
- **Cơ chế điều khiển:** Tại một thời điểm, chỉ có **một khối** nhận quyền điều khiển (di chuyển 1 ô mỗi bước: Up, Down, Left, Right). Hành động `SWITCH` (phím Space / ký hiệu `S`) dùng để chuyển quyền điều khiển sang khối còn lại.
- **Đặc tính trọng lượng:** Khối lượng nhẹ bằng một nửa khối 1x1x2 ban đầu. Do đó:
  - Đi qua và đứng an toàn trên ô dễ vỡ `F`.
  - Kích hoạt được công tắc mềm `O`.
  - **Không** kích hoạt được công tắc nặng `X` và công tắc tách `( )` (`T`).
  - **Không** thể hoàn thành màn chơi khi đứng trên ô Đích `G`.

---

## 3. Đặc tả chi tiết từng loại ô & Công tắc

### 3.1. Ô dễ vỡ (`Tile.FRAGILE` — Ký tự `F`)
1. **Khối 1x1x2 đứng (`STANDING`):**
   - Áp lực quá lớn dồn lên 1 điểm $\rightarrow$ Sàn sụp đổ ngay lập tức.
   - Nước đi **không hợp lệ** (`is_legal = False`), khối rơi xuống vực, trả về `None`.
2. **Khối 1x1x2 nằm (`HORIZONTAL` hoặc `VERTICAL`):**
   - Dù 1 hay cả 2 nửa thân khối nằm trên ô `F`, áp lực đã được phân bổ đều $\rightarrow$ **An toàn**, khối di chuyển bình thường. Ô `F` không bị vỡ.
3. **Khối 1x1x1 (Cube):**
   - Trọng lượng nhẹ $\rightarrow$ **An toàn**, các khối 1x1x1 có thể đứng vững trên ô `F`.

### 3.2. Cầu (`Tile.BRIDGE` — Ký tự `-` và `=`)
- Trạng thái cầu được quản lý bởi bitmask `bridges` trong `State`:
  - **Cầu đóng (Bit 0):** Xem như ô `VOID`. Bất kỳ khối nào đặt chân lên ô này đều rơi xuống vực $\rightarrow$ nước đi không hợp lệ.
  - **Cầu mở (Bit 1):** Xem như ô `FLOOR` bình thường.

### 3.3. Công tắc mềm (`SOFT_SWITCH` — Ký tự `O` / Biểu tượng vòng tròn)
- **Điều kiện kích hoạt:**
  - Bất kỳ phần nào của khối 1x1x2 (đứng hay nằm) đè lên `O`.
  - HOẶC một khối 1x1x1 đè lên `O`.
- **Cơ chế tác động:** Cập nhật bitmask của các cầu liên kết theo trường `effect`:
  - `toggle`: Đảo trạng thái cầu (mở $\leftrightarrow$ đóng).
  - `open`: Mở vĩnh viễn các cầu liên kết (chuyển bit thành 1).
  - `close`: Đóng vĩnh viễn các cầu liên kết (chuyển bit thành 0).

### 3.4. Công tắc nặng (`HEAVY_SWITCH` — Ký tự `X` / Biểu tượng chữ X)
- **Điều kiện kích hoạt:**
  - **CHỈ** kích hoạt khi khối nguyên 1x1x2 ở tư thế **đứng (`STANDING`)** hoàn toàn trên ô `X`.
- **Trường hợp KHÔNG kích hoạt:**
  - Khối 1x1x2 ở tư thế nằm đè lên `X` $\rightarrow$ Không kích hoạt (coi như sàn thường).
  - Khối 1x1x1 đè lên `X` $\rightarrow$ Không kích hoạt (coi như sàn thường).
- **Cơ chế tác động:** Tương tự công tắc mềm (`toggle`, `open`, `close`).

### 3.5. Công tắc tách (`SPLIT_SWITCH` — Ký tự `T` / Biểu tượng `( )`)
- **Điều kiện kích hoạt:**
  - **CHỈ** kích hoạt khi khối nguyên 1x1x2 ở tư thế **đứng (`STANDING`)** hoàn toàn trên ô `T`.
- **Trường hợp KHÔNG kích hoạt:**
  - Khối 1x1x2 nằm đè lên `T` $\rightarrow$ Không kích hoạt.
  - Khối 1x1x1 đè lên `T` $\rightarrow$ Không kích hoạt.
- **Cơ chế tác động:**
  - Triệt tiêu khối 1x1x2.
  - Tạo ra 2 khối 1x1x1 tại hai tọa độ chỉ định trước trong `targets = (t1, t2)`.
  - Khối tại `t1` (`targets[0]`) mặc định nhận quyền điều khiển đầu tiên.
  - Chuyển `State` sang trạng thái tách: `block = None`, `cubes = (t1, t2)`.

### 3.6. Ô Đích (`Tile.GOAL` — Ký tự `G`)
1. **Khối 1x1x2 đứng (`STANDING`):**
   - Khối lọt vừa khít vào lỗ đích $\rightarrow$ **Chiến thắng** (`is_goal = True`).
2. **Khối 1x1x2 nằm:**
   - Thân khối nằm vắt ngang qua ô đích $\rightarrow$ Đi qua bình thường như sàn phẳng, **không thắng**.
3. **Khối 1x1x1:**
   - Đi vào hoặc đứng trên ô đích $\rightarrow$ Đi qua bình thường như sàn phẳng, **không thắng** (*A single cube never wins*).

---

## 4. Các Trường hợp Biên (Edge Cases) & Quyết định Nhóm đã Thống nhất

Phần này làm rõ toàn bộ các góc khuất và tình huống đặc thù mà đề bài chưa nêu rõ, do thành viên **Long** chốt quy ước:

### 4.1. Edge Case 1: Cầu bị rút dưới chân khối (Tự làm sập cầu)
- **Mô tả:** Khối 1x1x2 lăn đến tư thế nằm: một nửa thân đè lên công tắc mềm `O`, nửa còn lại nằm trên cây cầu đang mở `=`. Công tắc `O` được kích hoạt và làm đóng chính cây cầu đó lại (`=` thành `-`).
- **Quy ước xử lý:**
  - Ngay sau khi `apply_effects`, cây cầu dưới chân nửa thân khối biến thành ô trống hư vô (`VOID`).
  - Khối mất điểm tựa $\rightarrow$ **Khối lập tức rơi xuống vực $\rightarrow$ Nước đi không hợp lệ (`result = None`)**.

### 4.2. Edge Case 2: Khối đứng yên trên công tắc trong Chế độ Tách (Split Mode)
- **Mô tả:** Khối A đang đứng trên công tắc mềm `O` (loại `toggle`). Khối B di chuyển từng bước ở khu vực khác.
- **Quy ước xử lý:**
  - Công tắc chỉ được ấn khi có khối **mới bước chân vào** trong lượt đi hiện tại.
  - Khối A đứng yên tại chỗ không tạo thêm lực tác động mới lên công tắc $\rightarrow$ **Không kích hoạt lại công tắc ở mỗi bước đi của Khối B**.

### 4.3. Edge Case 3: Thao tác đổi lượt `SWITCH` (phím Space / ký hiệu `S`)
- **Mô tả:** Khối A đang đứng trên một công tắc mềm `O`. Người chơi bấm phím `SWITCH` để chuyển quyền điều khiển sang Khối B (hoặc người lại chuyển từ khối B sang khối A).
- **Quy ước xử lý:**
  - Thao tác `SWITCH` không làm khối dịch chuyển vị trí cũng như tạo lực tác động mới lên công tắc $\rightarrow$ **Không kích hoạt công tắc**.
  - Không gọi hàm `apply_effects`, giữ nguyên trạng thái cầu `state.bridges`.

### 4.4. Edge Case 4: Cơ chế Tự động Ghép khối (Merge)
- **Mô tả:** Hai khối 1x1x1 di chuyển đến gần nhau.
- **Quy ước xử lý:**
  - **Điều kiện ghép:** Hai khối phải nằm ở **hai ô liền kề cạnh** (4-connected, khoảng cách Manhattan $|r_1 - r_2| + |c_1 - c_2| = 1$).
  - **Kề chéo:** Nếu hai khối chạm nhau theo đường chéo (khoảng cách Manhattan = 2, ví dụ `(r, c)` và `(r+1, c+1)`) $\rightarrow$ **KHÔNG ghép khối**.
  - **Hình thái sau ghép:** Tự động sáp nhập tức thì thành **khối nằm 1x1x2**:
    - Cùng hàng kề cột (`(r, c)` và `(r, c + 1)`): Tạo thành `Block(r, c, Orientation.HORIZONTAL)`.
    - Cùng cột kề hàng (`(r, c)` và `(r + 1, c)`): Tạo thành `Block(r, c, Orientation.VERTICAL)`.
    - **Không bao giờ ghép thành tư thế đứng (`STANDING`)**.

### 4.5. Edge Case 5: Va chạm giữa hai khối 1x1x1
- **Mô tả:** Khối đang điều khiển cố gắng bước vào đúng ô mà khối thứ hai đang đứng.
- **Quy ước xử lý:**
  - Hai khối vật lý đặc không thể cùng chiếm 1 ô tọa độ.
  - Về logic bước đi, trước khi bước đè lên nhau thì chúng đã phải đứng ở 2 ô kề nhau, và ngay tại bước kề nhau đó chúng đã lập tức ghép khối (Merge) thành khối 1x1x2 rồi. Nước đi bước đè lên nhau là **nước đi không hợp lệ**.

### 4.6. Edge Case 6: Một trong hai khối 1x1x1 bị rơi xuống hố
- **Mô tả:** Khối đang điều khiển bước hụt ra ngoài mép sàn hoặc bước vào ô `VOID` / cầu đóng, trong khi khối kia vẫn an toàn trên sàn.
- **Quy ước xử lý:**
  - Cả 2 khối là một thực thể người chơi thống nhất. Mất 1 khối là vĩnh viễn không thể ghép lại và không thể thắng $\rightarrow$ **Thua cuộc ngay lập tức (`result = None`)**.

### 4.7. Edge Case 7: Nằm đè lên cùng lúc 2 công tắc mềm
- **Mô tả:** Khối 1x1x2 ở tư thế nằm đè lên cùng lúc 2 công tắc mềm $O_1$ và $O_2$.
- **Quy ước xử lý:**
  - Cả hai công tắc đều được kích hoạt theo thứ tự tọa độ từ trái sang phải, từ trên xuống dưới.
  - Nếu cả hai công tắc cùng điều khiển một cây cầu với hiệu ứng `toggle`: Cầu sẽ bị đảo trạng thái 2 lần (ví dụ: đang mở $\rightarrow$ đóng $\rightarrow$ mở lại).

### 4.8. Edge Case 8: Ghép khối ngay trên ô dễ vỡ (`Tile.FRAGILE`)
- **Mô tả:** Khối A đứng trên sàn thường, Khối B bước lên ô `F` ngay cạnh Khối A.
- **Quy ước xử lý:**
  - Ngay khi Khối B đặt chân lên `F`, hai khối liền kề nhau và lập tức ghép thành khối 1x1x2 ở **tư thế nằm**.
  - Vì khối nằm có trọng lượng phân bổ đều 50% - 50% nên ô `F` **an toàn, không bị sập**.

---

## 5. Nguyên tắc Triển khai Mã nguồn (`rules.py`)

Khi hiện thực hóa các quy ước trên vào mã nguồn tại `Source/bloxorz/core/rules.py`:

1. **Tính bất biến (`Immutability`):**
   - Tuyệt đối không thay đổi thuộc tính của đối tượng `Level`.
   - Hàm `apply_effects(level, state)` luôn trả về một thể hiện `State` mới (hoặc trả về chính `state` nếu không có hiệu ứng nào kích hoạt).
2. **Kiểm tra tính hợp lệ sau hiệu ứng:**
   - Trong `apply_effects`, sau khi cập nhật bitmask cầu mới, phải kiểm tra lại xem mọi ô khối đang chiếm đóng có còn hợp lệ hay không (`is_passable`). Nếu có ô nào biến thành cầu đóng, trả về `None` (khối rơi).
3. **Thứ tự xử lý một nước đi (`problem.result`):**
   - Bước 1: Tính vị trí hình học mới sau khi lăn / bước (`roll` / `step`).
   - Bước 2: Kiểm tra tính hợp lệ cơ bản bằng `rules.is_legal` (biên, void, cầu đóng ban đầu, đứng trên ô fragile).
   - Bước 3: Áp dụng hiệu ứng ô đặc biệt bằng `rules.apply_effects` (công tắc, đảo cầu, tách khối, ghép khối, kiểm tra sập cầu dưới chân).
