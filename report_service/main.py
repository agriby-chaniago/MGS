from fastapi import FastAPI
from models.database import init_db
from routers import reports
from shared.response import success_response

app = FastAPI(title="Report Service", version="1.0.0")


@app.on_event("startup")
def startup():
    init_db()


app.include_router(reports.router)


@app.get("/api/v1/reports/health")
def health():
    return success_response(
        data={"status": "ok", "service": "report_service"},
        service="report_service",
    )
