from fastapi import FastAPI
from models.database import init_db
from shared.response import success_response

app = FastAPI(title="Analysis Service", version="1.0.0")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/v1/analyses/health")
def health():
    return success_response(
        data={"status": "ok", "service": "analysis_service"},
        service="analysis_service",
    )
