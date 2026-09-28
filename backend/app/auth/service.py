import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.config import settings
from app.models import RefreshToken, User


class AuthError(Exception):
    pass


class DuplicateUsernameError(Exception):
    pass


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("invalid username or password")
    return user


def issue_token_pair(db: Session, user: User) -> tuple[str, str]:
    access_token = create_access_token(subject=str(user.id))

    jti = str(uuid.uuid4())
    refresh_token = create_refresh_token(subject=str(user.id), jti=jti)
    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    db.commit()
    return access_token, refresh_token


def refresh_access_token(db: Session, refresh_token: str | None) -> str:
    if not refresh_token:
        raise AuthError("missing refresh token")
    try:
        payload = decode_token(refresh_token)
    except Exception as exc:
        raise AuthError("invalid or expired refresh token") from exc

    if payload.get("type") != "refresh":
        raise AuthError("not a refresh token")

    record = db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).first()
    if record is None or record.revoked_at is not None:
        raise AuthError("refresh token has been revoked")
    if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise AuthError("refresh token expired")

    return create_access_token(subject=payload["sub"])


def revoke_refresh_token(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token)
    except Exception:
        return
    record = db.query(RefreshToken).filter(RefreshToken.jti == payload.get("jti")).first()
    if record is not None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()
