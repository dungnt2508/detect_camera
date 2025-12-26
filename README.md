# Camera Detect - Touchless Interaction System

Hệ thống tương tác không chạm bằng camera theo kiến trúc phân tầng rõ ràng.

## Kiến trúc

Hệ thống được xây dựng theo kiến trúc 8 tầng:

1. **Sensor Layer** (`camera.py`) - Đọc frame từ camera
2. **Perception Layer** (`perception.py`) - MediaPipe detection (Hands, Face, Pose)
3. **Normalization Layer** (`normalize.py`) - Normalize coordinates + smoothing
4. **Motion Feature Layer** (`motion.py`) - Tính toán velocity, distance, direction
5. **Gesture Layer** (`gesture.py`) - Detect gesture (SWIPE, PINCH, HOLD)
6. **State Machine** (`state.py`) - Quản lý trạng thái (IDLE, BROWSE_ITEM, TRY_ON)
7. **Bridge Layer** (`bridge.py`) - WebSocket emit events
8. **Frontend Renderer** (`frontend/index.html`) - HTML Canvas renderer

## Cài đặt

### 1. Kích hoạt virtual environment

```bash
# Windows
Env3_9\Scripts\activate

# Linux/Mac
source Env3_9/bin/activate
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

## Chạy hệ thống

### 1. Khởi động backend

```bash
python main.py
```

Backend sẽ:
- Khởi tạo camera
- Khởi động WebSocket server tại `ws://localhost:8765`
- Khởi động HTTP video stream tại `http://localhost:9000/video`
- Bắt đầu xử lý frame và emit events

### 2. Mở frontend

Mở file `frontend/index.html` trong trình duyệt (hoặc dùng local server):

```bash
# Python 3
cd frontend
python -m http.server 8000
```

Sau đó truy cập: `http://localhost:8000`

## Cách sử dụng

1. **IDLE State**: Đưa tay vào camera, thực hiện PINCH hoặc HOLD để bắt đầu
2. **BROWSE_ITEM State**: 
   - Di chuyển tay để điều khiển cursor
   - SWIPE_LEFT/SWIPE_RIGHT để đổi item
   - PINCH/HOLD để chọn item
3. **TRY_ON State**:
   - Sản phẩm sẽ được gắn lên cổ
   - Xoay đầu để xem sản phẩm
   - Vẫn có thể dùng hand gesture để đổi item, remove, confirm

## Events

Backend emit các events sau qua WebSocket:

- `CURSOR_MOVE`: Vị trí cursor (x, y)
- `GESTURE`: Gesture event (SWIPE_LEFT, SWIPE_RIGHT, PINCH, HOLD)
- `ITEM_TRANSFORM`: Transform cho try-on (anchor, rotation, scale)
- `STATE_CHANGE`: Thay đổi state (IDLE, BROWSE_ITEM, TRY_ON)

## Cấu trúc project

```
.
├── camera.py              # Sensor Layer
├── perception.py          # Perception Layer
├── normalize.py           # Normalization Layer
├── motion.py              # Motion Feature Layer
├── gesture.py            # Gesture Layer
├── state.py              # State Machine
├── bridge.py             # Bridge Layer
├── main.py               # Main loop
├── frontend/
│   └── index.html        # Frontend renderer
├── requirements.txt      # Dependencies
└── README.md            # Documentation
```

## Nguyên tắc kiến trúc

- Không gộp nhiều tầng logic vào cùng một file
- Backend chỉ phát EVENT, không phát ý định UI
- Frontend chỉ phản ứng theo type, không đoán
- Mỗi event = 1 hành động logic, không gộp
- Không fake mouse, không DOM animation
- Ưu tiên đúng kiến trúc hơn đẹp code

