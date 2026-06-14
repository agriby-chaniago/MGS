from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import Audit, DatasetReadOnly
from models.schemas import CreateAuditRequest, AuditSchema
from services.state_machine import transition
from services.publisher import publish_audit_job
from shared.response import success_response

router = APIRouter()

SERVICE_NAME = "audit_service"


@router.post("/api/v1/audits", status_code=201)
def create_audit(body: CreateAuditRequest, db: Session = Depends(get_db)):
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

    # 3. Buat audit record
    audit = Audit(dataset_id=body.dataset_id)
    db.add(audit)

    # 3. Commit dulu — supaya audit_id visible ke consumer sebelum message diterima
    db.commit()
    db.refresh(audit)

    # 4. Publish ke RabbitMQ
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

    # 5. Update status ke QUEUED — caller commit
    transition(audit, "queued", db)
    db.commit()
    db.refresh(audit)

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )


@router.post("/api/v1/audits/{audit_id}/retry", status_code=200)
def retry_audit(audit_id: UUID, db: Session = Depends(get_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")
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
def get_audit(audit_id: UUID, db: Session = Depends(get_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")

    return success_response(
        data=AuditSchema.model_validate(audit).model_dump(),
        service=SERVICE_NAME,
    )
