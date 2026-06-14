from datetime import datetime, timezone

VALID_TRANSITIONS = {
    "pending":    ["queued"],
    "queued":     ["processing"],
    "processing": ["completed", "failed"],
}


def transition(audit, new_status: str, db):
    if new_status not in VALID_TRANSITIONS.get(audit.status, []):
        raise ValueError(f"Invalid transition: {audit.status} → {new_status}")
    audit.status = new_status
    if new_status in ("completed", "failed"):
        audit.completed_at = datetime.now(timezone.utc)
    # Tidak ada db.commit() — caller yang commit
    # Supaya Fase 3 bisa atomic: transition + db.add(AnalysisResult) + satu commit
    return audit
