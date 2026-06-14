from fastapi import FastAPI
from models.database import init_db
from routers import audits
from shared.response import success_response

app = FastAPI(title="Audit Service", version="1.0.0")


@app.on_event("startup")
def startup():
    init_db()


app.include_router(audits.router)


@app.get("/api/v1/audits/health")
def health():
    return success_response(
        data={"status": "ok", "service": "audit_service"},
        service="audit_service",
    )
