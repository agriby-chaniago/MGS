from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from models.database import init_db
from services.minio_service import minio_service
from routers import upload, datasets
from shared.response import success_response

app = FastAPI(title="Dataset Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def startup():
    init_db()
    minio_service.ensure_bucket()


@app.get("/api/v1/datasets/health")
def health():
    return success_response(
        data={"status": "ok", "service": "dataset_service"},
        service="dataset_service",
    )


app.include_router(upload.router)
app.include_router(datasets.router)
