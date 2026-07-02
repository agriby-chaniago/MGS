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
        "user_id": str(audit.user_id) if audit.user_id else None,
        "audit_status": audit.status,
        "health_score": health["score"] if health else None,
        "grade": health["grade"] if health else None,
        "components": health["components"] if health else None,
        # So the UI can tell "component defaulted to neutral because its
        # analyzer wasn't requested for this tier" apart from "genuinely
        # scored 1.0" — see health_score.py's neutral-default gap found
        # while preparing demo screenshots (free tier skips duplicate/
        # distribution, but the score still showed them as a perfect 1.0
        # with no indication they were never actually checked).
        "requested_analyzers": audit.requested_analyzers,
        "analysis_results": results_data,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
    }
