"""
Bridge Layer - WebSocket emit
Gửi dữ liệu sang frontend: cursor position, gesture event, item transform
"""
import json
import asyncio
import websockets
from typing import Optional, Dict, Any


class WebSocketBridge:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.server = None
    
    async def register_client(self, websocket):
        """Đăng ký client mới"""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")
    
    async def unregister_client(self, websocket):
        """Hủy đăng ký client"""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def handler(self, websocket, path):
        """WebSocket handler"""
        await self.register_client(websocket)
        try:
            # Giữ connection mở
            async for message in websocket:
                # Frontend có thể gửi ping
                if message == "ping":
                    await websocket.send("pong")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def emit_cursor_move(self, x, y):
        """
        Emit cursor position (có throttle dựa trên khoảng cách thay đổi)
        Args:
            x, y: pixel coordinates
        """
        if hasattr(self, 'last_cursor'):
            # Chỉ gửi nếu di chuyển đủ xa (> 2 pixel) để giảm noise/bandwidth
            dx = abs(x - self.last_cursor[0])
            dy = abs(y - self.last_cursor[1])
            if dx < 2 and dy < 2:
                return
        
        self.last_cursor = (x, y)
        payload = {
            'type': 'CURSOR_MOVE',
            'x': x,
            'y': y
        }
        await self.broadcast(payload)
    
    async def emit_gesture_event(self, gesture):
        """
        Emit gesture event
        Args:
            gesture: str (SWIPE_LEFT, SWIPE_RIGHT, PINCH, HOLD)
        """
        payload = {
            'type': 'GESTURE',
            'gesture': gesture
        }
        await self.broadcast(payload)
    
    async def emit_item_transform(self, neck_anchor, rotation, scale):
        """
        Emit item transform cho try-on
        Args:
            neck_anchor: tuple (x, y) pixel coordinates
            rotation: float (radians)
            scale: float
        """
        payload = {
            'type': 'ITEM_TRANSFORM',
            'anchor': {
                'x': neck_anchor[0],
                'y': neck_anchor[1]
            },
            'rotation': rotation,
            'scale': scale
        }
        await self.broadcast(payload)
    
    async def emit_state_change(self, state):
        """
        Emit state change
        Args:
            state: str (IDLE, BROWSE_ITEM, TRY_ON)
        """
        payload = {
            'type': 'STATE_CHANGE',
            'state': state
        }
        await self.broadcast(payload)
    
    async def broadcast(self, payload):
        """
        Broadcast message đến tất cả clients
        Args:
            payload: dict
        """
        if not self.clients:
            return
        
        message = json.dumps(payload)
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Xóa các client đã disconnect
        for client in disconnected:
            self.clients.discard(client)
    
    async def start_server(self):
        """Khởi động WebSocket server"""
        self.server = await websockets.serve(
            self.handler,
            self.host,
            self.port
        )
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
    
    async def stop_server(self):
        """Dừng WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped")

