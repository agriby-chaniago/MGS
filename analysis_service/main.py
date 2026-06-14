import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from consumer import start_consuming
from models.database import init_db
from shared.response import success_response

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    thread = threading.Thread(target=start_consuming, daemon=True)
    thread.start()
    yield


app = FastAPI(title="Analysis Service", version="1.0.0", lifespan=lifespan)


@app.get("/api/v1/analyses/health")
def health():
    return success_response(
        data={"status": "ok", "service": "analysis_service"},
        service="analysis_service",
    )
