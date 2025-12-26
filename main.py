import asyncio
import time
import cv2
import signal
import sys
from aiohttp import web
import threading
from concurrent.futures import ThreadPoolExecutor
from camera import Camera
from perception import Perception
from normalize import Normalizer
from motion import MotionFeatureExtractor
from gesture import GestureDetector
from state import StateMachine, SystemState
from bridge import WebSocketBridge


class System:
    def __init__(self):
        # Khởi tạo các tầng
        try:
            print("Đang khởi tạo camera...")
            self.camera = Camera(camera_id=0)
            print("Camera đã khởi tạo")
        except Exception as e:
            print(f"Lỗi khởi tạo camera: {e}")
            raise
        
        try:
            print("Đang khởi tạo MediaPipe...")
            self.perception = Perception()
            print("MediaPipe đã khởi tạo")
        except Exception as e:
            print(f"Lỗi khởi tạo MediaPipe: {e}")
            raise
        
        self.normalizer = Normalizer(screen_width=1920, screen_height=1080)
        self.motion_extractor = MotionFeatureExtractor()
        self.gesture_detector = GestureDetector(self.motion_extractor)
        self.state_machine = StateMachine(idle_timeout=8.0) # 8s timeout
        self.bridge = WebSocketBridge(host='localhost', port=8765)
        
        # Multithreading cho Perception (tránh block main loop)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.perception_task = None
        
        # HTTP server cho video stream
        self.app = web.Application()
        self.app.router.add_get('/video', self.video_stream_handler)
        self.runner = None
        self.site = None
        
        # State tracking
        self.last_hand_landmarks = None
        self.frame_count = 0
        self.dropped_frames = 0
        self.start_time = time.time()
        self.current_frame_bgr = None
        self.frame_lock = threading.Lock()
        self.running = False
    
    async def initialize(self):
        """Khởi tạo hệ thống"""
        await self.bridge.start_server()
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', 9000)
        await self.site.start()
        
        print("System initialized:")
        print("- WebSocket: ws://localhost:8765")
        print("- Video View: http://localhost:9000/video")
        self.running = True
    
    async def process_loop(self):
        """Main non-blocking processing loop"""
        loop = asyncio.get_event_loop()
        
        while self.running:
            # 1. Sensor Layer: Đọc frame thô nhất có thể
            success, frame_rgb = self.camera.read_frame()
            if not success:
                await asyncio.sleep(0.01)
                continue
            
            # Cập nhật frame cho video stream (MJPEG)
            frame_bgr = self.camera.get_last_frame_bgr()
            if frame_bgr is not None:
                with self.frame_lock:
                    self.current_frame_bgr = frame_bgr.copy()
            
            # 2. Perception & Logic: Đẩy sang thread khác để không lag camera
            # Frame Dropping: Bỏ qua frame mới nếu executor đang busy để tránh latency tích lũy
            if self.perception_task is None or self.perception_task.done():
                self.perception_task = loop.run_in_executor(
                    self.executor, self._sync_logic, frame_rgb
                )
                # Đăng ký callback để gửi dữ liệu sang Bridge khi xử lý xong
                self.perception_task.add_done_callback(
                    lambda fut: asyncio.run_coroutine_threadsafe(self._emit_results(fut.result()), loop)
                )
                self.frame_count += 1
            else:
                # Executor đang busy - drop frame để duy trì realtime
                self.dropped_frames += 1
                if self.dropped_frames % 30 == 0:  # Log mỗi 30 frames
                    print(f"Frame dropping: {self.dropped_frames} frames dropped (maintaining realtime)")

            # Check timeout state machine
            if self.state_machine.check_timeout():
                await self.bridge.emit_state_change(SystemState.IDLE.value)

            await asyncio.sleep(0.001)

    def _sync_logic(self, frame_rgb):
        """Xử lý đồng bộ trong thread riêng"""
        current_time = time.time() - self.start_time
        results = {'gesture': None, 'cursor': None, 'transform': None}

        # Perception: Hands
        hand_landmarks = self.perception.process_hands(frame_rgb)
        if hand_landmarks is not None:
            self.last_hand_landmarks = hand_landmarks
            # Normalize & Smooth
            norm_pos = self.normalizer.get_index_finger_position(hand_landmarks)
            if norm_pos:
                pixel_x, pixel_y = self.normalizer.normalize_to_pixel(norm_pos[0], norm_pos[1])
                results['cursor'] = (pixel_x, pixel_y)
                self.motion_extractor.update(norm_pos[0], norm_pos[1], current_time)

        # Gesture Detection
        gesture = self.gesture_detector.process(self.last_hand_landmarks, current_time)
        if gesture:
            is_valid, should_emit = self.state_machine.handle_gesture(gesture)
            if is_valid and should_emit:
                results['gesture'] = gesture
                results['new_state'] = self.state_machine.get_state().value

        # Try-on logic (nếu đang trong state TRY_ON)
        if self.state_machine.get_state() == SystemState.TRY_ON:
            face_data = self.perception.process_face(frame_rgb)
            if face_data:
                # Smooth neck anchor
                smooth_anchor = self.normalizer.smooth_neck_anchor(
                    face_data['neck_anchor'][0], 
                    face_data['neck_anchor'][1]
                )
                anchor_x, anchor_y = self.normalizer.normalize_to_pixel(
                    smooth_anchor[0], smooth_anchor[1]
                )
                
                # Smooth rotation và scale
                smooth_rotation = self.normalizer.smooth_rotation(face_data['rotation'])
                smooth_scale = self.normalizer.smooth_scale(face_data['face_scale'])
                
                results['transform'] = {
                    'anchor': (anchor_x, anchor_y),
                    'rotation': smooth_rotation,
                    'scale': smooth_scale
                }
        
        return results

    async def _emit_results(self, results):
        """Gửi kết quả từ thread xử lý sang WebSocket"""
        if results['cursor']:
            await self.bridge.emit_cursor_move(*results['cursor'])
        
        if results['gesture']:
            await self.bridge.emit_gesture_event(results['gesture'])
            if 'new_state' in results:
                await self.bridge.emit_state_change(results['new_state'])
                
        if results['transform']:
            t = results['transform']
            await self.bridge.emit_item_transform(t['anchor'], t['rotation'], t['scale'])

    async def run(self):
        """Khởi động hệ thống"""
        await self.initialize()
        try:
            await self.process_loop()
        except asyncio.CancelledError:
            pass
        finally:
            await self.cleanup()
    
    async def video_stream_handler(self, request):
        """MJPEG Streamer"""
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=frame'
        response.headers['Access-Control-Allow-Origin'] = '*'
        await response.prepare(request)
        
        try:
            while self.running:
                with self.frame_lock:
                    if self.current_frame_bgr is None:
                        await asyncio.sleep(0.01)
                        continue
                    frame = self.current_frame_bgr.copy()
                
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                await response.write(
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
                )
                await asyncio.sleep(0.03) # ~30 FPS
        except:
            pass
        return response
    
    async def cleanup(self):
        """Dọn dẹp resources"""
        print("Cleaning up...")
        self.running = False
        if self.runner: await self.runner.cleanup()
        self.camera.release()
        self.perception.release()
        await self.bridge.stop_server()
        self.executor.shutdown(wait=False)
        print("Done.")


async def main():
    system = System()
    try:
        await system.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    asyncio.run(main())

