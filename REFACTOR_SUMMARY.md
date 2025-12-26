# Tóm Tắt Refactor & Tối Ưu Hóa

## Các Vấn Đề Đã Được Fix (Theo Audit Report)

### ✅ 1. Perception Threading Bottleneck (CRITICAL)
**Vấn đề**: `ThreadPoolExecutor(max_workers=1)` tạo queue, gây latency tích lũy khi frame processing vượt quá inter-frame arrival time.

**Giải pháp**:
- Thêm **frame dropping** trong `main.py`: Bỏ qua frame mới nếu executor đang busy
- Thêm tracking `dropped_frames` để monitor
- Log mỗi 30 frames dropped để debug

**File thay đổi**: `main.py`
- Thêm `self.dropped_frames = 0`
- Logic: Chỉ xử lý frame mới nếu `perception_task` đã done, nếu không thì drop frame

### ✅ 2. Partial Smoothing & Jitter (CRITICAL)
**Vấn đề**: `OneEuroFilter` chỉ áp dụng cho finger cursor. Neck anchors, face rotation, và pinch landmarks là raw data → gây jitter.

**Giải pháp**:
- Thêm các OneEuroFilter riêng cho:
  - **Neck anchor** (X, Y): `neck_anchor_filter` với `min_cutoff=0.3, beta=0.005`
  - **Face rotation**: `rotation_filter` với `min_cutoff=0.4, beta=0.01`
  - **Face scale**: `scale_filter` với `min_cutoff=0.2, beta=0.005`

**File thay đổi**: 
- `normalize.py`: Thêm 3 filter mới và các methods `smooth_neck_anchor()`, `smooth_rotation()`, `smooth_scale()`
- `main.py`: Áp dụng smoothing cho tất cả transform data trong TRY_ON state

### ✅ 3. Heuristic Collision & Determinism (CRITICAL)
**Vấn đề**: Gesture detection dựa trên threshold đơn giản, thiếu confidence/hysteresis → nhạy cảm với noise.

**Giải pháp**:
- **Hysteresis**: Thêm frame-counter buffer (3 frames)
  - Gesture phải được detect trong **3 frames liên tiếp** mới được emit
  - Reset buffer khi gesture không được detect
- **Confidence Scoring**: 
  - **PINCH**: Confidence dựa trên distance (1.0 = rất chắc, 0.5 = ngưỡng)
  - **SWIPE**: Confidence dựa trên velocity magnitude và distance (>= 60%)
  - **HOLD**: Confidence dựa trên variance (>= 70%)

**File thay đổi**: `gesture.py`
- Thêm `HYSTERESIS_FRAMES = 3`
- Thêm `gesture_buffer` để track frame count
- Cải thiện `detect_pinch()`, `detect_swipe()`, `detect_hold()` với confidence scoring
- Cập nhật `process()` để implement hysteresis logic

### ✅ 4. Performance Optimization
**Cải thiện**:
- Confidence-based filtering giảm false positives
- Hysteresis giảm flicker và noise
- Frame dropping đảm bảo realtime performance

## Kết Quả Mong Đợi

1. **Latency**: Không còn latency tích lũy nhờ frame dropping
2. **Jitter**: Giảm đáng kể visual vibration trong try-on mode
3. **Gesture Accuracy**: Tăng độ chính xác và giảm false positives nhờ hysteresis + confidence
4. **Realtime Performance**: Duy trì ổn định ngay cả khi processing chậm

## Các Vấn Đề Chưa Fix (Theo 14-Day & 30-Day Sprint)

### 14-Day Sprint (Chưa thực hiện)
- Logic Migration: Move StateMachine sang dedicated service
- Protocol Design: Standardize message schema

### 30-Day Sprint (Chưa thực hiện)
- Security: JWT/Token handshake cho WebSocket
- Auto-Calibration: Home state để calibrate user range và screen dimensions

## Testing Recommendations

1. Test frame dropping: Chạy với camera resolution cao để trigger frame drops
2. Test smoothing: So sánh jitter trước/sau khi apply full-point smoothing
3. Test hysteresis: Thử các gesture nhanh để verify không có false positives
4. Test confidence: Thử gesture ở các điều kiện ánh sáng khác nhau

