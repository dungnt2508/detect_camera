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
        self.gesture_cooldown = 0.5  # Giây - cooldown giữa các gesture
        self.gesture_cooldown = 0.3  # Giây giữa các gesture
    
    def detect_swipe(self):
        """
        Detect swipe gesture
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
        
        # Xác định hướng (ưu tiên ngang hơn dọc)
        if abs(vx) > abs(vy):
            if vx < -0.1:  # Chuyển động sang trái
                return 'SWIPE_LEFT'
            elif vx > 0.1:  # Chuyển động sang phải
                return 'SWIPE_RIGHT'
        
        return None
    
    def detect_pinch(self, hand_landmarks):
        """
        Detect pinch gesture (thumb và index gần nhau)
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
        
        if distance < self.PINCH_DISTANCE_THRESHOLD:
            return 'PINCH'
        
        return None
    
    def detect_hold(self, hand_landmarks, current_time):
        """
        Detect hold gesture (giữ tay ở một vị trí)
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
                if var_x < 0.001 and var_y < 0.001:
                    return 'HOLD'
        
        return None
    
    def process(self, hand_landmarks, current_time=None):
        """
        Xử lý và detect tất cả gestures
        Nhận motion features đã được tính từ motion layer
        Returns:
            str: gesture name hoặc None
        """
        if hand_landmarks is None:
            return None
        
        # Kiểm tra cooldown
        if current_time is not None:
            last_time = self.last_gesture_time.get('last', 0)
            if current_time - last_time < self.gesture_cooldown:
                return None
        
        # Priority: PINCH > SWIPE > HOLD
        pinch = self.detect_pinch(hand_landmarks)
        if pinch:
            if current_time is not None:
                self.last_gesture_time['last'] = current_time
            return pinch
        
        swipe = self.detect_swipe()
        if swipe:
            if current_time is not None:
                self.last_gesture_time['last'] = current_time
            return swipe
        
        hold = self.detect_hold(hand_landmarks, current_time)
        if hold:
            # Hold không cần cooldown vì là continuous
            return hold
        
        return None

