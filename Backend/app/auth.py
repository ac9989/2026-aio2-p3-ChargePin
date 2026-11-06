"""Server-side login and short-lived role sessions for the demo environment."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hmac
import os
import secrets
from threading import Lock

from fastapi import HTTPException


KST = timezone(timedelta(hours=9))
SESSION_TTL_HOURS = 4
ROLE_KEYS = {
    "GUEST": "CUSTOMER_SERVICE_KEY",
    "JUNIOR_ADMIN": "LOW_MANAGER_SERVICE_KEY",
    "SENIOR_ADMIN": "HIGH_MANAGER_SERVICE_KEY",
}


@dataclass(frozen=True)
class AuthSession:
    role: str
    expires_at: datetime
    session_ref: str


def _secret(name: str) -> str:
    """Accept values with optional quotes or whitespace, without ever returning them to a response."""
    value = os.environ.get(name, "").strip()
    if len(value) >= 2 and value[:1] == value[-1:] and value[:1] in {'"', "'"}:
        return value[1:-1].strip()
    return value


class SessionAuthenticator:
    def __init__(self) -> None:
        self._sessions: dict[str, AuthSession] = {}
        self._lock = Lock()

    def login(self, submitted_key: str) -> tuple[str, AuthSession]:
        candidate = submitted_key.strip()
        role = next(
            (
                role_name
                for role_name, env_name in ROLE_KEYS.items()
                if _secret(env_name) and hmac.compare_digest(_secret(env_name), candidate)
            ),
            None,
        )
        if role is None:
            raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")
        session = AuthSession(
            role=role,
            expires_at=datetime.now(KST) + timedelta(hours=SESSION_TTL_HOURS),
            # This is a server-only reference for short-lived chat context, not the access token.
            session_ref=secrets.token_urlsafe(16),
        )
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions = {value: saved for value, saved in self._sessions.items() if saved.expires_at > datetime.now(KST)}
            self._sessions[token] = session
        return token, session

    def require(self, authorization: str | None) -> AuthSession:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="로그인이 필요하거나 세션이 만료되었습니다.")
        token = authorization.removeprefix("Bearer ").strip()
        with self._lock:
            session = self._sessions.get(token)
        if session is None or session.expires_at <= datetime.now(KST):
            raise HTTPException(status_code=401, detail="로그인이 필요하거나 세션이 만료되었습니다.")
        return session
