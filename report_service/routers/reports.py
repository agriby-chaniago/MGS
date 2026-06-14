from fastapi import APIRouter

router = APIRouter()

# TODO (Humam - Fase 3): Implement endpoints berikut
# GET /api/v1/reports/{audit_id}          → report lengkap
# GET /api/v1/reports/{audit_id}/summary  → health_score + grade saja
#
# Gunakan:
#   from models.database import get_db
#   from models.orm import Audit, AnalysisResult   ← read-only mirror models
#   from models.schemas import ReportSchema, ReportSummarySchema
#   from shared.response import success_response, error_response
#
# Contoh query:
#   audit = db.query(Audit).filter(Audit.id == audit_id).first()
#   results = db.query(AnalysisResult).filter(AnalysisResult.audit_id == audit_id).all()
#
# JANGAN write/update ke Audit atau AnalysisResult — tabel ini milik service lain
