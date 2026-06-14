import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from models.database import init_db
from routers import reports
from shared.response import success_response

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Report Service", version="1.0.0", lifespan=lifespan)


@app.get("/api/v1/reports/health")
def health():
    return success_response(
        data={"status": "ok", "service": "report_service"},
        service="report_service",
    )


app.include_router(reports.router)
