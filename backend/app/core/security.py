from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: UUID, token_version: int = 0, *, purpose: str | None = None, request_id: str | None = None) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    claims = {"sub": str(user_id), "ver": token_version, "exp": expires_at}
    if purpose:
        claims["purpose"] = purpose
    if request_id:
        claims["rid"] = request_id
    return jwt.encode(
        claims,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
