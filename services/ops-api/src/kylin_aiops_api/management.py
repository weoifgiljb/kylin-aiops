"""注册账号、资源、事件和审计管理接口，并统一执行事务与权限校验。"""

import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import Cookie, Depends, FastAPI, Form, Header, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .auth import ApiProblem, AuthManager, AuthUser, HumanRole, Role
from .database import (
    AuditLogRow,
    DependencyEdgeRow,
    DiagnosisRow,
    EvidenceRow,
    IncidentRow,
    NodeRow,
    ServiceRow,
    UserRow,
)
from .pagination import page_response, page_scalars
from .schemas import (
    AuditLogPage,
    DependencyPage,
    DependencyResponse,
    IncidentPage,
    IncidentResponse,
    NodePage,
    NodeResponse,
    ServicePage,
    ServiceResponse,
    UserPage,
    UserResponse,
)
from .serializers import serialize_incident

CurrentUserDependency = Callable[..., AuthUser]


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,64}$")
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=256)
    role: HumanRole


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    role: HumanRole | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class NodeCreate(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    display_name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    enabled: bool = True


class NodeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=50)
    enabled: bool | None = None


class ServiceCreate(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    node_id: str
    name: str = Field(min_length=1, max_length=128)
    service_type: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=4000)
    enabled: bool = True


class ServiceUpdate(BaseModel):
    node_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=128)
    service_type: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=4000)
    enabled: bool | None = None


class DependencyCreate(BaseModel):
    source_service_id: str
    target_service_id: str


class DependencyUpdate(BaseModel):
    source_service_id: str | None = None
    target_service_id: str | None = None


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    fault_type: str = Field(min_length=1, max_length=64)
    severity: Literal["low", "medium", "high", "critical"]
    root_node_id: str | None = None
    assignee_user_id: str | None = None
    handling_notes: str = Field(default="", max_length=10000)


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    fault_type: str | None = Field(default=None, min_length=1, max_length=64)
    severity: Literal["low", "medium", "high", "critical"] | None = None
    status: Literal["open", "acknowledged", "resolving", "resolved"] | None = None
    root_node_id: str | None = None
    assignee_user_id: str | None = None
    handling_notes: str | None = Field(default=None, max_length=10000)


def register_management_routes(
    app: FastAPI,
    auth: AuthManager,
    sessions: sessionmaker[Session],
    current_user: CurrentUserDependency,
    secure_cookies: bool,
) -> None:
    """把管理路由绑定到应用；闭包确保所有接口共享同一认证与会话工厂。"""

    def require(*roles: Role):
        def dependency(user: Annotated[AuthUser, Depends(current_user)]) -> AuthUser:
            if user.role not in roles:
                raise ApiProblem(403, "INSUFFICIENT_ROLE", "当前角色无权执行该操作")
            return user

        return dependency

    def expected_version(if_match: Annotated[str | None, Header(alias="If-Match")] = None) -> int:
        if if_match is None:
            raise ApiProblem(428, "PRECONDITION_REQUIRED", "写操作必须携带 If-Match 版本")
        value = if_match.strip().removeprefix("W/").strip('"')
        if not value.isdigit():
            raise ApiProblem(422, "INVALID_VERSION", "If-Match 必须是整数版本")
        return int(value)

    def audit(
        session: Session,
        user: AuthUser,
        action: str,
        target: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        session.add(
            AuditLogRow(
                id=str(uuid.uuid4()),
                actor_id=user.id,
                action=action,
                target=target,
                request_id=str(uuid.uuid4()),
                details=details or {},
                created_at=datetime.now(UTC),
            )
        )

    @app.post("/api/v1/auth/token")
    def token(
        response: Response,
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
    ) -> dict[str, Any]:
        client_ip = request.client.host if request.client else "unknown"
        issued = auth.authenticate(username, password, client_ip)
        _set_refresh_cookie(response, issued.refresh_token, secure_cookies)
        return {
            "access_token": issued.access_token,
            "token_type": "bearer",
            "expires_in": issued.expires_in,
        }

    @app.post("/api/v1/auth/refresh")
    def refresh(
        response: Response,
        refresh_token: Annotated[str | None, Cookie()] = None,
    ) -> dict[str, Any]:
        if not refresh_token:
            raise ApiProblem(401, "REFRESH_REQUIRED", "缺少 refresh session")
        issued = auth.refresh(refresh_token)
        _set_refresh_cookie(response, issued.refresh_token, secure_cookies)
        return {
            "access_token": issued.access_token,
            "token_type": "bearer",
            "expires_in": issued.expires_in,
        }

    @app.post("/api/v1/auth/logout", status_code=204)
    def logout(
        response: Response,
        refresh_token: Annotated[str | None, Cookie()] = None,
    ) -> Response:
        auth.revoke_refresh(refresh_token)
        response.delete_cookie("refresh_token", path="/api/v1/auth")
        return response

    @app.get("/api/v1/auth/me")
    def me(user: Annotated[AuthUser, Depends(require("admin", "operator", "viewer"))]) -> AuthUser:
        return user

    @app.get("/api/v1/admin/users", response_model=UserPage)
    def list_users(
        _: Annotated[AuthUser, Depends(require("admin"))],
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        q: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        with sessions() as session:
            statement = select(UserRow)
            if not include_archived:
                statement = statement.where(UserRow.archived_at.is_(None))
            if q:
                statement = statement.where(
                    or_(UserRow.username.contains(q), UserRow.display_name.contains(q))
                )
            result = page_scalars(
                session,
                statement.order_by(UserRow.created_at.desc()),
                page,
                page_size,
            )
            return page_response(
                [_user(row) for row in result.items],
                result.total,
                page,
                page_size,
            )

    @app.post("/api/v1/admin/users", status_code=201, response_model=UserResponse)
    def create_user(
        payload: UserCreate,
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        row = UserRow(
            id=str(uuid.uuid4()),
            username=payload.username,
            display_name=payload.display_name,
            password_hash=auth.passwords.hash(payload.password),
            role=payload.role,
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
            archived_at=None,
            archived_by=None,
        )
        with sessions() as session:
            session.add(row)
            audit(session, actor, "user.created", f"user:{row.id}", {"role": row.role})
            try:
                session.commit()
            except IntegrityError as exc:
                raise ApiProblem(409, "USERNAME_EXISTS", "用户名已经存在") from exc
            return _user(row)

    @app.patch("/api/v1/admin/users/{user_id}", response_model=UserResponse)
    def update_user(
        user_id: str,
        payload: UserUpdate,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, UserRow, user_id, "USER_NOT_FOUND", "用户不存在")
            _check_version(row.version, version)
            changes = payload.model_dump(exclude_unset=True)
            if actor.id == row.id and changes.get("is_active") is False:
                raise ApiProblem(409, "CANNOT_DISABLE_SELF", "不能停用当前登录账号")
            if row.role == "admin" and changes.get("role") not in {None, "admin"}:
                if auth.active_admin_count(session) <= 1:
                    raise ApiProblem(409, "LAST_ADMIN_REQUIRED", "必须保留至少一个有效管理员")
            for key, value in changes.items():
                setattr(row, key, value)
            row.version += 1
            row.updated_at = datetime.now(UTC)
            auth.revoke_user_sessions(session, row.id)
            audit(session, actor, "user.updated", f"user:{row.id}", {"fields": sorted(changes)})
            session.commit()
            return _user(row)

    @app.post(
        "/api/v1/admin/users/{user_id}/reset-password",
        response_model=UserResponse,
    )
    def reset_password(
        user_id: str,
        payload: PasswordReset,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, UserRow, user_id, "USER_NOT_FOUND", "用户不存在")
            _check_version(row.version, version)
            row.password_hash = auth.passwords.hash(payload.password)
            row.version += 1
            row.updated_at = datetime.now(UTC)
            auth.revoke_user_sessions(session, row.id)
            audit(session, actor, "user.password_reset", f"user:{row.id}")
            session.commit()
            return _user(row)

    @app.delete("/api/v1/admin/users/{user_id}", response_model=UserResponse)
    def archive_user(
        user_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, UserRow, user_id, "USER_NOT_FOUND", "用户不存在")
            _check_version(row.version, version)
            if actor.id == row.id:
                raise ApiProblem(409, "CANNOT_DISABLE_SELF", "不能归档当前登录账号")
            if row.role == "admin" and auth.active_admin_count(session) <= 1:
                raise ApiProblem(409, "LAST_ADMIN_REQUIRED", "必须保留至少一个有效管理员")
            _archive(row, actor.id)
            row.is_active = False
            auth.revoke_user_sessions(session, row.id)
            audit(session, actor, "user.archived", f"user:{row.id}")
            session.commit()
            return _user(row)

    @app.post("/api/v1/admin/users/{user_id}/restore", response_model=UserResponse)
    def restore_user(
        user_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, UserRow, user_id, "USER_NOT_FOUND", "用户不存在")
            _check_version(row.version, version)
            _restore(row)
            row.is_active = True
            audit(session, actor, "user.restored", f"user:{row.id}")
            session.commit()
            return _user(row)

    _register_resource_routes(app, sessions, require, expected_version, audit)
    _register_incident_routes(app, sessions, require, expected_version, audit)

    @app.get("/api/v1/audit-logs", response_model=AuditLogPage)
    def audit_logs(
        _: Annotated[AuthUser, Depends(require("admin"))],
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        actor_id: str | None = None,
        action: str | None = None,
        target: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> dict[str, Any]:
        with sessions() as session:
            statement = select(AuditLogRow)
            if actor_id:
                statement = statement.where(AuditLogRow.actor_id == actor_id)
            if action:
                statement = statement.where(AuditLogRow.action == action)
            if target:
                statement = statement.where(AuditLogRow.target.contains(target))
            if created_from:
                statement = statement.where(AuditLogRow.created_at >= created_from)
            if created_to:
                statement = statement.where(AuditLogRow.created_at <= created_to)
            result = page_scalars(
                session,
                statement.order_by(AuditLogRow.created_at.desc()),
                page,
                page_size,
            )
            return page_response(
                [_audit(row) for row in result.items],
                result.total,
                page,
                page_size,
            )


def _register_resource_routes(app, sessions, require, expected_version, audit) -> None:
    @app.get("/api/v1/resources/nodes", response_model=NodePage)
    def nodes(
        _: Annotated[AuthUser, Depends(require("admin"))],
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        q: str | None = None,
        status: str | None = None,
        service_type: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        with sessions() as session:
            statement = select(NodeRow)
            if not include_archived:
                statement = statement.where(NodeRow.archived_at.is_(None))
            if q:
                statement = statement.where(
                    or_(NodeRow.id.contains(q), NodeRow.display_name.contains(q))
                )
            if status:
                statement = statement.where(NodeRow.status == status)
            if service_type:
                statement = statement.where(
                    NodeRow.id.in_(
                        select(ServiceRow.node_id).where(
                            ServiceRow.service_type == service_type,
                            ServiceRow.archived_at.is_(None),
                        )
                    )
                )
            result = page_scalars(session, statement.order_by(NodeRow.id), page, page_size)
            return page_response(
                [_node(row) for row in result.items],
                result.total,
                page,
                page_size,
            )

    @app.post("/api/v1/resources/nodes", status_code=201, response_model=NodeResponse)
    def create_node(
        payload: NodeCreate,
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        row = NodeRow(
            id=payload.id,
            hostname=None,
            architecture=None,
            kylin_version=None,
            status="offline",
            last_seen_at=None,
            display_name=payload.display_name,
            description=payload.description,
            tags=payload.tags,
            enabled=payload.enabled,
            version=1,
            archived_at=None,
            archived_by=None,
        )
        with sessions() as session:
            session.add(row)
            audit(session, actor, "node.created", f"node:{row.id}")
            try:
                session.commit()
            except IntegrityError as exc:
                raise ApiProblem(409, "NODE_EXISTS", "节点标识已经存在") from exc
            return _node(row)

    @app.patch("/api/v1/resources/nodes/{node_id}", response_model=NodeResponse)
    def update_node(
        node_id: str,
        payload: NodeUpdate,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, NodeRow, node_id, "NODE_NOT_FOUND", "节点不存在")
            _check_version(row.version, version)
            changes = payload.model_dump(exclude_unset=True)
            for key, value in changes.items():
                setattr(row, key, value)
            row.version += 1
            audit(session, actor, "node.updated", f"node:{row.id}", {"fields": sorted(changes)})
            session.commit()
            return _node(row)

    @app.delete("/api/v1/resources/nodes/{node_id}", response_model=NodeResponse)
    def archive_node(
        node_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, NodeRow, node_id, "NODE_NOT_FOUND", "节点不存在")
            _check_version(row.version, version)
            has_service = session.scalar(
                select(ServiceRow.id).where(
                    ServiceRow.node_id == node_id, ServiceRow.archived_at.is_(None)
                )
            )
            has_incident = session.scalar(
                select(IncidentRow.id).where(
                    IncidentRow.root_node_id == node_id,
                    IncidentRow.status != "resolved",
                    IncidentRow.archived_at.is_(None),
                )
            )
            if has_service or has_incident:
                raise ApiProblem(409, "NODE_IN_USE", "节点仍有关联的服务或未结束事件")
            _archive(row, actor.id)
            audit(session, actor, "node.archived", f"node:{row.id}")
            session.commit()
            return _node(row)

    @app.post("/api/v1/resources/nodes/{node_id}/restore", response_model=NodeResponse)
    def restore_node(
        node_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, NodeRow, node_id, "NODE_NOT_FOUND", "节点不存在")
            _check_version(row.version, version)
            _restore(row)
            audit(session, actor, "node.restored", f"node:{row.id}")
            session.commit()
            return _node(row)

    @app.get("/api/v1/resources/services", response_model=ServicePage)
    def services(
        _: Annotated[AuthUser, Depends(require("admin"))],
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        q: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        with sessions() as session:
            statement = select(ServiceRow)
            if not include_archived:
                statement = statement.where(ServiceRow.archived_at.is_(None))
            if q:
                statement = statement.where(
                    or_(ServiceRow.id.contains(q), ServiceRow.name.contains(q))
                )
            result = page_scalars(session, statement.order_by(ServiceRow.id), page, page_size)
            return page_response(
                [_service(row) for row in result.items],
                result.total,
                page,
                page_size,
            )

    @app.post(
        "/api/v1/resources/services",
        status_code=201,
        response_model=ServiceResponse,
    )
    def create_service(
        payload: ServiceCreate,
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            _get(session, NodeRow, payload.node_id, "NODE_NOT_FOUND", "所属节点不存在")
            row = ServiceRow(
                id=payload.id,
                node_id=payload.node_id,
                name=payload.name,
                service_type=payload.service_type,
                status="unknown",
                description=payload.description,
                enabled=payload.enabled,
                version=1,
                archived_at=None,
                archived_by=None,
            )
            session.add(row)
            audit(session, actor, "service.created", f"service:{row.id}")
            try:
                session.commit()
            except IntegrityError as exc:
                raise ApiProblem(409, "SERVICE_EXISTS", "服务标识已经存在") from exc
            return _service(row)

    @app.patch("/api/v1/resources/services/{service_id}", response_model=ServiceResponse)
    def update_service(
        service_id: str,
        payload: ServiceUpdate,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, ServiceRow, service_id, "SERVICE_NOT_FOUND", "服务不存在")
            _check_version(row.version, version)
            changes = payload.model_dump(exclude_unset=True)
            if "node_id" in changes:
                _get(session, NodeRow, changes["node_id"], "NODE_NOT_FOUND", "所属节点不存在")
            for key, value in changes.items():
                setattr(row, key, value)
            row.version += 1
            audit(
                session,
                actor,
                "service.updated",
                f"service:{row.id}",
                {"fields": sorted(changes)},
            )
            session.commit()
            return _service(row)

    @app.delete("/api/v1/resources/services/{service_id}", response_model=ServiceResponse)
    def archive_service(
        service_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, ServiceRow, service_id, "SERVICE_NOT_FOUND", "服务不存在")
            _check_version(row.version, version)
            edge = session.scalar(
                select(DependencyEdgeRow.id).where(
                    or_(
                        DependencyEdgeRow.source_service_id == service_id,
                        DependencyEdgeRow.target_service_id == service_id,
                    ),
                    DependencyEdgeRow.archived_at.is_(None),
                )
            )
            if edge:
                raise ApiProblem(409, "SERVICE_IN_USE", "服务仍存在有效依赖关系")
            _archive(row, actor.id)
            audit(session, actor, "service.archived", f"service:{row.id}")
            session.commit()
            return _service(row)

    @app.post(
        "/api/v1/resources/services/{service_id}/restore",
        response_model=ServiceResponse,
    )
    def restore_service(
        service_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, ServiceRow, service_id, "SERVICE_NOT_FOUND", "服务不存在")
            _check_version(row.version, version)
            _restore(row)
            audit(session, actor, "service.restored", f"service:{row.id}")
            session.commit()
            return _service(row)

    @app.get("/api/v1/resources/dependencies", response_model=DependencyPage)
    def dependencies(
        _: Annotated[AuthUser, Depends(require("admin"))],
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        include_archived: bool = False,
    ) -> dict[str, Any]:
        with sessions() as session:
            statement = select(DependencyEdgeRow)
            if not include_archived:
                statement = statement.where(DependencyEdgeRow.archived_at.is_(None))
            result = page_scalars(
                session,
                statement.order_by(DependencyEdgeRow.id),
                page,
                page_size,
            )
            return page_response(
                [_dependency(row) for row in result.items],
                result.total,
                page,
                page_size,
            )

    @app.post(
        "/api/v1/resources/dependencies",
        status_code=201,
        response_model=DependencyResponse,
    )
    def create_dependency(
        payload: DependencyCreate,
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        if payload.source_service_id == payload.target_service_id:
            raise ApiProblem(422, "DEPENDENCY_SELF_REFERENCE", "服务不能依赖自身")
        with sessions() as session:
            _get(
                session,
                ServiceRow,
                payload.source_service_id,
                "SERVICE_NOT_FOUND",
                "源服务不存在",
            )
            _get(
                session,
                ServiceRow,
                payload.target_service_id,
                "SERVICE_NOT_FOUND",
                "目标服务不存在",
            )
            duplicate = session.scalar(
                select(DependencyEdgeRow.id).where(
                    DependencyEdgeRow.source_service_id == payload.source_service_id,
                    DependencyEdgeRow.target_service_id == payload.target_service_id,
                    DependencyEdgeRow.archived_at.is_(None),
                )
            )
            if duplicate:
                raise ApiProblem(409, "DEPENDENCY_EXISTS", "依赖关系已经存在")
            row = DependencyEdgeRow(
                source_service_id=payload.source_service_id,
                target_service_id=payload.target_service_id,
                source="manual",
                confidence=1.0,
                observed_at=datetime.now(UTC),
                version=1,
                archived_at=None,
                archived_by=None,
            )
            session.add(row)
            session.flush()
            audit(session, actor, "dependency.created", f"dependency:{row.id}")
            session.commit()
            return _dependency(row)

    @app.delete(
        "/api/v1/resources/dependencies/{dependency_id}",
        response_model=DependencyResponse,
    )
    def archive_dependency(
        dependency_id: int,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(
                session,
                DependencyEdgeRow,
                dependency_id,
                "DEPENDENCY_NOT_FOUND",
                "依赖关系不存在",
            )
            _check_version(row.version, version)
            if row.source != "manual":
                raise ApiProblem(403, "DISCOVERED_DEPENDENCY_READ_ONLY", "自动发现依赖不可人工修改")
            _archive(row, actor.id)
            audit(session, actor, "dependency.archived", f"dependency:{row.id}")
            session.commit()
            return _dependency(row)

    @app.patch(
        "/api/v1/resources/dependencies/{dependency_id}",
        response_model=DependencyResponse,
    )
    def update_dependency(
        dependency_id: int,
        payload: DependencyUpdate,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(
                session,
                DependencyEdgeRow,
                dependency_id,
                "DEPENDENCY_NOT_FOUND",
                "依赖关系不存在",
            )
            _check_version(row.version, version)
            if row.source != "manual":
                raise ApiProblem(403, "DISCOVERED_DEPENDENCY_READ_ONLY", "自动发现依赖不可人工修改")
            changes = payload.model_dump(exclude_unset=True)
            source_id = changes.get("source_service_id", row.source_service_id)
            target_id = changes.get("target_service_id", row.target_service_id)
            if source_id == target_id:
                raise ApiProblem(422, "DEPENDENCY_SELF_REFERENCE", "服务不能依赖自身")
            _get(session, ServiceRow, source_id, "SERVICE_NOT_FOUND", "源服务不存在")
            _get(session, ServiceRow, target_id, "SERVICE_NOT_FOUND", "目标服务不存在")
            duplicate = session.scalar(
                select(DependencyEdgeRow.id).where(
                    DependencyEdgeRow.source_service_id == source_id,
                    DependencyEdgeRow.target_service_id == target_id,
                    DependencyEdgeRow.archived_at.is_(None),
                    DependencyEdgeRow.id != row.id,
                )
            )
            if duplicate:
                raise ApiProblem(409, "DEPENDENCY_EXISTS", "依赖关系已经存在")
            row.source_service_id = source_id
            row.target_service_id = target_id
            row.version += 1
            audit(
                session,
                actor,
                "dependency.updated",
                f"dependency:{row.id}",
                {"fields": sorted(changes)},
            )
            session.commit()
            return _dependency(row)

    @app.post(
        "/api/v1/resources/dependencies/{dependency_id}/restore",
        response_model=DependencyResponse,
    )
    def restore_dependency(
        dependency_id: int,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(
                session,
                DependencyEdgeRow,
                dependency_id,
                "DEPENDENCY_NOT_FOUND",
                "依赖关系不存在",
            )
            _check_version(row.version, version)
            if row.source != "manual":
                raise ApiProblem(403, "DISCOVERED_DEPENDENCY_READ_ONLY", "自动发现依赖不可人工修改")
            _restore(row)
            audit(session, actor, "dependency.restored", f"dependency:{row.id}")
            session.commit()
            return _dependency(row)


def _register_incident_routes(app, sessions, require, expected_version, audit) -> None:
    @app.get("/api/v1/incidents", response_model=IncidentPage)
    def incidents(
        _: Annotated[AuthUser, Depends(require("admin", "operator", "viewer"))],
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: str | None = None,
        source: str | None = None,
        severity: str | None = None,
        q: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        normalized_started_from = (
            _query_time_as_utc(started_from, "started_from") if started_from else None
        )
        normalized_started_to = _query_time_as_utc(started_to, "started_to") if started_to else None
        with sessions() as session:
            statement = select(IncidentRow)
            if not include_archived:
                statement = statement.where(IncidentRow.archived_at.is_(None))
            if status:
                statement = statement.where(IncidentRow.status == status)
            if source:
                statement = statement.where(IncidentRow.source == source)
            if severity:
                statement = statement.where(IncidentRow.severity == severity)
            if q:
                statement = statement.where(
                    or_(IncidentRow.title.contains(q), IncidentRow.root_node_id.contains(q))
                )
            if normalized_started_from:
                statement = statement.where(IncidentRow.started_at >= normalized_started_from)
            if normalized_started_to:
                statement = statement.where(IncidentRow.started_at <= normalized_started_to)
            result = page_scalars(
                session,
                statement.order_by(IncidentRow.started_at.desc(), IncidentRow.id.desc()),
                page,
                page_size,
            )
            if not result.items:
                return page_response([], result.total, page, page_size)
            incident_ids = [row.id for row in result.items]
            evidence_by_incident: dict[str, list[EvidenceRow]] = defaultdict(list)
            for evidence in session.scalars(
                select(EvidenceRow).where(EvidenceRow.incident_id.in_(incident_ids))
            ):
                evidence_by_incident[evidence.incident_id].append(evidence)
            diagnosis_by_incident = {
                diagnosis.incident_id: diagnosis
                for diagnosis in session.scalars(
                    select(DiagnosisRow).where(DiagnosisRow.incident_id.in_(incident_ids))
                )
            }
            items = [
                serialize_incident(
                    row,
                    evidence_by_incident[row.id],
                    diagnosis_by_incident.get(row.id),
                )
                for row in result.items
            ]
            return page_response(items, result.total, page, page_size)

    @app.get("/api/v1/incidents/{incident_id}", response_model=IncidentResponse)
    def incident(
        incident_id: str,
        _: Annotated[AuthUser, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, IncidentRow, incident_id, "INCIDENT_NOT_FOUND", "事件不存在")
            return _incident(row, session)

    @app.post("/api/v1/incidents", status_code=201, response_model=IncidentResponse)
    def create_incident(
        payload: IncidentCreate,
        actor: Annotated[AuthUser, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        row = IncidentRow(
            id=f"inc-manual-{uuid.uuid4().hex[:16]}",
            title=payload.title,
            fault_type=payload.fault_type,
            severity=payload.severity,
            status="open",
            started_at=now,
            ended_at=None,
            root_node_id=payload.root_node_id,
            source="manual",
            assignee_user_id=payload.assignee_user_id,
            handling_notes=payload.handling_notes,
            version=1,
            archived_at=None,
            archived_by=None,
        )
        with sessions() as session:
            if payload.root_node_id:
                _get(session, NodeRow, payload.root_node_id, "NODE_NOT_FOUND", "根节点不存在")
            session.add(row)
            audit(session, actor, "incident.created", f"incident:{row.id}")
            session.commit()
            return _incident(row, session)

    @app.patch("/api/v1/incidents/{incident_id}", response_model=IncidentResponse)
    def update_incident(
        incident_id: str,
        payload: IncidentUpdate,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, IncidentRow, incident_id, "INCIDENT_NOT_FOUND", "事件不存在")
            _check_version(row.version, version)
            changes = payload.model_dump(exclude_unset=True)
            immutable_alert_fields = {"title", "fault_type", "root_node_id"}
            if row.source == "alert" and immutable_alert_fields.intersection(changes):
                raise ApiProblem(422, "ALERT_FIELDS_IMMUTABLE", "自动告警的原始字段不可修改")
            if changes.get("root_node_id"):
                _get(session, NodeRow, changes["root_node_id"], "NODE_NOT_FOUND", "根节点不存在")
            for key, value in changes.items():
                setattr(row, key, value)
            if row.status == "resolved" and row.ended_at is None:
                row.ended_at = datetime.now(UTC)
            if row.status != "resolved":
                row.ended_at = None
            row.version += 1
            audit(
                session,
                actor,
                "incident.updated",
                f"incident:{row.id}",
                {"fields": sorted(changes)},
            )
            session.commit()
            return _incident(row, session)

    @app.delete("/api/v1/incidents/{incident_id}", response_model=IncidentResponse)
    def archive_incident(
        incident_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, IncidentRow, incident_id, "INCIDENT_NOT_FOUND", "事件不存在")
            _check_version(row.version, version)
            if row.status != "resolved":
                raise ApiProblem(409, "INCIDENT_NOT_RESOLVED", "事件结束后才能归档")
            if row.source == "alert" and actor.role != "admin":
                raise ApiProblem(403, "INSUFFICIENT_ROLE", "只有管理员可以归档自动事件")
            _archive(row, actor.id)
            audit(session, actor, "incident.archived", f"incident:{row.id}")
            session.commit()
            return _incident(row, session)

    @app.post(
        "/api/v1/incidents/{incident_id}/restore",
        response_model=IncidentResponse,
    )
    def restore_incident(
        incident_id: str,
        version: Annotated[int, Depends(expected_version)],
        actor: Annotated[AuthUser, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        with sessions() as session:
            row = _get(session, IncidentRow, incident_id, "INCIDENT_NOT_FOUND", "事件不存在")
            _check_version(row.version, version)
            if row.source == "alert" and actor.role != "admin":
                raise ApiProblem(403, "INSUFFICIENT_ROLE", "只有管理员可以恢复自动事件")
            _restore(row)
            audit(session, actor, "incident.restored", f"incident:{row.id}")
            session.commit()
            return _incident(row, session)


def _set_refresh_cookie(response: Response, token: str, secure: bool) -> None:
    response.set_cookie(
        "refresh_token",
        token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/api/v1/auth",
    )


def _check_version(actual: int, expected: int) -> None:
    if actual != expected:
        raise ApiProblem(
            409,
            "VERSION_CONFLICT",
            "数据已被其他用户更新，请刷新后重试",
            {"current_version": actual},
        )


def _archive(row: Any, actor_id: str) -> None:
    if row.archived_at is None:
        row.archived_at = datetime.now(UTC)
        row.archived_by = actor_id
        row.version += 1


def _restore(row: Any) -> None:
    if row.archived_at is not None:
        row.archived_at = None
        row.archived_by = None
        row.version += 1


def _get(session: Session, model, key, code: str, message: str):
    row = session.get(model, key)
    if row is None:
        raise ApiProblem(404, code, message)
    return row


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _query_time_as_utc(value: datetime, field_name: str) -> datetime:
    """将带时区的查询时间归一化为 UTC，避免 SQLite 与 PostgreSQL 比较语义不一致。"""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ApiProblem(422, "TIMEZONE_REQUIRED", f"{field_name} 必须包含时区偏移")
    return value.astimezone(UTC)


def _user(row: UserRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "username": row.username,
        "display_name": row.display_name,
        "role": row.role,
        "is_active": row.is_active,
        "version": row.version,
        "created_at": _dt(row.created_at),
        "updated_at": _dt(row.updated_at),
        "archived_at": _dt(row.archived_at),
    }


def _node(row: NodeRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "display_name": row.display_name,
        "description": row.description,
        "tags": row.tags or [],
        "enabled": row.enabled,
        "hostname": row.hostname,
        "architecture": row.architecture,
        "kylin_version": row.kylin_version,
        "status": row.status,
        "last_seen_at": _dt(row.last_seen_at),
        "version": row.version,
        "archived_at": _dt(row.archived_at),
    }


def _service(row: ServiceRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "node_id": row.node_id,
        "name": row.name,
        "service_type": row.service_type,
        "description": row.description,
        "enabled": row.enabled,
        "status": row.status,
        "version": row.version,
        "archived_at": _dt(row.archived_at),
    }


def _dependency(row: DependencyEdgeRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "source_service_id": row.source_service_id,
        "target_service_id": row.target_service_id,
        "source": row.source,
        "confidence": row.confidence,
        "observed_at": _dt(row.observed_at),
        "version": row.version,
        "archived_at": _dt(row.archived_at),
    }


def _incident(row: IncidentRow, session: Session) -> dict[str, Any]:
    evidence_rows = list(
        session.scalars(select(EvidenceRow).where(EvidenceRow.incident_id == row.id))
    )
    diagnosis = session.scalar(select(DiagnosisRow).where(DiagnosisRow.incident_id == row.id))
    return serialize_incident(row, evidence_rows, diagnosis)


def _audit(row: AuditLogRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "actor_id": row.actor_id,
        "action": row.action,
        "target": row.target,
        "request_id": row.request_id,
        "details": row.details,
        "created_at": _dt(row.created_at),
    }
