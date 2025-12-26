"""
Perception Layer - MediaPipe detection
Lấy landmark từ Hands, Face Mesh, Pose
Output là tọa độ thô (x, y, z) normalized
"""
import mediapipe as mp
import numpy as np


class Perception:
    def __init__(self):
        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        
        # MediaPipe Face Mesh (cho try-on)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # MediaPipe Pose (cho anchor cổ)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def process_hands(self, rgb_frame):
        """
        Xử lý hand detection
        Returns:
            list: Danh sách landmarks [(x, y, z), ...] hoặc None
        """
        results = self.hands.process(rgb_frame)
        if results.multi_hand_landmarks:
            # Lấy hand đầu tiên
            hand = results.multi_hand_landmarks[0]
            landmarks = np.array([[lm.x, lm.y, lm.z] for lm in hand.landmark])
            return landmarks
        return None
    
    def _calculate_head_rotation(self, landmarks):
        """
        Tính rotation (yaw, pitch, roll) từ face mesh landmarks
        Args:
            landmarks: np.array (468, 3)
        Returns:
            float: rotation angle (yaw) để xoay item
        """
        # Landmark 1: mũi, 152: cằm, 33: mắt trái, 263: mắt phải
        # Để đơn giản và mượt, ta dùng vector giữa hai mắt để tính yaw
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        
        # Tính hướng vector giữa hai mắt
        eye_vector = right_eye - left_eye
        yaw = np.arctan2(eye_vector[2], eye_vector[0])
        
        # Roll (nghiêng đầu)
        roll = np.arctan2(eye_vector[1], eye_vector[0])
        
        return roll # Trả về roll để item nghiêng theo đầu

    def process_face(self, rgb_frame):
        """
        Xử lý face detection cho try-on
        Returns:
            dict: {
                'landmarks': np.array,  # Face mesh landmarks
                'neck_anchor': tuple,   # (x, y) của cổ
                'face_scale': float,    # Scale dựa trên kích thước mặt
                'rotation': float       # Góc xoay (radians)
            } hoặc None
        """
        results = self.face_mesh.process(rgb_frame)
        pose_results = self.pose.process(rgb_frame)
        
        if results.multi_face_landmarks:
            face = results.multi_face_landmarks[0]
            landmarks = np.array([[lm.x, lm.y, lm.z] for lm in face.landmark])
            
            # 1. Tính rotation
            rotation = self._calculate_head_rotation(landmarks)
            
            # 2. Tính neck anchor
            # Kết hợp Face Mesh và Pose để có điểm neo ổn định
            if pose_results and pose_results.pose_landmarks:
                pose_landmarks = pose_results.pose_landmarks.landmark
                # Landmark 11, 12 là vai trái/phải
                left_shoulder = pose_landmarks[11]
                right_shoulder = pose_landmarks[12]
                
                # Cổ nằm ở giữa hai vai và hơi dịch lên
                neck_x = (left_shoulder.x + right_shoulder.x) / 2
                neck_y = (left_shoulder.y + right_shoulder.y) / 2 - 0.05
                neck_anchor = (neck_x, neck_y)
            else:
                # Fallback: dùng điểm dưới cằm trong face mesh
                chin = landmarks[152] 
                neck_anchor = (chin[0], chin[1] + 0.05)
            
            # 3. Tính scale từ kích thước mặt (landmark 234 và 454)
            left_side = landmarks[234]
            right_side = landmarks[454]
            face_width = np.linalg.norm(left_side[:2] - right_side[:2])
            face_scale = face_width * 2.5  # Tăng hệ số scale để item to hơn
            
            return {
                'landmarks': landmarks,
                'neck_anchor': neck_anchor,
                'face_scale': face_scale,
                'rotation': rotation
            }
        
        return None
    
    def release(self):
        """Giải phóng resources"""
        try:
            if self.hands:
                self.hands.close()
        except Exception as e:
            print(f"Lỗi khi giải phóng Hands: {e}")
        
        try:
            if self.face_mesh:
                self.face_mesh.close()
        except Exception as e:
            print(f"Lỗi khi giải phóng Face Mesh: {e}")
        
        try:
            if self.pose:
                self.pose.close()
        except Exception as e:
            print(f"Lỗi khi giải phóng Pose: {e}")

