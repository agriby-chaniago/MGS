from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import Audit, DatasetReadOnly
from models.schemas import CreateAuditRequest, AuditSchema
from services.state_machine import transition
from services.publisher import publish_audit_job
from shared.response import success_response

router = APIRouter()

SERVICE_NAME = "audit_service"

ALL_ANALYZERS = ["corruption", "empty", "resolution", "distribution", "duplicate"]

# Analyzer selection is computed server-side from the plan, never taken from
# the client — otherwise a free-tier client could just request all 5 itself.
TIER_ANALYZERS = {
    "free": ["corruption", "empty", "resolution"],
    "pro": ALL_ANALYZERS,
    "max": ALL_ANALYZERS,
}

# Daily audit quota per plan; None = unlimited. Fail-open default is "max"
# (see dataset_service/routers/upload.py for the same rationale).
TIER_DAILY_QUOTA = {"free": 3, "pro": 20, "max": None}


def _check_ownership(audit: Audit, x_user_id: str | None):
    if audit.user_id is not None and str(audit.user_id) != x_user_id:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")


def _check_daily_quota(db: Session, x_user_id: str | None, plan: str):
    quota = TIER_DAILY_QUOTA.get(plan)
    if quota is None or not x_user_id:
        return
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count_today = db.query(Audit).filter(
        Audit.user_id == x_user_id,
        Audit.created_at >= start_of_day,
    ).count()
    if count_today >= quota:
        raise HTTPException(
            status_code=429,
            detail=f"Kuota audit harian ({quota}/hari) untuk paket '{plan}' tercapai",
        )


@router.post("/api/v1/audits", status_code=201)
def create_audit(
    body: CreateAuditRequest,
    db: Session = Depends(get_db),
    x_user_plan: str = Header(default="max", alias="X-User-Plan"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    # 1. Validasi dataset ada dan tidak deleted
    dataset = db.query(DatasetReadOnly).filter(
        DatasetReadOnly.id == body.dataset_id,
        DatasetReadOnly.status != "deleted",
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan atau sudah dihapus")

    # 2. Dedup: return audit completed yang sudah ada untuk dataset ini (skip jika force=True)
    if not body.force:
        existing = db.query(Audit).filter(
            Audit.dataset_id == body.dataset_id,
            Audit.status == "completed",
        ).order_by(Audit.created_at.desc()).first()
        if existing:
            data = AuditSchema.model_validate(existing).model_dump()
            data["cached"] = True
            return success_response(data=data, service=SERVICE_NAME)

    # 3. Kuota harian per-tier (tidak berlaku untuk retry — lihat retry_audit)
    _check_daily_quota(db, x_user_id, x_user_plan)

    # 4. Buat audit record — requested_analyzers ditentukan server-side dari plan,
    # bukan dari client, biar free tier gak bisa minta 5 analyzer sendiri.
    analyzers = TIER_ANALYZERS.get(x_user_plan, TIER_ANALYZERS["free"])
    audit = Audit(dataset_id=body.dataset_id, user_id=x_user_id, requested_analyzers=analyzers)
    db.add(audit)

    # 5. Commit dulu — supaya audit_id visible ke consumer sebelum message diterima
    db.commit()
    db.refresh(audit)

    # 6. Transisi ke QUEUED **sebelum** publish — bugfix: urutan lama
    # (publish dulu, baru commit "queued") punya race condition nyata:
    # consumer bisa keburu dequeue & baca status="pending" (masih default
    # ORM sebelum transisi), lalu skip proses & ack pesan — audit macet
    # permanen (gak ada di queue lagi, gak bisa di-retry krn bukan status
    # "failed"). Commit status dulu baru publish menutup race window ini.
    transition(audit, "queued", db)
    db.commit()
    db.refresh(audit)

    # 7. Publish ke RabbitMQ
    try:
        publish_audit_job({
            "audit_id":            str(audit.id),
            "dataset_id":          str(audit.dataset_id),
            "dataset_minio_path":  dataset.minio_path,
            "requested_analyzers": audit.requested_analyzers,
            "created_at":          audit.created_at.isoformat(),
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal mengirim job ke queue")

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )


@router.post("/api/v1/audits/{audit_id}/retry", status_code=200)
def retry_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")
    _check_ownership(audit, x_user_id)
    # Retry does not consume new daily quota — it re-runs an existing audit,
    # not a new one, and keeps the original requested_analyzers.
    if audit.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Hanya audit berstatus 'failed' yang bisa di-retry (status saat ini: {audit.status})",
        )

    dataset = db.query(DatasetReadOnly).filter(
        DatasetReadOnly.id == audit.dataset_id,
        DatasetReadOnly.status != "deleted",
    ).first()
    if not dataset:
        raise HTTPException(status_code=400, detail="Dataset sudah dihapus, tidak bisa retry")

    transition(audit, "queued", db)
    audit.error_message = None
    audit.completed_at = None
    db.commit()
    db.refresh(audit)

    try:
        publish_audit_job({
            "audit_id":            str(audit.id),
            "dataset_id":          str(audit.dataset_id),
            "dataset_minio_path":  dataset.minio_path,
            "requested_analyzers": audit.requested_analyzers,
            "created_at":          audit.created_at.isoformat(),
            "force":               True,
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Gagal mengirim retry job ke queue")

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )


@router.get("/api/v1/audits/{audit_id}")
def get_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")
    _check_ownership(audit, x_user_id)

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )
