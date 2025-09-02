"""
WebSocket Manager for Real-Time Updates

Handles WebSocket connections, message broadcasting, and real-time
communication for the Social Inbox and other real-time features.
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """WebSocket message types"""
    # Connection management
    CONNECT = "connect"
    DISCONNECT = "disconnect" 
    HEARTBEAT = "heartbeat"
    
    # Social inbox events
    NEW_INTERACTION = "new_interaction"
    INTERACTION_UPDATE = "interaction_update"
    INTERACTION_RESPONDED = "interaction_responded"
    RESPONSE_GENERATED = "response_generated"
    
    # General notifications
    NOTIFICATION = "notification"
    ERROR = "error"
    SUCCESS = "success"

@dataclass
class WebSocketMessage:
    """Structured WebSocket message"""
    type: MessageType
    data: Dict[str, Any]
    user_id: int
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        # Store connections by user_id -> list of websockets
        self.user_connections: Dict[int, List[WebSocket]] = {}
        # Store user_id for each websocket (reverse lookup)
        self.websocket_users: Dict[WebSocket, int] = {}
        self.total_connections: int = 0
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        
        self.user_connections[user_id].append(websocket)
        self.websocket_users[websocket] = user_id
        self.total_connections += 1
        
        logger.info(f"WebSocket connected for user {user_id}. Total connections: {self.total_connections}")
        
        # Send connection confirmation
        message = WebSocketMessage(
            type=MessageType.CONNECT,
            data={
                "message": "Connected successfully",
                "user_id": user_id,
                "connection_count": len(self.user_connections[user_id])
            },
            user_id=user_id
        )
        await self._send_to_websocket(websocket, message)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        user_id = self.websocket_users.get(websocket)
        
        if user_id is not None:
            if user_id in self.user_connections:
                self.user_connections[user_id].remove(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            del self.websocket_users[websocket]
            self.total_connections -= 1
            
            logger.info(f"WebSocket disconnected for user {user_id}. Total connections: {self.total_connections}")
    
    async def send_to_user(self, user_id: int, message: WebSocketMessage):
        """Send a message to all connections for a specific user"""
        if user_id not in self.user_connections:
            logger.debug(f"No WebSocket connections found for user {user_id}")
            return
        
        connections = self.user_connections[user_id].copy()
        for websocket in connections:
            await self._send_to_websocket(websocket, message)
    
    async def send_to_all_users(self, message: WebSocketMessage, exclude_user: Optional[int] = None):
        """Send a message to all connected users with backpressure handling"""
        user_ids = list(self.user_connections.keys())
        if exclude_user:
            user_ids = [uid for uid in user_ids if uid != exclude_user]
        
        # Use bounded concurrency to prevent overwhelming the event loop
        semaphore = asyncio.Semaphore(20)  # Max 20 concurrent sends
        
        async def bounded_send(user_id: int):
            async with semaphore:
                try:
                    await self.send_to_user(user_id, message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
        
        # Send to all users concurrently with backpressure
        await asyncio.gather(
            *[bounded_send(uid) for uid in user_ids],
            return_exceptions=True
        )
    
    async def broadcast_to_user_sessions(self, user_id: int, message: WebSocketMessage):
        """Broadcast to all sessions of a specific user"""
        await self.send_to_user(user_id, message)
    
    async def _send_to_websocket(self, websocket: WebSocket, message: WebSocketMessage):
        """Send a message to a specific WebSocket connection with timeout"""
        try:
            # Add timeout to prevent hanging on slow clients
            await asyncio.wait_for(
                websocket.send_text(message.to_json()),
                timeout=5.0  # 5 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("WebSocket send timed out, disconnecting slow client")
            self.disconnect(websocket)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            # Clean up failed connection
            self.disconnect(websocket)
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of connections for a user"""
        return len(self.user_connections.get(user_id, []))
    
    def get_total_connections(self) -> int:
        """Get total number of connections"""
        return self.total_connections
    
    def get_connected_users(self) -> Set[int]:
        """Get set of all connected user IDs"""
        return set(self.user_connections.keys())

# Global connection manager instance
manager = ConnectionManager()

class WebSocketService:
    """Service for handling WebSocket operations"""
    
    def __init__(self, connection_manager: ConnectionManager = None):
        self.manager = connection_manager or manager
    
    async def handle_websocket(self, websocket: WebSocket, user_id: int):
        """Handle a WebSocket connection lifecycle"""
        await self.manager.connect(websocket, user_id)
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                await self._handle_client_message(websocket, user_id, data)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            self.manager.disconnect(websocket)
    
    async def _handle_client_message(self, websocket: WebSocket, user_id: int, data: str):
        """Handle incoming message from client"""
        try:
            message_data = json.loads(data)
            message_type = message_data.get("type")
            
            if message_type == MessageType.HEARTBEAT.value:
                # Respond to heartbeat
                response = WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    data={"timestamp": datetime.now(timezone.utc).isoformat()},
                    user_id=user_id
                )
                await self.manager._send_to_websocket(websocket, response)
                
            else:
                logger.debug(f"Received message from user {user_id}: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from user {user_id}: {e}")
            error_message = WebSocketMessage(
                type=MessageType.ERROR,
                data={"message": "Invalid JSON format"},
                user_id=user_id
            )
            await self.manager._send_to_websocket(websocket, error_message)
    
    async def notify_new_interaction(self, user_id: int, interaction_data: Dict[str, Any]):
        """Notify user of new social media interaction"""
        message = WebSocketMessage(
            type=MessageType.NEW_INTERACTION,
            data={
                "interaction": interaction_data,
                "message": "New interaction received"
            },
            user_id=user_id
        )
        await self.manager.send_to_user(user_id, message)
    
    async def notify_interaction_update(self, user_id: int, interaction_id: str, updates: Dict[str, Any]):
        """Notify user of interaction status update"""
        message = WebSocketMessage(
            type=MessageType.INTERACTION_UPDATE,
            data={
                "interaction_id": interaction_id,
                "updates": updates,
                "message": "Interaction updated"
            },
            user_id=user_id
        )
        await self.manager.send_to_user(user_id, message)
    
    async def notify_response_generated(self, user_id: int, interaction_id: str, response_data: Dict[str, Any]):
        """Notify user that AI response was generated"""
        message = WebSocketMessage(
            type=MessageType.RESPONSE_GENERATED,
            data={
                "interaction_id": interaction_id,
                "response": response_data,
                "message": "AI response generated"
            },
            user_id=user_id
        )
        await self.manager.send_to_user(user_id, message)
    
    async def notify_interaction_responded(self, user_id: int, interaction_id: str, response_id: str):
        """Notify user that response was sent"""
        message = WebSocketMessage(
            type=MessageType.INTERACTION_RESPONDED,
            data={
                "interaction_id": interaction_id,
                "response_id": response_id,
                "message": "Response sent successfully"
            },
            user_id=user_id
        )
        await self.manager.send_to_user(user_id, message)
    
    async def send_notification(self, user_id: int, notification_data: Dict[str, Any]):
        """Send a general notification to user"""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            data=notification_data,
            user_id=user_id
        )
        await self.manager.send_to_user(user_id, message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": self.manager.get_total_connections(),
            "connected_users": len(self.manager.get_connected_users()),
            "users": list(self.manager.get_connected_users())
        }

# Global WebSocket service instance
websocket_service = WebSocketService(manager)