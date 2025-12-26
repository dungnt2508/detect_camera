"""
Sensor Layer - Chỉ đọc frame từ camera
Không xử lý logic, chỉ capture
"""
import cv2


class Camera:
    def __init__(self, camera_id=0):
        self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"Không thể mở camera {camera_id}")
        self.last_frame_bgr = None
    
    def read_frame(self):
        """
        Đọc frame từ camera (RGB cho MediaPipe)
        Returns:
            tuple: (success, frame_rgb) hoặc (False, None)
        """
        ret, frame = self.cap.read()
        if ret:
            # Lưu frame BGR để dùng cho video stream
            self.last_frame_bgr = frame.copy()
            # Chuyển BGR sang RGB cho MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return True, frame_rgb
        return False, None
    
    def get_last_frame_bgr(self):
        """
        Lấy frame BGR cuối cùng đã đọc (cho video stream)
        Returns:
            numpy array hoặc None
        """
        return self.last_frame_bgr
    
    def release(self):
        """Giải phóng camera"""
        if self.cap:
            self.cap.release()
