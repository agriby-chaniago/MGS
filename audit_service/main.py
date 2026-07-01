import asyncio
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from models.database import init_db
from routers import audits, ws
from services import ws_manager
from services.results_consumer import start_results_consuming
from shared.response import success_response

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Captured so the sync RabbitMQ consumer thread below can schedule
    # WebSocket broadcasts back onto this event loop (see ws_manager.py).
    ws_manager.set_event_loop(asyncio.get_running_loop())
    thread = threading.Thread(target=start_results_consuming, daemon=True)
    thread.start()
    yield


app = FastAPI(title="Audit Service", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


@app.get("/api/v1/audits/health")
def health():
    return success_response(
        data={"status": "ok", "service": "audit_service"},
        service="audit_service",
    )


app.include_router(audits.router)
app.include_router(ws.router)
