"""提供事件、Agent、受控动作、运行状态和管理能力的 FastAPI 入口。"""

import asyncio
import os
import re
import secrets
import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from kylin_aiops_diagnosis.mindie import MindIEClient
from pydantic import BaseModel, Field, ValidationError
from redis import Redis
from sqlalchemy.orm.exc import StaleDataError

from .actions import ActionSigner, ApprovalError, create_action_request
from .auth import ApiProblem, AuthManager, Role
from .auth import AuthUser as User
from .management import register_management_routes
from .persistence import Database
from .queue import ActionQueue, InMemoryActionQueue, RedisActionQueue
from .schemas import (
    ActionResponse,
    ActionResult,
    AlertWebhook,
    DiagnosisResponse,
    Enrollment,
    OverviewResponse,
)
from .sql_store import SqlControlPlaneStore
from .status import RuntimeStatusProbe, SystemStatus
from .store import InMemoryStore


class ActionPreview(BaseModel):
    node_id: str
    action_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class TelemetryBatch(BaseModel):
    node_id: str
    observed_at: datetime
    metrics: dict[str, float]


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    incident_id: str | None = None


class GeneratedEvaluationReport(BaseModel):
    """约束 generate_report.py 产物中可以作为实测证据公开的字段。"""

    trial_count: int = Field(ge=0)
    metrics: dict[str, float]
    thresholds: dict[str, float]
    passed: bool
    seed: int | None = None
    code_revision: str | None = None
    model_sha256: str | None = None


def read_evaluation_report(path: Path) -> dict[str, Any]:
    """读取并校验评测报告，防止把不完整文件作为实测证据公开。"""

    report = GeneratedEvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))
    return report.model_dump(exclude_none=True)


TOKENS: dict[str, User] = {
    "dev-admin-token": User(id="admin-1", role="admin"),
    "dev-operator-token": User(id="operator-1", role="operator"),
    "dev-viewer-token": User(id="viewer-1", role="viewer"),
    "dev-agent-token": User(id="agent-1", role="agent"),
}

ACTION_RULES: dict[str, dict[str, Any]] = {
    "restart_demo_service": {"nodes": {"app-01"}, "fixed": {"service": "kylin-demo-app"}},
    "reload_nginx": {"nodes": {"web-01"}, "fixed": {"service": "nginx"}},
    "stop_fault_stressor": {"nodes": {"web-01", "app-01", "db-01"}},
    "remove_fault_file": {"nodes": {"web-01", "app-01", "db-01"}},
    "clear_fault_netem": {"nodes": {"app-01"}},
    "terminate_fault_db_sessions": {"nodes": {"db-01"}, "fixed": {"db_user": "ops_fault"}},
}
SAFE_EXPERIMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SAFE_INTERFACE = re.compile(r"^(eth|ens|enp)[A-Za-z0-9_.-]{1,31}$")


def valid_action_parameters(action_name: str, parameters: dict[str, Any]) -> bool:
    fixed = ACTION_RULES[action_name].get("fixed")
    if fixed is not None:
        return parameters == fixed
    experiment_id = str(parameters.get("experiment_id", ""))
    if not SAFE_EXPERIMENT_ID.fullmatch(experiment_id):
        return False
    if action_name == "stop_fault_stressor":
        return set(parameters) == {"experiment_id"}
    if action_name == "remove_fault_file":
        return (
            set(parameters) == {"experiment_id", "filename"}
            and parameters.get("filename") == "disk-fill.bin"
        )
    if action_name == "clear_fault_netem":
        return set(parameters) == {"experiment_id", "interface"} and bool(
            SAFE_INTERFACE.fullmatch(str(parameters.get("interface", "")))
        )
    return False


def _validate_school_test_config(
    database_url: str | None,
    redis_url: str | None,
    jwt_secret: str,
    action_secret: str,
    agent_bootstrap_token: str | None,
    cookie_secure: bool,
) -> None:
    """校内多人模式必须具备共享存储和强秘密，避免误用单机降级配置。"""

    if os.getenv("APP_ENV") != "school_test":
        return
    required = {
        "DATABASE_URL": database_url,
        "REDIS_URL": redis_url,
        "JWT_SECRET": jwt_secret if len(jwt_secret.encode("utf-8")) >= 32 else None,
        "ACTION_SIGNING_SECRET": (
            action_secret if len(action_secret.encode("utf-8")) >= 32 else None
        ),
        "AGENT_BOOTSTRAP_TOKEN": (
            agent_bootstrap_token
            if agent_bootstrap_token and len(agent_bootstrap_token.encode("utf-8")) >= 32
            else None
        ),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"校内测试模式缺少必要配置或强秘密：{', '.join(missing)}")
    if not cookie_secure:
        raise ValueError("校内测试模式必须启用 COOKIE_SECURE")


def create_app(
    seed_demo: bool = False,
    mindie_client: Any | None = None,
    status_get: Callable[..., httpx.Response] | None = None,
    database_url: str | None = None,
    jwt_secret: str | None = None,
    secure_cookies: bool | None = None,
) -> FastAPI:
    """创建中心 API，并允许测试注入数据库、密钥和外部状态探针。"""

    app = FastAPI(title="Kylin AIOps API", version="0.2.0")
    redis_url = os.getenv("REDIS_URL")
    configured_database_url = database_url or os.getenv("DATABASE_URL")
    configured_secret = jwt_secret or os.getenv("JWT_SECRET", "")
    signing_secret = os.getenv("ACTION_SIGNING_SECRET", "development-action-signing-secret")
    cookie_secure = (
        secure_cookies
        if secure_cookies is not None
        else os.getenv("COOKIE_SECURE", "true").lower() == "true"
    )
    _validate_school_test_config(
        configured_database_url,
        redis_url,
        configured_secret,
        signing_secret,
        os.getenv("AGENT_BOOTSTRAP_TOKEN"),
        cookie_secure,
    )
    queue: ActionQueue = (
        RedisActionQueue.from_url(redis_url) if redis_url else InMemoryActionQueue()
    )
    database = Database(configured_database_url) if configured_database_url else None
    app.state.database = database
    app.state.store = (
        SqlControlPlaneStore(database.sessions, queue)
        if database is not None
        else InMemoryStore(seed_demo=seed_demo, action_queue=queue)
    )
    app.state.auth_manager = None
    if database is not None:
        redis_client = Redis.from_url(redis_url, decode_responses=True) if redis_url else None
        app.state.auth_manager = AuthManager(
            database.sessions,
            configured_secret,
            redis_client=redis_client,
        )
    app.state.signer = ActionSigner(signing_secret.encode())
    mindie_url = os.getenv("MINDIE_BASE_URL")
    app.state.mindie_client = mindie_client or (
        MindIEClient(mindie_url, os.getenv("MINDIE_MODEL", "kylin-ops-llm")) if mindie_url else None
    )
    app.state.status_probe = RuntimeStatusProbe.from_environment(status_get or httpx.get)

    @app.exception_handler(ApiProblem)
    async def api_problem_handler(request: Request, exc: ApiProblem) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status,
            content={
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
                "details": exc.details,
            },
        )

    @app.exception_handler(StaleDataError)
    async def stale_data_handler(request: Request, _: StaleDataError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        return JSONResponse(
            status_code=409,
            content={
                "code": "VERSION_CONFLICT",
                "message": "数据已被其他用户更新，请刷新后重试",
                "request_id": request_id,
                "details": {},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_problem_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "request_id": request_id,
                "details": jsonable_encoder(exc.errors()),
            },
        )

    oauth2_scheme = OAuth2PasswordBearer(
        tokenUrl="/api/v1/auth/token",
        scheme_name="HumanOAuth2",
        auto_error=False,
    )

    def current_user(
        request: Request,
        token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    ) -> User:
        if not token:
            raise ApiProblem(401, "AUTH_REQUIRED", "Bearer token is required")
        bootstrap_token = os.getenv("AGENT_BOOTSTRAP_TOKEN")
        if bootstrap_token and secrets.compare_digest(token, bootstrap_token):
            return User(id="agent:bootstrap", role="agent")
        manager: AuthManager | None = request.app.state.auth_manager
        if manager is not None:
            return manager.authenticate_bearer(token)
        enrolled_node = next(
            (
                node_id
                for node_id, enrollment_token in request.app.state.store.agent_tokens.items()
                if enrollment_token == token
            ),
            None,
        )
        if enrolled_node:
            return User(id=f"agent:{enrolled_node}", role="agent")
        user = TOKENS.get(token)
        if user is None:
            raise ApiProblem(401, "INVALID_TOKEN", "Bearer token is invalid")
        return user

    def require(*roles: Role):
        def dependency(user: Annotated[User, Depends(current_user)]) -> User:
            if user.role not in roles:
                raise ApiProblem(403, "INSUFFICIENT_ROLE", "User role cannot perform this action")
            return user

        return dependency

    def store(request: Request) -> InMemoryStore:
        return request.app.state.store

    if app.state.auth_manager is not None:
        register_management_routes(
            app,
            app.state.auth_manager,
            database.sessions,
            current_user,
            secure_cookies=cookie_secure,
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/api/v1/overview",
        response_model=OverviewResponse,
        response_model_exclude_none=True,
    )
    def overview(
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        return data.overview()

    @app.get(
        "/api/v1/system/status",
        response_model=SystemStatus,
        response_model_exclude_none=True,
    )
    def system_status(
        request: Request,
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> SystemStatus:
        """Return observed model runtime state for the console status surfaces."""

        return request.app.state.status_probe.snapshot()

    @app.get(
        "/api/v1/incidents" if app.state.auth_manager is None else "/internal/legacy/incidents",
        include_in_schema=app.state.auth_manager is None,
    )
    def incidents(
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
        status: str | None = Query(default=None),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        items = list(data.incidents.values())
        if status:
            items = [item for item in items if item["status"] == status]
        total = len(items)
        start = (page - 1) * page_size
        return {
            "items": items[start : start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @app.get(
        "/api/v1/incidents/{incident_id}"
        if app.state.auth_manager is None
        else "/internal/legacy/incidents/{incident_id}",
        include_in_schema=app.state.auth_manager is None,
    )
    def incident_detail(
        incident_id: str,
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        incident = data.get_incident(incident_id)
        if incident is None:
            raise ApiProblem(404, "INCIDENT_NOT_FOUND", "Incident does not exist")
        return incident

    @app.post("/internal/v1/alerts", status_code=202)
    def receive_alerts(
        payload: AlertWebhook,
        data: Annotated[InMemoryStore, Depends(store)],
    ) -> dict[str, Any]:
        return data.receive_alerts(payload)

    @app.post(
        "/api/v1/incidents/{incident_id}/diagnose",
        response_model=DiagnosisResponse,
    )
    def run_diagnosis(
        incident_id: str,
        request: Request,
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        incident = data.get_incident(incident_id)
        if incident is None:
            raise ApiProblem(404, "INCIDENT_NOT_FOUND", "Incident does not exist")
        fallback = incident["diagnosis"]
        client = request.app.state.mindie_client
        if client is None:
            return fallback
        evidence_ids = {item["id"] for item in incident["evidence"]}
        try:
            generated = client.generate(
                {"incident": incident, "deterministic_diagnosis": fallback},
                available_evidence_ids=evidence_ids,
            )
            result = generated.model_dump()
            result["source"] = "mindie"
            return result
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            return {**fallback, "degraded_reason": type(exc).__name__}

    @app.get("/api/v1/events/stream")
    async def event_stream(
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> StreamingResponse:
        async def events():
            yield 'event: ready\ndata: {"connected":true}\n\n'
            while True:
                await asyncio.sleep(15)
                yield 'event: heartbeat\ndata: {"connected":true}\n\n'

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/v1/chat/sessions/{session_id}/messages")
    def chat(
        session_id: str,
        payload: ChatMessage,
        request: Request,
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        incident = (
            data.get_incident(payload.incident_id)
            if payload.incident_id
            else data.first_incident()
        )
        if incident is None:
            raise ApiProblem(404, "INCIDENT_NOT_FOUND", "Incident does not exist")
        diagnosis = incident["diagnosis"]
        client = request.app.state.mindie_client
        if client is not None:
            evidence_ids = {item["id"] for item in incident["evidence"]}
            try:
                generated = client.chat(
                    payload.message,
                    {"incident": incident, "deterministic_diagnosis": diagnosis},
                    available_evidence_ids=evidence_ids,
                )
                result = generated if isinstance(generated, dict) else generated.model_dump()
                return {
                    "session_id": session_id,
                    "answer": result["answer"],
                    "source": "generative_ai",
                    "evidence_refs": result["evidence_refs"],
                }
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                # 模型不可达或输出越权时必须降级到已有诊断，不能把未校验内容返回给用户。
                pass
        return {
            "session_id": session_id,
            "answer": diagnosis["summary"],
            "source": "deterministic_fallback",
            "evidence_refs": diagnosis["evidence_refs"],
        }

    @app.post(
        "/api/v1/incidents/{incident_id}/actions/preview",
        response_model=ActionResponse,
    )
    def preview_action(
        incident_id: str,
        payload: ActionPreview,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        if data.get_incident(incident_id) is None:
            raise ApiProblem(404, "INCIDENT_NOT_FOUND", "Incident does not exist")
        rule = ACTION_RULES.get(payload.action_name)
        if rule is None:
            raise ApiProblem(422, "ACTION_NOT_ALLOWLISTED", "Action is not in the allowlist")
        if payload.node_id not in rule["nodes"]:
            raise ApiProblem(422, "ACTION_TARGET_INVALID", "Action is not allowed on this node")
        if not valid_action_parameters(payload.action_name, payload.parameters):
            raise ApiProblem(
                422,
                "ACTION_PARAMETERS_INVALID",
                "Action parameters violate allowlist",
            )
        action = create_action_request(
            incident_id=incident_id,
            node_id=payload.node_id,
            action_name=payload.action_name,
            parameters=payload.parameters,
        )
        data.create_action(action, user.id)
        response = data.serialize_action(action)
        response.update(
            {
                "risk": "controlled_lab_action",
                "prechecks": ["target_online", "telemetry_fresh", "parameters_allowlisted"],
                "rollback": "run scenario-specific recovery and health check",
            }
        )
        return response

    @app.post(
        "/api/v1/action-requests/{action_id}/approve",
        response_model=ActionResponse,
    )
    def approve_action(
        action_id: str,
        request: Request,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        action = data.get_action(action_id)
        if action is None:
            raise ApiProblem(404, "ACTION_NOT_FOUND", "Action request does not exist")
        try:
            now = datetime.now(UTC)
            action.approve(user.id, now=now)
            envelope = request.app.state.signer.sign(action, now=now)
        except ApprovalError as exc:
            raise ApiProblem(409, "ACTION_APPROVAL_REJECTED", str(exc)) from exc
        data.save_approved_action(action, user.id)
        data.action_queue.enqueue(envelope)
        return data.serialize_action(action)

    @app.post("/agent/v1/enroll")
    def enroll_agent(
        request: Request,
        payload: Enrollment,
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("agent", "admin"))],
    ) -> dict[str, Any]:
        manager: AuthManager | None = request.app.state.auth_manager
        data.enroll_node(payload)
        if manager is not None:
            token = manager.issue_agent_credential(payload.node_id)
        else:
            token = secrets.token_urlsafe(48)
            data.agent_tokens[payload.node_id] = token
        return {"node_id": payload.node_id, "enrollment_token": token, "mtls_required": True}

    @app.get("/agent/v1/actions/next", response_model=None)
    def next_action(
        node_id: str,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("agent"))],
    ) -> Response | dict[str, Any]:
        if user.id.startswith("agent:") and user.id != f"agent:{node_id}":
            raise ApiProblem(403, "AGENT_TARGET_MISMATCH", "Agent token is bound to another node")
        envelope = data.action_queue.dequeue(node_id)
        if envelope is not None:
            result = asdict(envelope)
            result["issued_at"] = envelope.issued_at.isoformat()
            result["expires_at"] = envelope.expires_at.isoformat()
            return result
        return Response(status_code=204)

    @app.post("/agent/v1/telemetry", status_code=202)
    def ingest_telemetry(
        payload: TelemetryBatch,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("agent"))],
    ) -> dict[str, Any]:
        if user.id.startswith("agent:") and user.id != f"agent:{payload.node_id}":
            raise ApiProblem(403, "AGENT_TARGET_MISMATCH", "Agent token is bound to another node")
        try:
            data.record_telemetry(payload.node_id, payload.observed_at, payload.metrics)
        except KeyError:
            raise ApiProblem(
                404,
                "NODE_NOT_FOUND",
                "Node must enroll before sending telemetry",
            ) from None
        return {"accepted": True, "node_id": payload.node_id}

    @app.post("/agent/v1/actions/{action_id}/result")
    def action_result(
        action_id: str,
        payload: ActionResult,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("agent"))],
    ) -> dict[str, Any]:
        action = data.get_action(action_id)
        if action is None:
            raise ApiProblem(404, "ACTION_NOT_FOUND", "Action request does not exist")
        if user.id.startswith("agent:") and user.id != f"agent:{action.node_id}":
            raise ApiProblem(403, "AGENT_TARGET_MISMATCH", "Agent token is bound to another node")
        data.record_action_result(action_id, payload)
        return {"action_id": action_id, "status": "recorded"}

    @app.get("/api/v1/evaluations/runs/{run_id}")
    def evaluation_run(
        run_id: str,
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        report_root = os.getenv("EVALUATION_REPORT_DIR")
        if report_root and SAFE_EXPERIMENT_ID.fullmatch(run_id):
            root = Path(report_root).resolve()
            report_path = (root / run_id / "report.json").resolve()
            if report_path.parent.parent == root and report_path.is_file():
                try:
                    report = read_evaluation_report(report_path)
                except (OSError, ValidationError) as exc:
                    raise ApiProblem(
                        422,
                        "EVALUATION_REPORT_INVALID",
                        "Evaluation report is incomplete or invalid",
                        {"run_id": run_id, "error": type(exc).__name__},
                    ) from exc
                report.update(
                    {
                        "id": run_id,
                        "status": "passed" if report.get("passed") else "failed",
                    }
                )
                return report
        raise ApiProblem(
            404,
            "EVALUATION_RUN_NOT_FOUND",
            "Evaluation run has no generated report",
            {"run_id": run_id},
        )

    @app.get("/api/v1/evaluations/runs")
    def evaluation_runs(
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        """Discover generated reports; acceptance baselines are not evaluation runs."""

        report_root = os.getenv("EVALUATION_REPORT_DIR")
        if not report_root:
            return {"items": [], "total": 0}

        root = Path(report_root).resolve()
        if not root.is_dir():
            return {"items": [], "total": 0}

        reports: list[tuple[float, dict[str, Any]]] = []
        for run_dir in root.iterdir():
            # 目录名会进入 URL 路径参数，因此与详情接口使用相同的受限标识符规则。
            if not run_dir.is_dir() or not SAFE_EXPERIMENT_ID.fullmatch(run_dir.name):
                continue
            report_path = (run_dir / "report.json").resolve()
            if report_path.parent != run_dir.resolve() or not report_path.is_file():
                continue
            try:
                report = read_evaluation_report(report_path)
            except (OSError, ValidationError):
                # 不完整或损坏的生成结果不能在控制台中伪装成已完成的评测。
                continue
            report.update(
                {
                    "id": run_dir.name,
                    "status": "passed" if report.get("passed") else "failed",
                    "generated_at": datetime.fromtimestamp(
                        report_path.stat().st_mtime,
                        tz=UTC,
                    ).isoformat(),
                }
            )
            reports.append((report_path.stat().st_mtime, report))

        items = [report for _, report in sorted(reports, key=lambda item: item[0], reverse=True)]
        return {"items": items, "total": len(items)}

    @app.get(
        "/api/v1/audit-logs" if app.state.auth_manager is None else "/internal/legacy/audit-logs",
        include_in_schema=app.state.auth_manager is None,
    )
    def audit_logs(
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin"))],
    ) -> dict[str, Any]:
        return {"items": data.audit_logs, "total": len(data.audit_logs)}

    return app


app = create_app(seed_demo=os.getenv("DEMO_SEED", "false").lower() == "true")
