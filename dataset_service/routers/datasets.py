from fastapi import APIRouter

router = APIRouter()

# TODO (Humam): Implement endpoints berikut
# GET  /api/v1/datasets          → list semua dataset
# GET  /api/v1/datasets/{id}     → detail 1 dataset
# DELETE /api/v1/datasets/{id}   → soft delete (set status = "deleted")
#
# Gunakan:
#   from dataset_service.models.database import get_db
#   from dataset_service.models.orm import Dataset, DatasetClass
#   from dataset_service.models.schemas import DatasetSchema, DatasetDetailSchema
#   from shared.response import success_response, error_response
