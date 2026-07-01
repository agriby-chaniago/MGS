from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import ApiKey, User
from services.security import decode_access_token, hash_api_key

router = APIRouter(prefix="/internal")


def _token_from_original_uri(x_original_uri: str | None) -> str | None:
    # Nginx's auth_request module runs this endpoint as a subrequest whose
    # own URI has no query string — the WebSocket handshake's ?token=...
    # (browsers can't set custom headers on a WS upgrade) only survives via
    # X-Original-URI, which nginx.conf sets to $request_uri (always the
    # ORIGINAL client request, unlike subrequest args).
    if not x_original_uri:
        return None
    query = urlparse(x_original_uri).query
    values = parse_qs(query).get("token")
    return values[0] if values else None


def _verify_jwt(token: str, db: Session) -> tuple[str, str] | None:
    payload = decode_access_token(token)
    if not payload:
        return None
    # Trust the JWT's own plan claim (no DB round-trip) — this is the whole
    # point of using a stateless token; /upgrade re-issues a fresh token so
    # staleness is bounded to JWT_EXPIRE_MINUTES, which is an accepted
    # demo-scope limitation (see plan's Known Limitations).
    return payload["sub"], payload["plan"]


def _verify_api_key(raw_key: str, db: Session) -> tuple[str, str] | None:
    key_hash = hash_api_key(raw_key)
    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash, ApiKey.revoked.is_(False)
    ).first()
    if not api_key:
        return None
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        return None
    # Always reflects the user's *current* plan (unlike a JWT, an API key
    # carries no baked-in claim, so this stays correct even right after
    # an /upgrade with no re-issue needed).
    return str(user.id), user.plan


@router.get("/verify")
def verify(
    response: Response,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_original_uri: str | None = Header(default=None, alias="X-Original-URI"),
    token: str | None = None,
    db: Session = Depends(get_db),
):
    # Checked in priority order: Bearer JWT header, X-API-Key header, then
    # a ?token= query param — either passed directly (curl/testing) or via
    # X-Original-URI (real Nginx auth_request subrequests for /ws/, since
    # browsers cannot set custom headers on a WebSocket handshake).
    result = None
    ws_token = token or _token_from_original_uri(x_original_uri)

    if authorization and authorization.lower().startswith("bearer "):
        result = _verify_jwt(authorization.split(" ", 1)[1], db)
    elif x_api_key:
        result = _verify_api_key(x_api_key, db)
    elif ws_token:
        # The WS query-param fallback carries whatever credential the
        # client has — the browser (React) always holds a JWT, but the
        # `mgs` CLI only ever holds an API key (no login flow). Try both
        # rather than assuming JWT, since it's just an opaque string here.
        result = _verify_jwt(ws_token, db) or _verify_api_key(ws_token, db)

    if not result:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id, plan = result
    response.headers["X-User-Id"] = user_id
    response.headers["X-User-Plan"] = plan
    return {"user_id": user_id, "plan": plan}
