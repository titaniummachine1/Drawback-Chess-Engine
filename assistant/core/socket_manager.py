import asyncio
import json
import socketio
from pathlib import Path
from typing import Dict, List, Optional, Callable

class SocketManager:
    def __init__(self, game_id: str, port: int, on_update: Callable, on_message: Callable = None):
        self.game_id = game_id
        self.port = port
        self.on_update = on_update
        self.on_message = on_message
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.connecting = False
        self.username = None

    async def connect(self, username: Optional[str] = None):
        """Connect to the game's Socket.IO server."""
        if self.connecting or self.connected:
            return
        
        self.connecting = True
        self.username = username
        
        @self.sio.event
        async def connect():
            print(f"[SOCKET.IO] Connected to port {self.port}")
            self.connected = True
            await self.sio.emit('join', {'room': self.game_id})
            if self.username:
                await self.sio.emit('join', {'room': f"{self.game_id}-{self.username}"})

        @self.sio.event
        async def disconnect():
            print("[SOCKET.IO] Disconnected")
            self.connected = False

        @self.sio.event
        async def update(data):
            if self.on_update:
                await self.on_update(data)

        @self.sio.event
        async def message(data):
            if self.on_message:
                await self.on_message(data)
            else:
                print(f"[SOCKET.IO] Message: {data.get('message')}")

        try:
            url = "https://www.drawbackchess.com"
            path = f"/app{self.port - 5000}/socket.io"
            await self.sio.connect(url, socketio_path=path, transports=["websocket"])
        except Exception as e:
            print(f"[SOCKET.IO] Connection error: {e}")
            self.connected = False
        finally:
            self.connecting = False

    async def disconnect(self):
        """Disconnect from the server."""
        if self.connected:
            await self.sio.disconnect()
            self.connected = False
