import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Mutated/read ONLY from inside the FastAPI event loop (the WebSocket
# handler's own coroutine, or the _broadcast coroutine scheduled via
# broadcast_threadsafe below) — never directly from the sync RabbitMQ
# consumer thread. This is what makes it safe without locks.
# See plan Workstream C's thread-safety rule.
_connections: dict[str, list[WebSocket]] = {}
_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    """Captured once at FastAPI startup so the sync consumer thread
    (results_consumer.py, running in its own daemon thread) can safely
    hand broadcasts back to the event loop via run_coroutine_threadsafe."""
    global _loop
    _loop = loop


async def connect(audit_id: str, ws: WebSocket):
    await ws.accept()
    _connections.setdefault(audit_id, []).append(ws)


async def disconnect(audit_id: str, ws: WebSocket):
    conns = _connections.get(audit_id)
    if conns and ws in conns:
        conns.remove(ws)
        if not conns:
            _connections.pop(audit_id, None)


async def _broadcast(audit_id: str, message: dict):
    for ws in list(_connections.get(audit_id, [])):
        try:
            await ws.send_json(message)
        except Exception:
            await disconnect(audit_id, ws)


def broadcast_threadsafe(audit_id: str, message: dict):
    """Called from the synchronous results_consumer.py thread."""
    if _loop is None:
        logger.warning("WS event loop not yet set, dropping broadcast")
        return
    asyncio.run_coroutine_threadsafe(_broadcast(audit_id, message), _loop)
