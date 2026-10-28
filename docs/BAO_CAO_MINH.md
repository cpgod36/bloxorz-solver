# Phần báo cáo: UCS, A* và Heuristic — Lâm Duy Minh (24120091)

---

## 3.3. Thuật toán Uniform-Cost Search (UCS)

### 3.3.1. Ý tưởng

UCS (Uniform-Cost Search) mở rộng các đỉnh theo thứ tự **chi phí đường đi tích lũy tăng dần** $g(n)$. Khi chi phí mỗi bước di chuyển là không đồng nhất (ví dụ: lăn ngang tốn 1.0, dựng đứng tốn 3.0), UCS đảm bảo tìm được đường đi có **tổng chi phí nhỏ nhất**, không chỉ ít bước nhất.

### 3.3.2. Cấu trúc dữ liệu

| Thành phần | Mô tả |
|---|---|
| **Hàng đợi ưu tiên (frontier)** | `heapq` lưu bộ $(g, \text{tie\_breaker}, s)$. `tie_breaker` đơn điệu tăng để phá hòa khi hai đỉnh có cùng $g$, tránh so sánh trực tiếp giữa hai đối tượng `State`. |
| **`best_cost[s]`** | Dictionary ánh xạ mỗi trạng thái $s$ đến chi phí đường đi tốt nhất từ trạng thái đầu đến $s$ đã biết. |
| **`parent[s]`** | Lưu cặp $(\text{state}_{\text{prev}}, \text{action})$ để truy vết đường đi khi tìm thấy đích. |

### 3.3.3. Thuật toán

```
function UCS(problem, cost_fn):
    frontier ← MinHeap chứa (0.0, 0, start_state)
    best_cost[start_state] ← 0.0
    parent[start_state] ← None

    while frontier ≠ ∅:
        g, _, s ← frontier.pop_min()

        if g > best_cost[s]:          // Lazy deletion
            continue

        if is_goal(s):                // Goal test khi POP
            return reconstruct_path(parent, s)

        for (action, s') in successors(s):
            new_g ← g + cost_fn(s, action, s')
            if new_g < best_cost.get(s', ∞):
                best_cost[s'] ← new_g
                parent[s'] ← (s, action)
                frontier.push(new_g, tie++, s')

    return None                       // Không có lời giải
```

**Các điểm then chốt:**

1. **Goal test khi pop** (không phải khi sinh): Đảm bảo đỉnh được lấy ra khỏi hàng đợi luôn có chi phí tối ưu, vì mọi đỉnh có chi phí thấp hơn đã được xử lý trước đó.
2. **Lazy deletion**: Thay vì cập nhật vị trí đỉnh trong heap (tốn $O(n)$), ta cho phép nhiều bản sao cùng đỉnh tồn tại trong heap. Khi pop ra một đỉnh có $g > \text{best\_cost}[s]$, ta bỏ qua vì đã xử lý bản sao tốt hơn trước đó. Cách tiếp cận này đơn giản hơn `decrease-key` và phù hợp với `heapq` của Python (không hỗ trợ `decrease-key` natively).
3. **Tính đúng đắn**: UCS luôn tìm được đường đi tối ưu khi mọi chi phí bước di chuyển dương ($c(s, a, s') \ge 1.0$).

### 3.3.4. Hàm chi phí `physics_cost`

Nhóm thiết kế hàm chi phí không đồng nhất dựa trên mô hình biến thiên thế năng trọng trường của vật rắn đồng chất kích thước $1 \times 1 \times 2$:

Khi khối nằm trên mặt phẳng, độ cao ban đầu của khối tâm (trọng tâm) là $h_0 = 0.5$.

1. **Lăn ngang (nằm → nằm):** Khối lăn quanh trục là cạnh dài $2$, thiết diện vuông $1 \times 1$. Bán kính từ trục quay đến khối tâm là $R_{\text{roll}} = \sqrt{0.5^2 + 0.5^2} = \frac{\sqrt{2}}{2} \approx 0.7071$. Độ nâng khối tâm lớn nhất đạt đỉnh quỹ đạo tròn:
   $$\Delta h_{\text{roll}} = \frac{\sqrt{2}}{2} - 0.5 = \frac{\sqrt{2} - 1}{2} \approx 0.2071 \approx 0.21$$
   Giá trị này được chuẩn hóa làm chi phí cơ sở (**baseline = $1.0$**).

2. **Dựng đứng (nằm → đứng):** Khối lật quanh trục là cạnh ngắn $1$, thiết diện chữ nhật $1 \times 2$. Bán kính từ trục quay đến khối tâm là $R_{\text{stand}} = \sqrt{0.5^2 + 1.0^2} = \frac{\sqrt{5}}{2} \approx 1.1180$. Độ nâng khối tâm lớn nhất:
   $$\Delta h_{\text{stand}} = \frac{\sqrt{5}}{2} - 0.5 = \frac{\sqrt{5} - 1}{2} \approx 0.6180 \approx 0.62$$

3. **Tỷ số công cơ học nâng thế năng:**
   $$\frac{\Delta h_{\text{stand}}}{\Delta h_{\text{roll}}} = \frac{\sqrt{5} - 1}{\sqrt{2} - 1} \approx \frac{0.6180}{0.2071} \approx 2.984 \approx 3.0$$

Bảng quy đổi chi phí hoàn chỉnh:

| Hành động | Chi phí | Công thức & Giải thích vật lý |
|---|---|---|
| Lăn ngang (nằm → nằm) | $1.0$ | $\Delta h_{\text{roll}} = \frac{\sqrt{2}-1}{2} \approx 0.21$, chọn làm chuẩn baseline. |
| Dựng đứng (nằm → đứng) | $3.0$ | $\Delta h_{\text{stand}} = \frac{\sqrt{5}-1}{2} \approx 0.62$, gấp $\approx 3\times$ baseline ($2.98 \approx 3.0$). |
| Lật xuống (đứng → nằm) | $1.0$ | Khối tâm ở độ cao $1.0$, quay quanh cạnh đáy lên bán kính đỉnh $R = \frac{\sqrt{5}}{2} \approx 1.118 \implies \Delta h \approx 0.118$ (khoảng $0.57\times$ baseline) trước khi đổ xuống. Nhóm làm tròn lên $1.0$ để duy trì $c_{\min} = 1.0$, trực tiếp bảo toàn tính chấp nhận được (admissible) cho các cận dưới $\lceil d/2 \rceil \times c_{\min}$ của heuristic A*. |
| Di chuyển khối lập phương $1\times 1$ | $1.0$ | Khối $1\times 1$ lăn quanh cạnh có $\Delta h = \frac{\sqrt{2}-1}{2} \approx 0.207$, bằng đúng baseline của bước lăn ngang khối nguyên. |

Hàm chi phí này tạo ra sự khác biệt bản chất giữa UCS và BFS: UCS sẽ **ưu tiên các đường lăn ngang** thay vì dựng đứng khi cả hai đều đi được đến đích, giúp giảm tổng hao tổn năng lượng.

### 3.3.5. Độ phức tạp

- **Thời gian:** $O(|E| \log |V|) = O(|V| \log |V|)$
  - Do sử dụng **Lazy deletion** (không dùng thao tác `decrease-key` vốn tốn kém), mỗi cạnh chuyển trạng thái $(s, a, s')$ có thể đẩy thêm một bản sao trạng thái vào MinHeap khi tìm thấy đường rẻ hơn. Kích thước tối đa của heap là $O(|E|)$, chi phí mỗi thao tác heap là $O(\log |E|) = O(\log |V|^2) = O(\log |V|)$.
  - Trong không gian trạng thái của Bloxorz, bậc ra của mỗi trạng thái luôn bị chặn trên bởi một hằng số nhỏ ($\deg(s) \le 4$ khi nguyên khối, và $\deg(s) \le 5$ khi tách thành 2 khối gồm tối đa 4 hướng lăn + 1 hành động `SWITCH`). Vì vậy, tổng số cạnh thỏa mãn $|E| \le 5|V| = O(|V|)$.
  - Do đó: $O(|E| \log |E|) = O(|V| \log |V|)$.
- **Không gian:** $O(|E|) = O(|V|)$ cho `frontier` trong trường hợp xấu nhất, và $O(|V|)$ để lưu trữ bảng `best_cost` cùng `parent`.

---

## 3.4. Thuật toán A* Search

### 3.4.1. Ý tưởng

A* là cải tiến của UCS bằng cách sử dụng hàm đánh giá:

$$f(n) = g(n) + h(n)$$

trong đó:
- $g(n)$: chi phí đường đi thực tế từ trạng thái đầu đến $n$.
- $h(n)$: **ước lượng** chi phí còn lại từ $n$ đến đích.

Nếu $h(n)$ thỏa tính chấp nhận được (admissible) — tức $h(n) \le h^*(n)$ với mọi $n$ — thì A* vẫn đảm bảo tìm đường đi tối ưu, nhưng mở ít đỉnh hơn UCS nhờ ưu tiên khám phá các đỉnh "hứa hẹn" gần đích hơn.

### 3.4.2. Khác biệt so với UCS

| Tiêu chí | UCS | A* |
|---|---|---|
| Hàm ưu tiên | $g(n)$ | $f(n) = g(n) + h(n)$ |
| Heuristic | Không cần | Cần hàm $h(n)$ admissible |
| Số đỉnh mở rộng | Nhiều hơn | Ít hơn (nhờ heuristic dẫn hướng) |
| Tính tối ưu | Luôn đảm bảo | Đảm bảo khi $h$ admissible |

Cài đặt A* của nhóm kế thừa cấu trúc từ UCS, trong đó hàng đợi ưu tiên MinHeap quản lý các trạng thái theo thứ tự tuple:

```python
# UCS: frontier lưu (g_cost, tie_breaker, state)
# A*:  frontier lưu (f_cost, g_cost, tie_breaker, state)
#      với f_cost = g_cost + heuristic(state)
```

### 3.4.3. Thuật toán

```
function A*(problem, cost_fn, heuristic):
    h₀ ← heuristic(start_state)
    frontier ← MinHeap chứa (h₀, 0.0, 0, start_state)
    best_g[start_state] ← 0.0
    parent[start_state] ← None

    while frontier ≠ ∅:
        f, g, _, s ← frontier.pop_min()

        if g > best_g[s]:             // Lazy deletion
            continue

        if is_goal(s):                // Goal test khi POP
            return reconstruct_path(parent, s)

        for (action, s') in successors(s):
            new_g ← g + cost_fn(s, action, s')
            if new_g < best_g.get(s', ∞):
                best_g[s'] ← new_g
                parent[s'] ← (s, action)
                h ← heuristic(s')
                frontier.push(new_g + h, new_g, tie++, s')

    return None
```

> [!NOTE]
> **Cơ chế Phá hòa (Tie-breaking) trong Frontier:**
> Trong Python `heapq`, khi hai trạng thái có cùng giá trị hàm đánh giá $f = g + h$, bộ so sánh tuple sẽ xét đến trường thứ hai là `g_cost`:
> 1. **Về mặt lý thuyết A\* kinh điển (Russell & Norvig - AIMA):** Khi cùng $f$, việc ưu tiên các đỉnh có **$g$ lớn hơn** (tương đương $h$ nhỏ hơn — tức đỉnh ở gần đích hơn) sẽ giúp thuật toán mở ít đỉnh hơn và đi thẳng về đích nhanh hơn. Để cài đặt theo hướng này, người ta thường lưu số đối `-g_cost` vào MinHeap.
> 2. **Trong mã nguồn thực tế:** Nhóm lưu `+g_cost` vào tuple, tức ưu tiên mở đỉnh có $g$ nhỏ hơn trước (khám phá các đường đi an toàn có chi phí thực tích lũy thấp). Cả hai cách cài đặt tie-breaking đều **đảm bảo 100% tính tối ưu nghiệm** vì $h$ thỏa mãn điều kiện admissible và consistent. Trình tự phá hòa `tie++` ở trường thứ ba đảm bảo tính ổn định (FIFO) và tránh việc Python phải so sánh trực tiếp hai đối tượng `State`.

---

## 3.5. Thiết kế và Phân tích Tính Đúng Đắn của Hàm Heuristic

### 3.5.1. Công thức Heuristic

Hàm heuristic $h(s)$ ước lượng chi phí còn lại từ trạng thái $s$ đến đích $G$:

$$h(s) = \begin{cases} 0 & \text{nếu } s \text{ là trạng thái đích} \\ \text{split\_cost}(c_1, c_2) & \text{nếu } s \text{ đang tách khối} \\ \max\!\Big(\min\!\big(h_{\text{direct}}(s, G),\; \min_{T} \big[h_{\text{direct}}(s, T) + \text{split\_cost}(\text{targets}_T)\big]\big),\; c_{\text{stand}}\Big) & \text{trường hợp còn lại} \end{cases}$$

Trong đó:

| Thành phần | Công thức | Ý nghĩa |
|---|---|---|
| $h_{\text{direct}}(s, X)$ | $\left\lceil \frac{\min_{c \in \text{cells}(s)} \text{manhattan}(c,\, X)}{2} \right\rceil \times c_{\min}$ | Cận dưới chi phí lăn khối nguyên đến ô $X$: mỗi bước lăn đi tối đa 2 ô. |
| $\text{split\_cost}(c_1, c_2)$ | $\max\!\big(\text{manhattan}(c_1, c_2) - 1,\; 0\big) \times c_{\min} + c_{\text{stand}}$ | Cận dưới chi phí để 2 khối $1\times 1$ di chuyển đến cạnh nhau (hợp nhất), sau đó dựng đứng vào đích. |
| $c_{\min}$ | $1.0$ | Chi phí bước đi tối thiểu (chung cho cả `physics_cost` và `unit_cost`). |
| $c_{\text{stand}}$ | $3.0$ (`physics_cost`) hoặc $1.0$ (`unit_cost`) | Chi phí tối thiểu của bước cuối cùng (dựng đứng trên ô đích). |

**Giải thích trực quan:**
- **Nhánh trực tiếp** $h_{\text{direct}}(s, G)$: Ước lượng chi phí đi thẳng đến đích, bỏ qua mọi chướng ngại vật và cầu.
- **Nhánh qua công tắc tách** $h_{\text{direct}}(s, T) + \text{split\_cost}(\text{targets}_T)$: Ước lượng chi phí đi đến công tắc tách $T$, rồi hai khối lập phương tìm nhau và hợp nhất.
- Lấy $\min$ giữa các nhánh: chọn con đường ước lượng rẻ nhất.
- Ép $\ge c_{\text{stand}}$: mọi trạng thái chưa phải đích đều cần ít nhất 1 bước dựng đứng.

### 3.5.2. Chứng minh Tính Chấp Nhận Được (Admissibility)

**Định nghĩa:** $h(s)$ là admissible nếu $0 \le h(s) \le h^*(s)$ với mọi $s$, trong đó $h^*(s)$ là chi phí tối ưu thật sự.

**Chứng minh:**

1. **Tại đích $G$:** $h(G) = 0 = h^*(G)$. ✓

2. **Cận dưới $c_{\text{stand}}$:** Mọi trạng thái chưa phải đích đều cần ít nhất 1 bước chuyển về đích. Bước cuối cùng buộc phải dựng khối đứng thẳng trên ô $G$, tốn tối thiểu $c_{\text{stand}}$ (3.0 với `physics_cost`, 1.0 với `unit_cost`). Nên $h^*(s) \ge c_{\text{stand}}$, và vì $h(s) \ge c_{\text{stand}}$ bởi phép $\max$, điều này không vi phạm.

3. **Cận dưới khoảng cách:** Khối $1\times 1\times 2$ lăn tối đa 2 ô mỗi bước, nên $\lceil d/2 \rceil \times c_{\min}$ luôn $\le$ chi phí thực tế. Khối $1\times 1$ di chuyển 1 ô/bước nên $\max(\text{manhattan} - 1, 0) \times c_{\min}$ cũng là cận dưới.

4. **Phép $\min$ bảo toàn admissibility:** $h_{\text{direct}}(s, G) \le h^*(s)$ (đường thẳng luôn $\le$ đường thực tế qua chướng ngại vật). Tương tự, chi phí qua $T$ cũng là cận dưới vì bỏ qua chướng ngại vật. Lấy $\min$ của nhiều cận dưới vẫn là cận dưới.

**Kiểm chứng thực nghiệm:** Sử dụng Dijkstra ngược (multi-source backward Dijkstra từ mọi trạng thái đích) để tính $h^*(s)$ chính xác cho mọi trạng thái $s$ có thể chạm tới. Kiểm tra trên toàn bộ 16 màn: **0 trạng thái vi phạm** $h(s) > h^*(s)$ trên cả `physics_cost` và `unit_cost`.

### 3.5.3. Chứng minh Tính Nhất Quán (Consistency / Monotonicity)

**Định nghĩa:** $h(s)$ là consistent (monotone) nếu với mọi bước chuyển $s \xrightarrow{a} s'$:
$$h(s) \le c(s, a, s') + h(s'), \quad \text{và}\quad h(G) = 0$$

Tương đương: $h(s) - h(s') \le c(s, a, s')$ — heuristic không giảm quá nhanh so với chi phí thực.

**Chứng minh qua toàn bộ 5 lớp bước chuyển trong Bloxorz:**

**1. Lăn khối nguyên (Non-split → Non-split):**
- Lăn khối $1\times 1\times 2$ thay đổi khoảng cách Manhattan tối thiểu đến bất kỳ ô mục tiêu $X$ nào tối đa 2 ô ($\Delta d \le 2$).
- Do đó, $\lceil \text{dist}(s, X) / 2 \rceil$ giảm tối đa 1 mỗi bước lăn.
- Mỗi nhánh ứng viên trong $h(s)$ giảm tối đa $c_{\min} \le c(s, a, s')$. Vì toán tử $\min/\max$ bảo toàn cận trên của hiệu, ta có $h(s) - h(s') \le c_{\min}$.
- Trường hợp đặc biệt vào đích ($s' = G$): Bước cuối bắt buộc dựng đứng nên $c(s, a, G) \ge c_{\text{stand}}$. Tại 1 bước cách đích, $h(s) = c_{\text{stand}}$ và $h(G) = 0$, cho $h(s) - h(G) = c_{\text{stand}} \le c(s, a, G)$. ✓

**2. Kích hoạt công tắc tách (Non-split $s$ → Split $s'$ qua lăn đứng lên $T$):**
- Bước lăn đứng lên $T$ chỉ xảy ra khi khối ở đủ gần nên $h_{\text{direct}}(s, T) \le c(s, a, s')$.
- Khi đứng trên $T$, khối bị tách đến vị trí cố định $(t_1, t_2)$, nên $h(s') = \text{split\_cost}((t_1, t_2))$.
- Vì $h_{\text{direct}}(s, T) + \text{split\_cost}((t_1, t_2))$ là một trong các nhánh ứng viên trong phép $\min(.)$ định nghĩa $h(s)$:
$$h(s) \le h_{\text{direct}}(s, T) + h(s') \implies h(s) - h(s') \le h_{\text{direct}}(s, T) \le c(s, a, s'). \;\checkmark$$

**3. Di chuyển một khối lập phương (Split $s$ → Split $s'$):**
- Một khối $1\times 1$ di chuyển 1 ô với chi phí $c(s, a, s') = c_{\min}$, thay đổi khoảng cách Manhattan giữa 2 khối tối đa 1 ô.
- Dưới heuristic nới lỏng $h(s) = \max(|c_1 - c_2| - 1, 0) \times c_{\min} + c_{\text{stand}}$ (cố ý nới lỏng khoảng cách đến đích để bảo toàn tính đơn điệu), $h(s)$ giảm tối đa $1 \times c_{\min} = c_{\min} = c(s, a, s')$. ✓

**4. Hợp nhất khối (Split $s$ → Merged Non-split $s'$):**
- Theo luật trò chơi (`docs/SPECIAL_TILES.md` §4.4), hai khối lập phương tự động hợp nhất thành khối nằm $1\times 1\times 2$ ngay khi vừa trở thành kề nhau; việc lăn đè lên khối kia là nước đi phạm quy (§4.5).
- Do đó, ngay trước bước ghép, khoảng cách Manhattan giữa hai khối luôn là $|c_1 - c_2| = 2$.
- Khi đó: $h(s) = \max(2 - 1, 0) \times c_{\min} + c_{\text{stand}} = c_{\min} + c_{\text{stand}}$.
- Khối sau khi hợp nhất là trạng thái nằm $s'$ (chưa thể là đích $G$ vì vào đích buộc phải đứng), do đó $h(s') \ge c_{\text{stand}}$.
- Suy ra:
$$h(s) - h(s') \le (c_{\min} + c_{\text{stand}}) - c_{\text{stand}} = c_{\min} \le c(s, a, s'). \;\checkmark$$

**5. Chuyển khối điều khiển (Split $s$ → Split $s'$ qua `Action.SWITCH`):**
- Hành động đổi khối điều khiển chiếm 28,652 / 123,355 cạnh của đồ thị. Hành động này chỉ thay đổi chỉ số khối được chọn điều khiển, vị trí tọa độ của cả 2 khối hoàn toàn giữ nguyên.
- Do hàm `split_cost` chỉ phụ thuộc vào khoảng cách Manhattan giữa hai khối $|c_1 - c_2|$, giá trị heuristic không đổi: $h(s') = h(s)$.
- Suy ra:
$$h(s) - h(s') = 0 \le c(s, a, s'). \;\checkmark$$

**Kiểm chứng thực nghiệm toàn diện:** Quét kiểm tra toàn bộ 123,355 cạnh chuyển trạng thái có thể đạt tới (reachable transition edges, bao gồm 28,652 bước `Action.SWITCH`) trên cả 16 màn chính thức: **0 cạnh vi phạm** bất đẳng thức tam giác $h(s) \le c(s, a, s') + h(s')$ trên cả `physics_cost` và `unit_cost`.

> [!IMPORTANT]
> **Ý nghĩa của tính nhất quán (consistent):** Với heuristic consistent, A* đảm bảo rằng mỗi đỉnh khi được pop ra khỏi hàng đợi ưu tiên thì $g(n)$ đã là tối ưu, nên **không bao giờ cần cập nhật lại** (re-open) bất kỳ đỉnh nào. Điều này mạnh hơn chỉ admissible, giúp A* chạy hiệu quả hơn.

---

## 3.6. Đánh Giá Thực Nghiệm UCS vs A*

### 3.6.1. So sánh số đỉnh mở rộng

#### Với `physics_cost` ($c_{\text{stand}} = 3.0$):

| Màn | UCS (đỉnh mở) | A* (đỉnh mở) | Chi phí ($g^*$) | Bước | Giảm |
|---|---:|---:|---:|---:|---:|
| g1_basic_01 | 44 | 37 | 12.0 | 8 | 15.9% |
| g1_basic_02 | 61 | 56 | 20.0 | 12 | 8.2% |
| g1_basic_03 | 89 | 60 | 13.0 | 9 | 32.6% |
| g1_basic_04 | 40 | 37 | 29.0 | 19 | 7.5% |
| g2_fragile_01 | 99 | 93 | 23.0 | 17 | 6.1% |
| g2_fragile_02 | 49 | 43 | 31.0 | 19 | 12.2% |
| g2_fragile_03 | 94 | 87 | 38.0 | 24 | 7.4% |
| g2_fragile_04 | 106 | 104 | 46.0 | 30 | 1.9% |
| g3_switch_01 | 203 | 187 | 29.0 | 15 | 7.9% |
| g3_switch_02 | 130 | 95 | 24.0 | 14 | 26.9% |
| g3_switch_03 | 374 | 309 | 42.0 | 24 | 17.4% |
| g3_switch_04 | 333 | 281 | 40.0 | 24 | 15.6% |
| g4_combined_01 | 1,816 | 357 | 22.0 | 12 | **80.3%** |
| g4_combined_02 | 4,641 | 4,552 | 39.0 | 29 | 1.9% |
| g4_combined_03 | 6,932 | 4,649 | 33.0 | 25 | 32.9% |
| g4_combined_04 | 13,405 | 11,315 | 45.0 | 31 | 15.6% |
| **Tổng cộng** | **28,416** | **22,262** | — | — | **21.7%** |

*(Ghi chú: UCS và A* tìm ra kết quả đồng nhất cả về tổng chi phí tối ưu $g^*$ lẫn số bước đi trên mọi màn).*

#### Với `unit_cost` ($c_{\text{stand}} = 1.0$):

| Màn | UCS (đỉnh mở) | A* (đỉnh mở) | Chi phí ($g^*$) | Bước | Giảm |
|---|---:|---:|---:|---:|---:|
| g1_basic_01 | 44 | 37 | 8.0 | 8 | 15.9% |
| g1_basic_02 | 62 | 52 | 12.0 | 12 | 16.1% |
| g1_basic_03 | 84 | 47 | 8.0 | 8 | **44.0%** |
| g1_basic_04 | 40 | 40 | 19.0 | 19 | 0.0% |
| g2_fragile_01 | 101 | 96 | 16.0 | 16 | 5.0% |
| g2_fragile_02 | 45 | 41 | 19.0 | 19 | 8.9% |
| g2_fragile_03 | 93 | 85 | 24.0 | 24 | 8.6% |
| g2_fragile_04 | 105 | 104 | 30.0 | 30 | 1.0% |
| g3_switch_01 | 180 | 121 | 15.0 | 15 | 32.8% |
| g3_switch_02 | 125 | 72 | 14.0 | 14 | **42.4%** |
| g3_switch_03 | 342 | 263 | 24.0 | 24 | 23.1% |
| g3_switch_04 | 329 | 249 | 23.0 | 23 | 24.3% |
| g4_combined_01 | 360 | 83 | 12.0 | 12 | **76.9%** |
| g4_combined_02 | 4,627 | 3,594 | 29.0 | 29 | 22.3% |
| g4_combined_03 | 5,544 | 3,822 | 25.0 | 25 | 31.1% |
| g4_combined_04 | 11,563 | 8,129 | 31.0 | 31 | 29.7% |
| **Tổng cộng** | **23,644** | **16,835** | — | — | **28.8%** |

### 3.6.2. Nhận xét

1. **Tính tối ưu tuyệt đối về chi phí:** Trên toàn bộ 16 màn, A* luôn tìm được lời giải có **cùng tổng chi phí tối ưu $g^*$** (và khớp hoàn toàn số bước) với UCS. Đây là hệ quả trực tiếp của tính admissible và consistent đã được chứng minh chặt chẽ cả trên lý thuyết lẫn qua kiểm chứng thực nghiệm 123,355 cạnh.

2. **Minh chứng thực nghiệm cho hiệu ứng của `physics_cost`:** So sánh chéo giữa hai bảng thực nghiệm, tại 3 màn `g1_basic_03`, `g2_fragile_01` và `g3_switch_04`, số bước trong lời giải tối ưu của `physics_cost` dài hơn `unit_cost` đúng 1 bước:
   - Ở `g1_basic_03`: `unit_cost` đi 8 bước (tiêu tốn $14.0$ nếu quy đổi theo physics cost), trong khi `physics_cost` đi 9 bước (chỉ tốn $13.0$).
   - Ở `g2_fragile_01`: `unit_cost` đi 16 bước (tiêu tốn $24.0$ physics cost), trong khi `physics_cost` đi 17 bước (chỉ tốn $23.0$).
   - Ở `g3_switch_04`: `unit_cost` đi 23 bước (tiêu tốn $41.0$ physics cost), trong khi `physics_cost` đi 24 bước (chỉ tốn $40.0$).
   Thuật toán UCS và A* đã chủ động chọn đường lăn ngang dài hơn 1 bước nhằm triệt tiêu bớt một bước dựng đứng tốn kém (chi phí $3.0$). Minh chứng thực tế này khẳng định hàm `physics_cost` đã thay đổi hành vi tìm kiếm theo đúng mô hình tối ưu năng lượng cơ học đã đề ra ở mục 3.3.4.

3. **Hiệu quả tìm kiếm:** A* giảm trung bình **21.7%** số đỉnh mở rộng so với UCS trên `physics_cost` và **28.8%** trên `unit_cost`. Heuristic phát huy hiệu quả mạnh nhất trên các màn có không gian trạng thái phức tạp và phân nhánh rộng:
   - `g4_combined_01`: giảm tới **80.3%** (physics) / **76.9%** (unit) — heuristic cắt tỉa gần như toàn bộ các nhánh đi chệch hướng khỏi mục tiêu.
   - `g3_switch_02`: giảm **26.9%** (physics) / **42.4%** (unit) — heuristic dẫn hướng hiệu quả qua các cây cầu và công tắc.

4. **Trường hợp heuristic ít cải thiện:** Trên các màn có địa hình hành lang hẹp hoặc bắt buộc chỉ có một con đường hợp lệ duy nhất:
   - `g2_fragile_04`: chỉ giảm 1.9% (physics) — bản đồ dài và hẹp, hầu hết các trạng thái sinh ra đều thuộc về tuyến đường khả dĩ duy nhất.
   - `g1_basic_04`: giảm 0.0% (unit) — không gian không có nhánh cụt dư thừa để cắt tỉa.

---

## 3.7. Ưu điểm và Nhược điểm

### UCS
| Ưu điểm | Nhược điểm |
|---|---|
| Đảm bảo tối ưu với mọi hàm chi phí dương. | Không có dẫn hướng, mở rộng đều theo mọi hướng ("tìm kiếm mù"). |
| Cài đặt đơn giản, không cần heuristic. | Mở nhiều đỉnh không cần thiết trên bản đồ lớn. |
| Hoạt động đúng ngay cả khi chi phí không đồng nhất. | Hiệu suất kém hơn A* khi có heuristic tốt. |

### A*
| Ưu điểm | Nhược điểm |
|---|---|
| Giảm đáng kể số đỉnh mở rộng so với UCS (trung bình 21–29%). | Cần thiết kế heuristic chặt chẽ: sai sẽ mất tính tối ưu. |
| Vẫn đảm bảo tính tối ưu nhờ heuristic admissible + consistent. | Heuristic dựa trên Manhattan distance nên ít hiệu quả trên bản đồ hẹp, dài, hoặc bản đồ có nhiều cầu (khoảng cách Manhattan bị biến dạng do cầu đóng/mở làm gián đoạn đường đi thực tế). |
| Heuristic consistent → không bao giờ re-open đỉnh → hiệu quả bộ nhớ. | Trên bản đồ nhỏ (< 100 đỉnh), chi phí tính heuristic có thể không bù được lợi ích cắt tỉa. |
| Trên bản đồ lớn (g4), tiết kiệm tới 80% số đỉnh mở rộng. | Cần điều chỉnh tham số $c_{\text{stand}}$ theo hàm chi phí (đã tự động hóa). |
