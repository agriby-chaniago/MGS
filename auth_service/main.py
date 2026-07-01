import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from models.database import init_db
from routers import auth, internal
from shared.response import success_response

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


@app.get("/api/v1/auth/health")
def health():
    return success_response(
        data={"status": "ok", "service": "auth_service"},
        service="auth_service",
    )


app.include_router(auth.router)
app.include_router(internal.router)
