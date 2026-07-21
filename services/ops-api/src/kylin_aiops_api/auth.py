"""提供本地账号、JWT 和可撤销 refresh session 的认证边界。"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .database import AgentCredentialRow, AuthSessionRow, UserRow

Role = Literal["admin", "operator", "viewer", "agent"]
HumanRole = Literal["admin", "operator", "viewer"]


class AuthUser(BaseModel):
    id: str
    role: Role
    username: str | None = None
    display_name: str | None = None


class ApiProblem(Exception):
    """把可预期业务拒绝转换为统一 API 错误结构。"""

    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.details = details if details is not None else {}


@dataclass(frozen=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    expires_in: int


class LoginRateLimiter:
    """优先使用 Redis 共享失败计数，本地模式退化为进程内限流。"""

    def __init__(self, redis_client: Any | None = None) -> None:
        self.redis = redis_client
        self.attempts: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        if self.redis is not None:
            count = int(self.redis.get(key) or 0)
            if count >= 5:
                raise ApiProblem(429, "LOGIN_RATE_LIMITED", "登录尝试过于频繁，请稍后再试")
            return
        now = time.monotonic()
        recent = [item for item in self.attempts.get(key, []) if now - item < 600]
        self.attempts[key] = recent
        if len(recent) >= 5:
            raise ApiProblem(429, "LOGIN_RATE_LIMITED", "登录尝试过于频繁，请稍后再试")

    def fail(self, key: str) -> None:
        if self.redis is not None:
            value = self.redis.incr(key)
            if value == 1:
                self.redis.expire(key, 600)
            return
        self.attempts.setdefault(key, []).append(time.monotonic())

    def clear(self, key: str) -> None:
        if self.redis is not None:
            self.redis.delete(key)
        self.attempts.pop(key, None)


class AuthManager:
    """封装密码校验、JWT 签发和 refresh session 轮换。"""

    ACCESS_SECONDS = 30 * 60
    REFRESH_DAYS = 7

    def __init__(self, database_url: str, jwt_secret: str, redis_client: Any | None = None) -> None:
        if len(jwt_secret.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET 至少需要 32 字节")
        self.engine = create_engine(database_url)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.jwt_secret = jwt_secret
        self.passwords = PasswordHash.recommended()
        self.limiter = LoginRateLimiter(redis_client)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def authenticate(self, username: str, password: str, client_ip: str) -> IssuedSession:
        key = f"auth:login:{hashlib.sha256(f'{username}:{client_ip}'.encode()).hexdigest()}"
        self.limiter.check(key)
        with self.sessions() as session:
            user = session.scalar(select(UserRow).where(UserRow.username == username))
            if (
                user is None
                or not user.is_active
                or user.archived_at is not None
                or not self.passwords.verify(password, user.password_hash)
            ):
                self.limiter.fail(key)
                raise ApiProblem(401, "INVALID_CREDENTIALS", "用户名或密码错误")
            self.limiter.clear(key)
            return self._issue_session(session, user)

    def _issue_session(self, session: Session, user: UserRow) -> IssuedSession:
        now = datetime.now(UTC)
        session_id = str(uuid.uuid4())
        refresh_token = secrets.token_urlsafe(48)
        session.add(
            AuthSessionRow(
                id=session_id,
                user_id=user.id,
                refresh_token_hash=self.hash_refresh_token(refresh_token),
                expires_at=now + timedelta(days=self.REFRESH_DAYS),
                revoked_at=None,
                created_at=now,
                last_used_at=None,
            )
        )
        access_token = jwt.encode(
            {
                "sub": user.id,
                "role": user.role,
                "ver": user.version,
                "sid": session_id,
                "iat": now,
                "exp": now + timedelta(seconds=self.ACCESS_SECONDS),
            },
            self.jwt_secret,
            algorithm="HS256",
        )
        session.commit()
        return IssuedSession(access_token, refresh_token, self.ACCESS_SECONDS)

    def current_user(self, token: str) -> AuthUser:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise ApiProblem(401, "INVALID_TOKEN", "访问令牌无效或已过期") from exc
        with self.sessions() as session:
            user = session.get(UserRow, payload.get("sub"))
            auth_session = session.get(AuthSessionRow, payload.get("sid"))
            if (
                user is None
                or auth_session is None
                or auth_session.revoked_at is not None
                or not user.is_active
                or user.archived_at is not None
                or payload.get("ver") != user.version
            ):
                raise ApiProblem(401, "SESSION_REVOKED", "登录会话已失效")
            return AuthUser(
                id=user.id,
                role=user.role,
                username=user.username,
                display_name=user.display_name,
            )

    def refresh(self, refresh_token: str) -> IssuedSession:
        now = datetime.now(UTC)
        token_hash = self.hash_refresh_token(refresh_token)
        with self.sessions() as session:
            old = session.scalar(
                select(AuthSessionRow).where(AuthSessionRow.refresh_token_hash == token_hash)
            )
            if old is None or old.revoked_at is not None or _as_utc(old.expires_at) <= now:
                raise ApiProblem(401, "INVALID_REFRESH_TOKEN", "refresh session 无效或已过期")
            user = session.get(UserRow, old.user_id)
            if user is None or not user.is_active or user.archived_at is not None:
                raise ApiProblem(401, "SESSION_REVOKED", "登录会话已失效")
            old.revoked_at = now
            old.last_used_at = now
            session.flush()
            return self._issue_session(session, user)

    def revoke_refresh(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        with self.sessions() as session:
            row = session.scalar(
                select(AuthSessionRow).where(
                    AuthSessionRow.refresh_token_hash == self.hash_refresh_token(refresh_token)
                )
            )
            if row is not None and row.revoked_at is None:
                row.revoked_at = datetime.now(UTC)
                session.commit()

    def revoke_user_sessions(self, session: Session, user_id: str) -> None:
        now = datetime.now(UTC)
        for row in session.scalars(
            select(AuthSessionRow).where(
                AuthSessionRow.user_id == user_id,
                AuthSessionRow.revoked_at.is_(None),
            )
        ):
            row.revoked_at = now

    def issue_agent_credential(self, node_id: str) -> str:
        """为节点轮换独立凭证，并只把摘要保存到数据库。"""

        token = secrets.token_urlsafe(48)
        now = datetime.now(UTC)
        with self.sessions() as session:
            for row in session.scalars(
                select(AgentCredentialRow).where(
                    AgentCredentialRow.node_id == node_id,
                    AgentCredentialRow.revoked_at.is_(None),
                )
            ):
                row.revoked_at = now
            session.add(
                AgentCredentialRow(
                    id=str(uuid.uuid4()),
                    node_id=node_id,
                    token_hash=self.hash_refresh_token(token),
                    created_at=now,
                    revoked_at=None,
                )
            )
            session.commit()
        return token

    def current_agent(self, token: str) -> AuthUser | None:
        """校验持久化 Agent 凭证，并返回与唯一节点绑定的身份。"""

        with self.sessions() as session:
            row = session.scalar(
                select(AgentCredentialRow).where(
                    AgentCredentialRow.token_hash == self.hash_refresh_token(token),
                    AgentCredentialRow.revoked_at.is_(None),
                )
            )
            if row is None:
                return None
            return AuthUser(id=f"agent:{row.node_id}", role="agent")

    def active_admin_count(self, session: Session) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(UserRow)
                .where(
                    UserRow.role == "admin",
                    UserRow.is_active.is_(True),
                    UserRow.archived_at.is_(None),
                )
            )
            or 0
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def seed_admin(database_url: str, username: str, password: str, display_name: str) -> str:
    """创建首个管理员；重复用户名会被明确拒绝，避免静默覆盖密码。"""

    engine = create_engine(database_url)
    now = datetime.now(UTC)
    with Session(engine) as session:
        if session.scalar(select(UserRow).where(UserRow.username == username)) is not None:
            raise ValueError("管理员用户名已存在")
        user_id = str(uuid.uuid4())
        session.add(
            UserRow(
                id=user_id,
                username=username,
                display_name=display_name,
                password_hash=PasswordHash.recommended().hash(password),
                role="admin",
                is_active=True,
                version=1,
                created_at=now,
                updated_at=now,
                archived_at=None,
                archived_by=None,
            )
        )
        session.commit()
        return user_id
