from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import Dataset
from models.schemas import DatasetSchema, DatasetDetailSchema
from services.minio_service import minio_service
from shared.response import success_response

router = APIRouter()

SERVICE_NAME = "dataset_service"


@router.get("/api/v1/datasets")
def list_datasets(db: Session = Depends(get_db)):
    datasets = (
        db.query(Dataset)
        .filter(Dataset.status != "deleted")
        .order_by(Dataset.created_at.desc())
        .all()
    )
    return success_response(
        data=[DatasetSchema.model_validate(d).model_dump() for d in datasets],
        service=SERVICE_NAME,
    )


@router.get("/api/v1/datasets/{dataset_id}")
def get_dataset(dataset_id: UUID, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.status != "deleted",
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    return success_response(
        data=DatasetDetailSchema.model_validate(dataset).model_dump(),
        service=SERVICE_NAME,
    )


@router.delete("/api/v1/datasets/{dataset_id}", status_code=200)
def delete_dataset(dataset_id: UUID, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.status != "deleted",
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    dataset.status = "deleted"
    db.commit()
    try:
        minio_service.delete_prefix(str(dataset_id) + "/")
    except Exception:
        pass
    return success_response(
        data={"dataset_id": str(dataset_id), "status": "deleted"},
        service=SERVICE_NAME,
    )
