import io
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from models.database import get_db
from services.aggregator import get_report_data
from services.pdf_generator import generate_pdf
from shared.response import success_response

router = APIRouter()
SERVICE_NAME = "report_service"


def _get_owned_report(audit_id: UUID, db: Session, x_user_id: str | None) -> dict:
    data = get_report_data(audit_id, db)
    if not data:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")
    # 404, not 403 — matches the ownership rule in dataset_service/audit_service.
    if data["user_id"] is not None and data["user_id"] != x_user_id:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")
    return data


@router.get("/api/v1/reports/{audit_id}")
def get_report(
    audit_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    data = _get_owned_report(audit_id, db, x_user_id)
    return success_response(data=data, service=SERVICE_NAME)


@router.get("/api/v1/reports/{audit_id}/summary")
def get_summary(
    audit_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    data = _get_owned_report(audit_id, db, x_user_id)
    return success_response(
        data={
            "audit_id": data["audit_id"],
            "audit_status": data["audit_status"],
            "health_score": data["health_score"],
            "grade": data["grade"],
            "components": data["components"],
        },
        service=SERVICE_NAME,
    )


@router.get("/api/v1/reports/{audit_id}/pdf")
def download_pdf(
    audit_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_plan: str = Header(default="max", alias="X-User-Plan"),
):
    if x_user_plan == "free":
        raise HTTPException(status_code=403, detail="PDF export hanya untuk paket Pro/Max")
    data = _get_owned_report(audit_id, db, x_user_id)
    pdf_bytes = generate_pdf(data)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{audit_id}.pdf"},
    )
