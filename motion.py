"""
Motion Feature Layer
Tính toán: vector chuyển động, velocity, distance, depth feature
Đây là tầng toán học thuần túy
"""
import numpy as np
from collections import deque


class MotionFeatureExtractor:
    def __init__(self, history_size=10):
        self.history_size = history_size
        self.position_history = deque(maxlen=history_size)
        self.time_history = deque(maxlen=history_size)
        self.last_time = None
    
    def update(self, x, y, current_time=None):
        """
        Cập nhật vị trí và thời gian
        Args:
            x, y: normalized coordinates
            current_time: timestamp (nếu None thì dùng frame count)
        """
        if current_time is None:
            current_time = len(self.position_history)
        
        self.position_history.append((x, y))
        self.time_history.append(current_time)
        self.last_time = current_time
    
    def get_velocity(self):
        """
        Tính velocity (tốc độ chuyển động)
        Returns:
            tuple: (vx, vy, magnitude) hoặc None nếu không đủ dữ liệu
        """
        if len(self.position_history) < 2:
            return None
        
        pos1 = self.position_history[-2]
        pos2 = self.position_history[-1]
        time1 = self.time_history[-2]
        time2 = self.time_history[-1]
        
        dt = time2 - time1
        if dt == 0:
            return None
        
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        
        vx = dx / dt
        vy = dy / dt
        magnitude = np.sqrt(vx**2 + vy**2)
        
        return (vx, vy, magnitude)
    
    def get_direction(self):
        """
        Tính hướng chuyển động
        Returns:
            tuple: (dx, dy) normalized direction vector hoặc None
        """
        if len(self.position_history) < 2:
            return None
        
        pos1 = self.position_history[-2]
        pos2 = self.position_history[-1]
        
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        
        magnitude = np.sqrt(dx**2 + dy**2)
        if magnitude == 0:
            return None
        
        # Normalize
        return (dx / magnitude, dy / magnitude)
    
    def get_distance(self, start_idx=-5, end_idx=-1):
        """
        Tính khoảng cách di chuyển trong khoảng thời gian
        Args:
            start_idx, end_idx: indices trong history
        Returns:
            float: distance hoặc None
        """
        if len(self.position_history) < abs(start_idx):
            return None
        
        pos1 = self.position_history[start_idx]
        pos2 = self.position_history[end_idx]
        
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        
        return np.sqrt(dx**2 + dy**2)
    
    def get_depth_feature(self, z_values):
        """
        Tính depth feature từ z coordinates
        Args:
            z_values: list hoặc array của z values
        Returns:
            dict: {
                'mean_depth': float,
                'depth_range': float,
                'is_forward': bool  # z < threshold
            }
        """
        if not z_values or len(z_values) == 0:
            return None
        
        z_array = np.array(z_values)
        mean_depth = np.mean(z_array)
        depth_range = np.max(z_array) - np.min(z_array)
        
        # Z âm = gần camera hơn
        is_forward = mean_depth < -0.05
        
        return {
            'mean_depth': mean_depth,
            'depth_range': depth_range,
            'is_forward': is_forward
        }
    
    def reset(self):
        """Reset history"""
        self.position_history.clear()
        self.time_history.clear()
        self.last_time = None

