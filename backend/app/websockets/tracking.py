"""
WebSocket endpoints for real-time tracking.
Handles driver location updates and client delivery tracking.
"""
import asyncio
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select, update
from datetime import datetime
import structlog

from app.db.session import AsyncSessionLocal
from app.models.models import Driver, Delivery, Location, DeliveryStatus, DriverStatus
from app.core.security import decode_token
from app.core.redis import get_redis, CacheManager, PubSubManager

logger = structlog.get_logger()
router = APIRouter(tags=["WebSockets"])


class ConnectionManager:
    """Manages active WebSocket connections with room-based broadcasting."""

    def __init__(self):
        # delivery_id -> set of websockets (clients tracking)
        self.delivery_rooms: Dict[str, Set[WebSocket]] = {}
        # driver_id -> websocket
        self.driver_connections: Dict[str, WebSocket] = {}
        # admin connections
        self.admin_connections: Set[WebSocket] = set()
        # user_id -> websocket
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect_driver(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.driver_connections[driver_id] = websocket
        logger.info("Driver connected", driver_id=driver_id)

    async def connect_client(self, user_id: str, delivery_id: str, websocket: WebSocket):
        await websocket.accept()
        self.delivery_rooms.setdefault(delivery_id, set()).add(websocket)
        self.user_connections[user_id] = websocket
        logger.info("Client tracking connected", user_id=user_id, delivery_id=delivery_id)

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.add(websocket)
        logger.info("Admin connected to fleet monitor")

    async def disconnect_driver(self, driver_id: str):
        self.driver_connections.pop(driver_id, None)

    async def disconnect_client(self, user_id: str, delivery_id: str, websocket: WebSocket):
        if delivery_id in self.delivery_rooms:
            self.delivery_rooms[delivery_id].discard(websocket)
        if self.user_connections.get(user_id) is websocket:
            self.user_connections.pop(user_id, None)

    async def disconnect_admin(self, websocket: WebSocket):
        self.admin_connections.discard(websocket)

    async def broadcast_to_delivery_room(self, delivery_id: str, message: dict):
        """Send a message to all clients tracking this delivery."""
        if delivery_id in self.delivery_rooms:
            dead_sockets = set()
            for ws in self.delivery_rooms[delivery_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_sockets.add(ws)
            self.delivery_rooms[delivery_id] -= dead_sockets

    async def broadcast_to_admins(self, message: dict):
        """Send fleet update to all connected admins."""
        dead_sockets = set()
        for ws in self.admin_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.add(ws)
        self.admin_connections -= dead_sockets


# Global connection manager
manager = ConnectionManager()


async def redis_listener(websocket: WebSocket, channel: str):
    """Forward messages published on a Redis pub/sub channel to a WebSocket."""
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                except (TypeError, ValueError):
                    continue
                await websocket.send_json(data)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.websocket("/ws/driver/{driver_id}")
async def driver_location_ws(
    websocket: WebSocket,
    driver_id: str,
    token: str = Query(...),
):
    """
    Driver WebSocket endpoint.
    Driver sends GPS coordinates; we broadcast to tracking clients and admins.
    Expected message format:
    {
        "type": "location_update",
        "lat": 12.9716,
        "lng": 77.5946,
        "speed": 40.0,
        "heading": 270.0,
        "accuracy": 5.0
    }
    """
    # Validate token
    try:
        payload = decode_token(token)
        token_user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect_driver(driver_id, websocket)
    redis = await get_redis()
    cache = CacheManager(redis)

    async with AsyncSessionLocal() as db:
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "location_update":
                    lat = data.get("lat")
                    lng = data.get("lng")
                    speed = data.get("speed")
                    heading = data.get("heading")
                    accuracy = data.get("accuracy")

                    if lat is None or lng is None:
                        await websocket.send_json({"error": "lat and lng required"})
                        continue

                    now = datetime.utcnow()

                    # Update driver location in DB (async)
                    await db.execute(
                        update(Driver)
                        .where(Driver.id == driver_id)
                        .values(
                            current_lat=lat,
                            current_lng=lng,
                            last_location_update=now
                        )
                    )

                    # Save to location history
                    location = Location(
                        driver_id=driver_id,
                        latitude=lat,
                        longitude=lng,
                        speed=speed,
                        heading=heading,
                        accuracy=accuracy,
                        timestamp=now,
                    )
                    db.add(location)
                    await db.commit()

                    location_data = {
                        "lat": lat,
                        "lng": lng,
                        "speed": speed,
                        "heading": heading,
                        "accuracy": accuracy,
                        "timestamp": now.isoformat(),
                    }

                    # Cache latest location for quick lookups by trackers
                    await cache.set(f"driver_location:{driver_id}", location_data, ttl=300)

                    # Find active delivery for this driver and broadcast
                    # (a driver should have at most one, but fall back to the
                    # most recently updated one if more than one is active)
                    delivery_result = await db.execute(
                        select(Delivery).where(
                            Delivery.driver_id == driver_id,
                            Delivery.status.in_([
                                DeliveryStatus.ASSIGNED,
                                DeliveryStatus.PICKED_UP,
                                DeliveryStatus.IN_TRANSIT
                            ])
                        ).order_by(Delivery.updated_at.desc())
                    )
                    active_delivery = delivery_result.scalars().first()

                    broadcast_msg = {
                        "type": "location_update",
                        "driver_id": driver_id,
                        **location_data,
                    }

                    if active_delivery:
                        await manager.broadcast_to_delivery_room(
                            str(active_delivery.id), broadcast_msg
                        )
                        # Publish for any tracking sockets on other instances
                        await redis.publish(
                            f"delivery:{active_delivery.id}",
                            json.dumps(broadcast_msg)
                        )

                    # Broadcast to admins
                    await manager.broadcast_to_admins(broadcast_msg)

                    # ACK
                    await websocket.send_json({"type": "ack", "timestamp": now.isoformat()})

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            logger.info("Driver disconnected", driver_id=driver_id)
        except Exception as e:
            logger.error("Driver WS error", driver_id=driver_id, error=str(e))
        finally:
            await manager.disconnect_driver(driver_id)
            # Update driver as offline
            async with AsyncSessionLocal() as cleanup_db:
                await cleanup_db.execute(
                    update(Driver)
                    .where(Driver.id == driver_id)
                    .values(status=DriverStatus.OFFLINE)
                )
                await cleanup_db.commit()


@router.websocket("/ws/track/{delivery_id}")
async def track_delivery_ws(
    websocket: WebSocket,
    delivery_id: str,
    token: str = Query(...),
):
    """
    Client WebSocket endpoint for tracking a specific delivery.
    Sends the driver's last known location on connect, then streams
    real-time location and status updates via Redis pub/sub.
    """
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect_client(user_id, delivery_id, websocket)
    redis = await get_redis()
    cache = CacheManager(redis)

    listener_task = None
    try:
        # Send the driver's last known location immediately if available
        async with AsyncSessionLocal() as db:
            delivery_result = await db.execute(
                select(Delivery).where(Delivery.id == delivery_id)
            )
            delivery = delivery_result.scalar_one_or_none()
            if delivery and delivery.driver_id:
                cached_location = await cache.get(f"driver_location:{delivery.driver_id}")
                if cached_location:
                    await websocket.send_json({
                        "type": "initial_location",
                        "driver_id": str(delivery.driver_id),
                        **cached_location,
                    })

        # Stream live updates for this delivery
        listener_task = asyncio.create_task(
            redis_listener(websocket, f"delivery:{delivery_id}")
        )

        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("Client disconnected from tracking", user_id=user_id, delivery_id=delivery_id)
    finally:
        if listener_task:
            listener_task.cancel()
        await manager.disconnect_client(user_id, delivery_id, websocket)


@router.websocket("/ws/fleet")
async def fleet_monitor_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    """Admin WebSocket for fleet-wide monitoring."""
    try:
        payload = decode_token(token)
        role = payload.get("role")
        if role != "ADMIN":
            await websocket.close(code=4003, reason="Admin access required")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect_admin(websocket)
    listener_task = asyncio.create_task(redis_listener(websocket, "system_events"))

    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("Admin disconnected from fleet monitor")
    finally:
        listener_task.cancel()
        await manager.disconnect_admin(websocket)


@router.websocket("/ws/notifications/{user_id}")
async def user_notifications_ws(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(...),
):
    """Real-time notification WebSocket per user."""
    try:
        payload = decode_token(token)
        token_user_id = payload.get("sub")
        if token_user_id != user_id:
            await websocket.close(code=4003, reason="Access denied")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    listener_task = asyncio.create_task(redis_listener(websocket, f"user:{user_id}"))

    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
