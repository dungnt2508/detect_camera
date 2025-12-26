"""
Normalization Layer
Chuyển normalized coordinates → pixel space
Smoothing, debounce
Không có gesture, không có UI
"""
import numpy as np
from collections import deque


import numpy as np
import time


class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0, freq=30):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.freq = freq
        self.x_prev = None
        self.dx_prev = None

    def _low_pass_filter(self, x, x_prev, alpha):
        if x_prev is None:
            return x
        return alpha * x + (1 - alpha) * x_prev

    def _alpha(self, cutoff):
        tau = 1.0 / (2 * np.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def __call__(self, x, dt=None):
        if dt is not None:
            self.freq = 1.0 / dt
        
        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = np.zeros_like(x)
            return x

        # Calculate derivative
        dx = (x - self.x_prev) * self.freq
        edx = self._low_pass_filter(dx, self.dx_prev, self._alpha(self.d_cutoff))
        self.dx_prev = edx

        # Calculate cutoff based on velocity
        cutoff = self.min_cutoff + self.beta * np.abs(edx)
        alpha = self._alpha(cutoff)
        
        # Filter value
        x_filtered = self._low_pass_filter(x, self.x_prev, alpha)
        self.x_prev = x_filtered
        
        return x_filtered


class Normalizer:
    def __init__(self, screen_width=1920, screen_height=1080):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Một bộ lọc cho X và một cho Y để xử lý vector
        # min_cutoff: càng thấp càng lọc rung tốt khi đứng yên
        # beta: càng cao càng giảm lag khi di chuyển nhanh
        self.filter = OneEuroFilter(min_cutoff=0.5, beta=0.01)
        self.last_time = None
    
    def normalize_to_pixel(self, normalized_x, normalized_y):
        """
        Chuyển từ normalized coordinates (0-1) sang pixel coordinates
        Args:
            normalized_x: float [0, 1]
            normalized_y: float [0, 1]
        Returns:
            tuple: (pixel_x, pixel_y)
        """
        # Đảm bảo trong khoảng [0, 1]
        nx = max(0.0, min(1.0, normalized_x))
        ny = max(0.0, min(1.0, normalized_y))
        
        pixel_x = int(nx * self.screen_width)
        pixel_y = int(ny * self.screen_height)
        return pixel_x, pixel_y
    
    def smooth_position(self, x, y):
        """
        Làm mượt vị trí bằng One Euro Filter
        Args:
            x, y: normalized coordinates
        Returns:
            tuple: (smoothed_x, smoothed_y) normalized
        """
        now = time.time()
        dt = None
        if self.last_time is not None:
            dt = now - self.last_time
        self.last_time = now

        # Áp dụng filter cho vector (x, y)
        smoothed = self.filter(np.array([x, y]), dt=dt)
        return float(smoothed[0]), float(smoothed[1])
    
    def get_index_finger_position(self, hand_landmarks):
        """
        Lấy vị trí ngón trỏ (landmark 8) và normalize
        Args:
            hand_landmarks: np.array shape (21, 3)
        Returns:
            tuple: (normalized_x, normalized_y) hoặc None
        """
        if hand_landmarks is None or len(hand_landmarks) < 9:
            return None
        
        # Landmark 8 là đầu ngón trỏ
        index_tip = hand_landmarks[8]
        x, y = index_tip[0], index_tip[1]
        
        # Smoothing
        x_smooth, y_smooth = self.smooth_position(x, y)
        
        return x_smooth, y_smooth
    
    def set_screen_size(self, width, height):
        """Cập nhật kích thước màn hình"""
        self.screen_width = width
        self.screen_height = height

