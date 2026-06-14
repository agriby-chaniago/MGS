from fastapi import APIRouter

router = APIRouter()

# TODO (Humam - Fase 3):
# GET /api/v1/reports/{audit_id}          → report lengkap
# GET /api/v1/reports/{audit_id}/summary  → health_score + grade saja
#
# Query dari:
#   audit_svc.audits         → audit info
#   analysis_svc.analysis_results → per-analyzer results
