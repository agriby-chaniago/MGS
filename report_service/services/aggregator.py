from uuid import UUID
from sqlalchemy.orm import Session
from models.orm import Audit, AnalysisResult
from services.health_score import calculate_health_score


def get_report_data(audit_id: UUID, db: Session) -> dict | None:
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        return None

    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.audit_id == audit_id)
        .order_by(AnalysisResult.completed_at)
        .all()
    )

    results_data = [
        {
            "analyzer_type": r.analyzer_type,
            "status": r.status,
            "result_payload": r.result_payload,
            "error_message": r.error_message,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in results
    ]

    health = None
    if audit.status == "completed" and results_data:
        health = calculate_health_score(results_data)

    return {
        "audit_id": str(audit.id),
        "dataset_id": str(audit.dataset_id),
        "audit_status": audit.status,
        "health_score": health["score"] if health else None,
        "grade": health["grade"] if health else None,
        "components": health["components"] if health else None,
        "analysis_results": results_data,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
    }
