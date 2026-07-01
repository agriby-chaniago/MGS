import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# bcrypt: for low-entropy user passwords only, checked once at login/register.
# Deliberately slow — must NEVER be used for API keys (see hash_api_key below),
# since /internal/verify runs on every gated request.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: str, email: str, plan: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "plan": plan,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    """Returns (raw_key, key_hash). Raw key is shown once, only the hash is stored."""
    raw_key = "mg_live_" + secrets.token_urlsafe(32)
    return raw_key, hash_api_key(raw_key)


def hash_api_key(raw_key: str) -> str:
    # SHA-256, not bcrypt: API keys are already high-entropy random tokens,
    # and this hash is looked up on every single gated request via
    # /internal/verify — bcrypt's deliberate slowness would add ~100-300ms
    # of latency to every API call authenticated this way.
    return hashlib.sha256(raw_key.encode()).hexdigest()
