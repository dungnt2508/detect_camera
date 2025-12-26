"""
State Machine
Quản lý trạng thái hệ thống: IDLE, BROWSE_ITEM, TRY_ON
Quyết định gesture nào hợp lệ trong từng state
"""
from enum import Enum


import time


class SystemState(Enum):
    IDLE = "IDLE"
    BROWSE_ITEM = "BROWSE_ITEM"
    TRY_ON = "TRY_ON"


class StateMachine:
    def __init__(self, idle_timeout=10.0):
        self.current_state = SystemState.IDLE
        self.transition_history = []
        self.last_activity_time = time.time()
        self.idle_timeout = idle_timeout
        self.last_transition_time = 0
        self.transition_cooldown = 1.5  # Giây - không cho phép chuyển state quá nhanh
    
    def get_state(self):
        """Lấy trạng thái hiện tại"""
        return self.current_state
    
    def update_activity(self):
        """Cập nhật thời gian hoạt động cuối cùng"""
        self.last_activity_time = time.time()
    
    def check_timeout(self):
        """
        Kiểm tra nếu hệ thống không có hoạt động quá lâu thì về IDLE
        Returns:
            bool: True nếu vừa có transition về IDLE
        """
        if self.current_state != SystemState.IDLE:
            if time.time() - self.last_activity_time > self.idle_timeout:
                print(f"Timeout! Tự động quay về IDLE sau {self.idle_timeout}s")
                self.transition_to(SystemState.IDLE)
                return True
        return False

    def transition_to(self, new_state):
        """
        Chuyển sang trạng thái mới
        Args:
            new_state: SystemState enum
        """
        if new_state != self.current_state:
            current_time = time.time()
            # Kiểm tra cooldown - không cho phép chuyển state quá nhanh
            if current_time - self.last_transition_time < self.transition_cooldown:
                return  # Bỏ qua transition nếu chưa đủ cooldown
            
            print(f"State transition: {self.current_state.value} -> {new_state.value}")
            self.transition_history.append({
                'from': self.current_state,
                'to': new_state,
                'time': current_time
            })
            self.current_state = new_state
            self.last_transition_time = current_time
            self.update_activity()
    
    def is_gesture_valid(self, gesture):
        """
        Kiểm tra gesture có hợp lệ trong state hiện tại không
        Args:
            gesture: str (SWIPE_LEFT, SWIPE_RIGHT, PINCH, HOLD)
        Returns:
            bool
        """
        if gesture is None:
            return False
        
        # Luôn cho phép PINCH/HOLD để tương tác bất kỳ lúc nào
        if gesture in ['PINCH', 'HOLD']:
            return True
            
        # Các gesture khác tùy thuộc vào state
        if self.current_state == SystemState.IDLE:
            return False # IDLE chỉ nhận pinch/hold để start
            
        return gesture in ['SWIPE_LEFT', 'SWIPE_RIGHT']
    
    def handle_gesture(self, gesture):
        """
        Xử lý gesture và chuyển state nếu cần
        Args:
            gesture: str
        Returns:
            tuple: (is_valid, should_emit_event)
        """
        self.update_activity()
        
        if not self.is_gesture_valid(gesture):
            return False, False
        
        # Logic chuyển state
        if gesture == 'PINCH' or gesture == 'HOLD':
            if self.current_state == SystemState.IDLE:
                self.transition_to(SystemState.BROWSE_ITEM)
                return True, True
            elif self.current_state == SystemState.BROWSE_ITEM:
                self.transition_to(SystemState.TRY_ON)
                return True, True
            elif self.current_state == SystemState.TRY_ON:
                # Khi ở TRY_ON, PINCH/HOLD không chuyển state nữa
                # Chỉ emit gesture event để frontend xử lý (ví dụ: remove item, confirm)
                # Không chuyển về BROWSE để tránh noise
                return True, True
        
        # SWIPE chỉ dùng để đổi item, không đổi state
        return True, True
    
    def reset(self):
        """Reset về IDLE"""
        self.transition_to(SystemState.IDLE)
        self.transition_history.clear()

