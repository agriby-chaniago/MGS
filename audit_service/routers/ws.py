from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import Audit, AnalysisResultReadOnly
from services import ws_manager

router = APIRouter()


@router.websocket("/ws/audits/{audit_id}")
async def audit_progress_ws(websocket: WebSocket, audit_id: str, db: Session = Depends(get_db)):
    # Nginx's auth_request already authenticated this connection (see
    # nginx.conf's /ws/ location) and forwards the result as X-User-Id —
    # same ownership rule as the REST endpoints (404-equivalent: just
    # close without the caller ever seeing the audit exists).
    x_user_id = websocket.headers.get("x-user-id")
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit or (audit.user_id is not None and str(audit.user_id) != x_user_id):
        await websocket.close(code=4404)
        return

    await ws_manager.connect(audit_id, websocket)

    # Snapshot-then-subscribe (bug found during testing): there is no
    # message replay, so a client that connects AFTER the audit already
    # finished — trivially easy for a tiny/cached dataset, where all 5
    # analyzers can complete before the client's WS handshake round-trip —
    # would otherwise wait forever for events that already fired. Sending
    # the current state immediately on connect closes that race.
    results = db.query(AnalysisResultReadOnly).filter(
        AnalysisResultReadOnly.audit_id == audit_id
    ).all()
    await websocket.send_json({
        "type": "snapshot",
        "audit_status": audit.status,
        "analyzer_statuses": {r.analyzer_type: r.status for r in results},
    })
    if audit.status in ("completed", "failed"):
        await ws_manager.disconnect(audit_id, websocket)
        await websocket.close()
        return

    try:
        while True:
            # No client->server messages expected; awaiting here is just
            # how we detect disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(audit_id, websocket)
