import hashlib
import os
import shutil
import zipfile
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import Dataset, DatasetClass
from models.schemas import UploadResponseSchema
from services.validator import (
    validate_zip_structure,
    scan_extracted_dataset,
    MAX_ZIP_SIZE_MB,
)
from services.minio_service import minio_service
from shared.response import success_response, error_response

router = APIRouter()

SERVICE_NAME = "dataset_service"
UPLOAD_TMP_DIR = "/tmp/modelgate_uploads"


def _cleanup_tmp(path: str):
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


@router.post("/api/v1/datasets/upload", status_code=201)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    # 1. Cek size limit
    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_ZIP_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File terlalu besar. Maksimum {MAX_ZIP_SIZE_MB}MB, diterima {size_mb:.1f}MB",
        )

    # 1b. Dedup: cek hash — return existing dataset jika sama
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = db.query(Dataset).filter(
        Dataset.file_hash == file_hash,
        Dataset.status == "active",
    ).first()
    if existing:
        return success_response(
            data={
                "dataset_id": str(existing.id),
                "name": existing.name,
                "class_count": existing.class_count,
                "total_images": existing.total_images,
                "file_size_mb": existing.file_size_mb,
                "invalid_files": [],
                "cached": True,
            },
            service=SERVICE_NAME,
        )

    upload_id = str(uuid4())
    tmp_dir = os.path.join(UPLOAD_TMP_DIR, upload_id)
    os.makedirs(tmp_dir, exist_ok=True)
    zip_path = os.path.join(tmp_dir, "upload.zip")

    # 2. Tulis ZIP ke /tmp
    with open(zip_path, "wb") as f:
        f.write(file_bytes)

    # 3. Validasi struktur ZIP
    validation = validate_zip_structure(zip_path)
    if not validation.valid:
        background_tasks.add_task(_cleanup_tmp, tmp_dir)
        raise HTTPException(status_code=400, detail=validation.error_message)

    # 4. Extract
    extract_dir = os.path.join(tmp_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    # 5. Scan gambar
    stats = scan_extracted_dataset(extract_dir)

    if stats.total_classes < 2:
        background_tasks.add_task(_cleanup_tmp, tmp_dir)
        raise HTTPException(
            status_code=400,
            detail=f"Dataset harus punya minimal 2 class valid, ditemukan: {stats.total_classes}",
        )

    dataset_id = str(uuid4())
    minio_path = None

    try:
        # 6. Upload ke MinIO
        minio_path = minio_service.upload_directory(dataset_id, extract_dir)

        # 7. Save ke DB
        dataset = Dataset(
            id=dataset_id,
            name=name,
            status="active",
            class_count=stats.total_classes,
            total_images=stats.total_images,
            file_size_mb=round(stats.total_size_bytes / (1024 * 1024), 2),
            minio_path=minio_path,
            file_hash=file_hash,
        )
        db.add(dataset)
        db.flush()

        for class_name, count in stats.images_per_class.items():
            db.add(DatasetClass(
                dataset_id=dataset_id,
                class_name=class_name,
                image_count=count,
            ))

        db.commit()

    except Exception as e:
        db.rollback()
        if minio_path:
            try:
                minio_service.delete_prefix(dataset_id + "/")
            except Exception:
                pass
        background_tasks.add_task(_cleanup_tmp, tmp_dir)

        if "minio" in str(type(e).__module__).lower() or "s3" in str(e).lower():
            raise HTTPException(status_code=500, detail="Storage upload gagal")
        raise HTTPException(status_code=500, detail="Database save gagal")

    background_tasks.add_task(_cleanup_tmp, tmp_dir)

    return success_response(
        data=UploadResponseSchema(
            dataset_id=dataset_id,
            name=name,
            class_count=stats.total_classes,
            total_images=stats.total_images,
            file_size_mb=round(stats.total_size_bytes / (1024 * 1024), 2),
            invalid_files=stats.invalid_files,
        ).model_dump(),
        service=SERVICE_NAME,
    )
