"""定义跨路由与存储层共享的 API 输入与响应模型。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Enrollment(BaseModel):
    node_id: str
    hostname: str
    architecture: str
    kylin_version: str


class ActionResult(BaseModel):
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    health_check: Literal["passed", "failed"]


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    fingerprint: str = Field(min_length=1)


class AlertWebhook(BaseModel):
    status: Literal["firing", "resolved"]
    alerts: list[Alert]


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    role: Literal["admin", "operator", "viewer"]
    is_active: bool
    version: int
    created_at: str
    updated_at: str
    archived_at: str | None = None


class NodeResponse(BaseModel):
    id: str
    display_name: str
    description: str
    tags: list[str]
    enabled: bool
    hostname: str | None = None
    architecture: str | None = None
    kylin_version: str | None = None
    status: str
    last_seen_at: str | None = None
    version: int
    archived_at: str | None = None


class ServiceResponse(BaseModel):
    id: str
    node_id: str
    name: str
    service_type: str
    description: str
    enabled: bool
    status: str
    version: int
    archived_at: str | None = None


class DependencyResponse(BaseModel):
    id: int
    source_service_id: str
    target_service_id: str
    source: str
    confidence: float
    observed_at: str
    version: int
    archived_at: str | None = None


class EvidenceResponse(BaseModel):
    id: str
    kind: str
    node_id: str
    summary: str
    observed_at: str


class DiagnosisResponse(BaseModel):
    summary: str
    root_cause: str
    severity: str
    propagation_path: list[str]
    evidence_refs: list[str]
    recommended_steps: list[str]
    action_candidates: list[str]
    confidence: float
    source: str


class IncidentResponse(BaseModel):
    id: str
    title: str
    fault_type: str
    severity: str
    status: str
    source: str
    started_at: str
    ended_at: str | None = None
    root_node: str | None = None
    assignee_user_id: str | None = None
    handling_notes: str
    version: int
    archived_at: str | None = None
    propagation_path: list[str]
    evidence: list[EvidenceResponse]
    diagnosis: DiagnosisResponse


class AuditLogResponse(BaseModel):
    id: str
    actor_id: str
    action: str
    target: str
    request_id: str
    details: dict[str, Any]
    created_at: str


class OverviewNodeResponse(BaseModel):
    id: str
    hostname: str
    status: str
    service: str | None = None
    architecture: str | None = None
    kylin_version: str | None = None
    last_seen_at: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class TopologyEdgeResponse(BaseModel):
    source: str
    target: str
    confidence: float


class OverviewResponse(BaseModel):
    online_nodes: int
    total_nodes: int
    active_incidents: int
    today_alerts: int
    pending_actions: int
    nodes: list[OverviewNodeResponse]
    topology: list[TopologyEdgeResponse]


class ActionResponse(BaseModel):
    id: str
    incident_id: str
    node_id: str
    action_name: str
    parameters: dict[str, Any]
    created_at: str
    expires_at: str
    status: str
    approved_by: str | None = None
    approved_at: str | None = None
    risk: str | None = None
    prechecks: list[str] | None = None
    rollback: str | None = None


class UserPage(BaseModel):
    items: list[UserResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class NodePage(BaseModel):
    items: list[NodeResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class ServicePage(BaseModel):
    items: list[ServiceResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class DependencyPage(BaseModel):
    items: list[DependencyResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class IncidentPage(BaseModel):
    items: list[IncidentResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class AuditLogPage(BaseModel):
    items: list[AuditLogResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
