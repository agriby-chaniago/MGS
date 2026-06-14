import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from models.database import init_db
from routers import audits
from services.results_consumer import start_results_consuming
from shared.response import success_response

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    thread = threading.Thread(target=start_results_consuming, daemon=True)
    thread.start()
    yield


app = FastAPI(title="Audit Service", version="1.0.0", lifespan=lifespan)


@app.get("/api/v1/audits/health")
def health():
    return success_response(
        data={"status": "ok", "service": "audit_service"},
        service="audit_service",
    )


app.include_router(audits.router)
