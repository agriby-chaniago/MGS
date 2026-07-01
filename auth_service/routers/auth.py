from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from models.orm import ApiKey, User
from models.schemas import (
    ApiKeyCreatedResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpgradeRequest,
    UserSchema,
)
from services.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from shared.response import success_response

router = APIRouter(prefix="/api/v1/auth")

SERVICE_NAME = "auth_service"


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token tidak valid atau sudah kedaluwarsa")
    user = db.query(User).filter(User.id == UUID(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    return user


@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

    user = User(email=body.email, password_hash=hash_password(body.password), plan="free")
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), user.email, user.plan)
    return success_response(
        data=TokenResponse(access_token=token, plan=user.plan).model_dump(),
        service=SERVICE_NAME,
    )


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password salah")

    token = create_access_token(str(user.id), user.email, user.plan)
    return success_response(
        data=TokenResponse(access_token=token, plan=user.plan).model_dump(),
        service=SERVICE_NAME,
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserSchema.model_validate(current_user).model_dump(),
        service=SERVICE_NAME,
    )


@router.post("/upgrade")
def upgrade(
    body: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Demo-only self-service upgrade, no payment — see plan Workstream A for rationale:
    # without this, there is no way to ever have a non-free test account.
    current_user.plan = body.plan
    db.commit()
    db.refresh(current_user)

    token = create_access_token(str(current_user.id), current_user.email, current_user.plan)
    return success_response(
        data=TokenResponse(access_token=token, plan=current_user.plan).model_dump(),
        service=SERVICE_NAME,
    )


@router.post("/api-keys", status_code=201)
def create_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.plan not in ("pro", "max"):
        raise HTTPException(status_code=403, detail="API key hanya untuk paket Pro/Max")

    raw_key, key_hash = generate_api_key()
    api_key = ApiKey(user_id=current_user.id, key_hash=key_hash)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return success_response(
        data=ApiKeyCreatedResponse(
            id=api_key.id, api_key=raw_key, plan=current_user.plan
        ).model_dump(),
        service=SERVICE_NAME,
    )
