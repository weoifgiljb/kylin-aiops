import asyncio
import json
import os
import re
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from kylin_aiops_diagnosis.mindie import MindIEClient
from pydantic import BaseModel, Field

from .actions import ActionSigner, ApprovalError, create_action_request
from .queue import RedisStreamActionQueue
from .store import InMemoryStore

Role = Literal["admin", "operator", "viewer", "agent"]


class User(BaseModel):
    id: str
    role: Role


class ApiProblem(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.details = details if details is not None else {}


class ActionPreview(BaseModel):
    node_id: str
    action_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    health_check: Literal["passed", "failed"]


class Enrollment(BaseModel):
    node_id: str
    hostname: str
    architecture: str
    kylin_version: str


class TelemetryBatch(BaseModel):
    node_id: str
    observed_at: datetime
    metrics: dict[str, float]


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    incident_id: str | None = None


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    fingerprint: str = Field(min_length=1)


class AlertWebhook(BaseModel):
    status: Literal["firing", "resolved"]
    alerts: list[Alert]


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
        return set(parameters) == {"experiment_id", "filename"} and parameters.get(
            "filename"
        ) == "disk-fill.bin"
    if action_name == "clear_fault_netem":
        return set(parameters) == {"experiment_id", "interface"} and bool(
            SAFE_INTERFACE.fullmatch(str(parameters.get("interface", "")))
        )
    return False


def create_app(seed_demo: bool = False, mindie_client: Any | None = None) -> FastAPI:
    app = FastAPI(title="Kylin AIOps API", version="0.1.0")
    redis_url = os.getenv("REDIS_URL")
    queue = RedisStreamActionQueue.from_url(redis_url) if redis_url else None
    app.state.store = InMemoryStore(
        seed_demo=seed_demo,
        action_queue=queue,
        database_url=os.getenv("DATABASE_URL"),
    )
    signing_secret = os.getenv("ACTION_SIGNING_SECRET", "development-action-signing-secret")
    app.state.signer = ActionSigner(signing_secret.encode())
    mindie_url = os.getenv("MINDIE_BASE_URL")
    app.state.mindie_client = mindie_client or (
        MindIEClient(mindie_url, os.getenv("MINDIE_MODEL", "kylin-ops-llm"))
        if mindie_url
        else None
    )

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

    def current_user(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise ApiProblem(401, "AUTH_REQUIRED", "Bearer token is required")
        token = authorization.removeprefix("Bearer ")
        user = TOKENS.get(token)
        if user is None:
            enrolled_node = next(
                (
                    node_id
                    for node_id, enrollment_token in request.app.state.store.agent_tokens.items()
                    if enrollment_token == token
                ),
                None,
            )
            if enrolled_node:
                user = User(id=f"agent:{enrolled_node}", role="agent")
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

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/overview")
    def overview(
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        return data.overview()

    @app.get("/api/v1/incidents")
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

    @app.get("/api/v1/incidents/{incident_id}")
    def incident_detail(
        incident_id: str,
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        incident = data.incidents.get(incident_id)
        if incident is None:
            raise ApiProblem(404, "INCIDENT_NOT_FOUND", "Incident does not exist")
        return incident

    @app.post("/internal/v1/alerts", status_code=202)
    def receive_alerts(
        payload: AlertWebhook,
        data: Annotated[InMemoryStore, Depends(store)],
    ) -> dict[str, Any]:
        created = 0
        incident_ids: list[str] = []
        for alert in payload.alerts:
            incident_id = data.alert_incidents.get(alert.fingerprint)
            if incident_id is None:
                incident_id = f"inc-{alert.fingerprint}"
                data.alert_incidents[alert.fingerprint] = incident_id
                created += 1
                node_id = alert.labels.get("instance", "unknown")
                data.incidents[incident_id] = {
                    "id": incident_id,
                    "title": alert.annotations.get(
                        "summary", alert.labels.get("alertname", "Alert")
                    ),
                    "severity": alert.labels.get("severity", "warning"),
                    "status": "open",
                    "started_at": alert.startsAt.isoformat(),
                    "root_node": node_id,
                    "propagation_path": [node_id],
                    "evidence": [],
                    "diagnosis": {
                        "summary": "Awaiting evidence correlation",
                        "root_cause": node_id,
                        "severity": alert.labels.get("severity", "warning"),
                        "propagation_path": [node_id],
                        "evidence_refs": [],
                        "recommended_steps": ["Collect node telemetry and service evidence"],
                        "action_candidates": [],
                        "confidence": 0.4,
                        "source": "rule_baseline",
                    },
                }
            incident = data.incidents[incident_id]
            incident["status"] = "resolved" if alert.status == "resolved" else "open"
            incident_ids.append(incident_id)
        data.persist_all()
        return {"accepted": len(payload.alerts), "created": created, "incident_ids": incident_ids}

    @app.post("/api/v1/incidents/{incident_id}/diagnose")
    def run_diagnosis(
        incident_id: str,
        request: Request,
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        incident = data.incidents.get(incident_id)
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
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin", "operator", "viewer"))],
    ) -> dict[str, Any]:
        incident = data.incidents.get(payload.incident_id or "inc-db-pool")
        if incident is None:
            raise ApiProblem(404, "INCIDENT_NOT_FOUND", "Incident does not exist")
        diagnosis = incident["diagnosis"]
        return {
            "session_id": session_id,
            "answer": diagnosis["summary"],
            "source": "deterministic_fallback",
            "evidence_refs": diagnosis["evidence_refs"],
        }

    @app.post("/api/v1/incidents/{incident_id}/actions/preview")
    def preview_action(
        incident_id: str,
        payload: ActionPreview,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        if incident_id not in data.incidents:
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
        data.actions[action.id] = action
        data.audit(user.id, "action.previewed", action.id, {"incident_id": incident_id})
        data.persist_all()
        response = data.serialize_action(action)
        response.update(
            {
                "risk": "controlled_lab_action",
                "prechecks": ["target_online", "telemetry_fresh", "parameters_allowlisted"],
                "rollback": "run scenario-specific recovery and health check",
            }
        )
        return response

    @app.post("/api/v1/action-requests/{action_id}/approve")
    def approve_action(
        action_id: str,
        request: Request,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("admin", "operator"))],
    ) -> dict[str, Any]:
        action = data.actions.get(action_id)
        if action is None:
            raise ApiProblem(404, "ACTION_NOT_FOUND", "Action request does not exist")
        try:
            now = datetime.now(UTC)
            action.approve(user.id, now=now)
            envelope = request.app.state.signer.sign(action, now=now)
        except ApprovalError as exc:
            raise ApiProblem(409, "ACTION_APPROVAL_REJECTED", str(exc)) from exc
        data.action_queue.enqueue(envelope)
        data.audit(user.id, "action.approved", action.id, {"node_id": action.node_id})
        data.persist_all()
        return data.serialize_action(action)

    @app.post("/agent/v1/enroll")
    def enroll_agent(
        payload: Enrollment,
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("agent", "admin"))],
    ) -> dict[str, Any]:
        token = str(uuid.uuid4())
        data.agent_tokens[payload.node_id] = token
        data.nodes[payload.node_id] = {
            "id": payload.node_id,
            "hostname": payload.hostname,
            "architecture": payload.architecture,
            "kylin_version": payload.kylin_version,
            "status": "online",
        }
        data.persist_all()
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
        node = data.nodes.get(payload.node_id)
        if node is None:
            raise ApiProblem(404, "NODE_NOT_FOUND", "Node must enroll before sending telemetry")
        observed_at = payload.observed_at.isoformat()
        node.update({"status": "online", "last_seen_at": observed_at})
        data.telemetry[payload.node_id] = {
            "observed_at": observed_at,
            "metrics": payload.metrics,
        }
        data.persist_all()
        return {"accepted": True, "node_id": payload.node_id}

    @app.post("/agent/v1/actions/{action_id}/result")
    def action_result(
        action_id: str,
        payload: ActionResult,
        data: Annotated[InMemoryStore, Depends(store)],
        user: Annotated[User, Depends(require("agent"))],
    ) -> dict[str, Any]:
        action = data.actions.get(action_id)
        if action is None:
            raise ApiProblem(404, "ACTION_NOT_FOUND", "Action request does not exist")
        if user.id.startswith("agent:") and user.id != f"agent:{action.node_id}":
            raise ApiProblem(403, "AGENT_TARGET_MISMATCH", "Agent token is bound to another node")
        data.executions[action_id] = payload.model_dump()
        action.status = action.status.EXECUTED
        data.persist_all()
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
                report = json.loads(report_path.read_text(encoding="utf-8"))
                report.update(
                    {
                        "id": run_id,
                        "status": "passed" if report.get("passed") else "failed",
                    }
                )
                return report
        return {
            "id": run_id,
            "status": "baseline_only",
            "trial_count": 0,
            "thresholds": {
                "detection_f1": 0.85,
                "severity_macro_f1": 0.80,
                "root_cause_top1": 0.80,
                "root_cause_top3": 0.95,
                "propagation_edge_f1": 0.80,
                "remediation_success_rate": 0.80,
            },
            "metrics": {},
        }

    @app.get("/api/v1/audit-logs")
    def audit_logs(
        data: Annotated[InMemoryStore, Depends(store)],
        _: Annotated[User, Depends(require("admin"))],
    ) -> dict[str, Any]:
        return {"items": data.audit_logs, "total": len(data.audit_logs)}

    return app


app = create_app(seed_demo=os.getenv("DEMO_SEED", "true").lower() == "true")
