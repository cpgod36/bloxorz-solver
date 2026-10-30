# Bloxorz Solver

## Requirements

- Python 3.10+

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Tests

```bash
python -m pytest tests
```

## Tutorial 
### Giao diện chính
Gồm 4 phần chính:
- Bảng điều khiển màn
- Bảng các nút solve bằng thuật toán đã nêu
- Bảng thông số các thuật toán khi giải
- Bảng hướng dẫn sơ bộ điều khiển

### Cách chơi
**Điều khiển:** Dùng WASD hoặc cách phím mũi tên để di chuyển khối, dùng các nút solver để giải bằng các thuật toán cùng tên

**Luật chơi:**
- Không được làm khối rơi khỏi platform:
  - Khối chênh khỏi khối gạch 1 ô
  - Khối trực tiếp lăn ra khỏi platform
- Thắng màn chơi khi điều khiển được khối rơi vào ô gạch rỗng có màu xanh ở trong
- Đối với các loại gạch và các nút đặc biệt: Sẽ được demo chi tiết trong video
- Khi thua thì phải bấm nút restart để bắt đầu lại màn chơi

### Video demo
**Link youtube:** https://youtu.be/Mz166a4SrWQ

