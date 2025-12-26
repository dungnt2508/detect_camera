"""
Gesture Layer
Nhận chuỗi feature theo thời gian từ motion layer
Phát event rời rạc: SWIPE_LEFT, SWIPE_RIGHT, PINCH, HOLD
Không biết UI, không biết item
"""
import numpy as np


class GestureDetector:
    def __init__(self, motion_extractor):
        """
        Args:
            motion_extractor: MotionFeatureExtractor instance từ motion layer
        """
        self.motion_extractor = motion_extractor
        
        # Thresholds
        self.SWIPE_VELOCITY_THRESHOLD = 0.3  # Tốc độ tối thiểu cho swipe
        self.SWIPE_DISTANCE_THRESHOLD = 0.15  # Khoảng cách tối thiểu
        self.PINCH_DISTANCE_THRESHOLD = 0.04  # Khoảng cách thumb-index cho pinch
        self.HOLD_TIME_THRESHOLD = 1.0  # Giây để hold
        
        # State tracking
        self.last_gesture_time = {}
        self.gesture_cooldown = 0.3  # Giây giữa các gesture
        
        # Hysteresis: Frame-counter buffer để tránh flicker
        # Gesture phải được detect trong N frames liên tiếp mới được emit
        self.HYSTERESIS_FRAMES = 3
        self.gesture_buffer = {}  # {gesture_name: frame_count}
    
    def detect_swipe(self):
        """
        Detect swipe gesture với confidence scoring
        Returns:
            str: 'SWIPE_LEFT', 'SWIPE_RIGHT', hoặc None
        """
        velocity = self.motion_extractor.get_velocity()
        if velocity is None:
            return None
        
        vx, vy, magnitude = velocity
        
        # Kiểm tra velocity threshold
        if magnitude < self.SWIPE_VELOCITY_THRESHOLD:
            return None
        
        # Kiểm tra distance threshold
        distance = self.motion_extractor.get_distance(start_idx=-10, end_idx=-1)
        if distance is None or distance < self.SWIPE_DISTANCE_THRESHOLD:
            return None
        
        # Confidence: dựa trên velocity magnitude và distance
        # Velocity càng cao, distance càng xa = confidence càng cao
        velocity_confidence = min(1.0, magnitude / (self.SWIPE_VELOCITY_THRESHOLD * 2))
        distance_confidence = min(1.0, distance / (self.SWIPE_DISTANCE_THRESHOLD * 2))
        overall_confidence = (velocity_confidence + distance_confidence) / 2
        
        # Chỉ accept nếu confidence >= 60%
        if overall_confidence < 0.6:
            return None
        
        # Xác định hướng (ưu tiên ngang hơn dọc)
        if abs(vx) > abs(vy):
            if vx < -0.1:  # Chuyển động sang trái
                return 'SWIPE_LEFT'
            elif vx > 0.1:  # Chuyển động sang phải
                return 'SWIPE_RIGHT'
        
        return None
    
    def detect_pinch(self, hand_landmarks):
        """
        Detect pinch gesture (thumb và index gần nhau) với confidence
        Args:
            hand_landmarks: np.array shape (21, 3)
        Returns:
            str: 'PINCH' hoặc None
        """
        if hand_landmarks is None or len(hand_landmarks) < 9:
            return None
        
        # Landmark 4: thumb tip, 8: index tip
        thumb_tip = hand_landmarks[4]
        index_tip = hand_landmarks[8]
        
        distance = np.linalg.norm(thumb_tip[:3] - index_tip[:3])
        
        # Confidence: càng gần threshold càng thấp confidence
        # Distance < 0.02: confidence cao, 0.02-0.04: confidence trung bình
        if distance < self.PINCH_DISTANCE_THRESHOLD:
            # Tính confidence (1.0 = rất chắc chắn, 0.5 = ngưỡng)
            confidence = 1.0 - (distance / self.PINCH_DISTANCE_THRESHOLD) * 0.5
            if confidence >= 0.5:  # Chỉ accept nếu confidence >= 50%
                return 'PINCH'
        
        return None
    
    def detect_hold(self, hand_landmarks, current_time):
        """
        Detect hold gesture (giữ tay ở một vị trí) với confidence
        Args:
            hand_landmarks: np.array shape (21, 3)
            current_time: timestamp
        Returns:
            str: 'HOLD' hoặc None
        """
        if hand_landmarks is None:
            return None
        
        # Kiểm tra velocity thấp
        velocity = self.motion_extractor.get_velocity()
        if velocity is None:
            return None
        
        vx, vy, magnitude = velocity
        
        # Velocity rất thấp = đang giữ
        if magnitude < 0.05:
            # Kiểm tra thời gian giữ
            if len(self.motion_extractor.position_history) >= 10:
                # Tính variance của vị trí
                positions = list(self.motion_extractor.position_history)[-10:]
                positions_x = [p[0] for p in positions]
                positions_y = [p[1] for p in positions]
                
                var_x = np.var(positions_x)
                var_y = np.var(positions_y)
                
                # Variance thấp = giữ yên
                # Confidence: variance càng thấp, confidence càng cao
                max_variance = 0.001
                var_confidence_x = 1.0 - min(1.0, var_x / max_variance)
                var_confidence_y = 1.0 - min(1.0, var_y / max_variance)
                overall_confidence = (var_confidence_x + var_confidence_y) / 2
                
                # Chỉ accept nếu confidence >= 70% (hold cần chắc chắn hơn)
                if var_x < 0.001 and var_y < 0.001 and overall_confidence >= 0.7:
                    return 'HOLD'
        
        return None
    
    def process(self, hand_landmarks, current_time=None):
        """
        Xử lý và detect tất cả gestures với hysteresis
        Nhận motion features đã được tính từ motion layer
        Returns:
            str: gesture name hoặc None
        """
        if hand_landmarks is None:
            # Reset buffer khi không có hand
            self.gesture_buffer.clear()
            return None
        
        # Kiểm tra cooldown
        if current_time is not None:
            last_time = self.last_gesture_time.get('last', 0)
            if current_time - last_time < self.gesture_cooldown:
                return None
        
        # Detect tất cả gestures
        detected_gestures = []
        
        # Priority: PINCH > SWIPE > HOLD
        pinch = self.detect_pinch(hand_landmarks)
        if pinch:
            detected_gestures.append(pinch)
        
        swipe = self.detect_swipe()
        if swipe:
            detected_gestures.append(swipe)
        
        hold = self.detect_hold(hand_landmarks, current_time)
        if hold:
            detected_gestures.append(hold)
        
        # Hysteresis: Cập nhật buffer cho các gestures được detect
        # Reset buffer cho gestures không được detect
        for gesture_name in ['PINCH', 'SWIPE_LEFT', 'SWIPE_RIGHT', 'HOLD']:
            if gesture_name in detected_gestures:
                self.gesture_buffer[gesture_name] = self.gesture_buffer.get(gesture_name, 0) + 1
            else:
                # Reset counter nếu gesture không được detect
                if gesture_name in self.gesture_buffer:
                    self.gesture_buffer[gesture_name] = 0
        
        # Chỉ emit gesture nếu đã được detect trong N frames liên tiếp
        for gesture_name in ['PINCH', 'SWIPE_LEFT', 'SWIPE_RIGHT', 'HOLD']:
            if gesture_name in self.gesture_buffer:
                if self.gesture_buffer[gesture_name] >= self.HYSTERESIS_FRAMES:
                    # Reset buffer sau khi emit
                    self.gesture_buffer[gesture_name] = 0
                    if current_time is not None:
                        self.last_gesture_time['last'] = current_time
                    return gesture_name
        
        return None

