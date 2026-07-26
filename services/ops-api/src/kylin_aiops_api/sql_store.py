"""提供数据库模式下的实时业务读取，避免依赖启动时内存快照。"""

import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from .actions import ActionRequest, ActionStatus
from .database import (
    ActionExecutionRow,
    ActionRequestRow,
    AuditLogRow,
    DependencyEdgeRow,
    DiagnosisRow,
    EvidenceRow,
    IncidentRow,
    NodeRow,
    ServiceRow,
    TelemetrySnapshotRow,
)
from .queue import ActionQueue
from .schemas import ActionResult, AlertWebhook, Enrollment
from .serializers import serialize_incident


class SqlControlPlaneStore:
    """数据库模式的状态服务，所有业务读写都直接落到目标数据行。"""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        action_queue: ActionQueue,
    ) -> None:
        self.sessions = sessions
        self.action_queue = action_queue

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        with self.sessions() as session:
            row = session.get(IncidentRow, incident_id)
            if row is None:
                return None
            return self._serialize_incident(session, row)

    def first_incident(self) -> dict[str, Any] | None:
        with self.sessions() as session:
            row = session.scalar(
                select(IncidentRow)
                .where(IncidentRow.archived_at.is_(None))
                .order_by(IncidentRow.started_at.desc())
                .limit(1)
            )
            return self._serialize_incident(session, row) if row is not None else None

    @staticmethod
    def _serialize_incident(session: Session, row: IncidentRow) -> dict[str, Any]:
        evidence = list(
            session.scalars(select(EvidenceRow).where(EvidenceRow.incident_id == row.id))
        )
        diagnosis = session.scalar(
            select(DiagnosisRow).where(DiagnosisRow.incident_id == row.id)
        )
        return serialize_incident(row, evidence, diagnosis)

    def overview(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        today = datetime(now.year, now.month, now.day, tzinfo=UTC)
        with self.sessions() as session:
            total_nodes = int(
                session.scalar(
                    select(func.count())
                    .select_from(NodeRow)
                    .where(NodeRow.archived_at.is_(None))
                )
                or 0
            )
            online_nodes = int(
                session.scalar(
                    select(func.count())
                    .select_from(NodeRow)
                    .where(NodeRow.archived_at.is_(None), NodeRow.status == "online")
                )
                or 0
            )
            topology_groups = [
                {
                    "id": f"{service}:{status}",
                    "service": service,
                    "status": status,
                    "count": int(count),
                }
                for service, status, count in session.execute(
                    select(
                        ServiceRow.service_type,
                        NodeRow.status,
                        func.count(NodeRow.id),
                    )
                    .join(NodeRow, ServiceRow.node_id == NodeRow.id)
                    .where(
                        ServiceRow.archived_at.is_(None),
                        NodeRow.archived_at.is_(None),
                    )
                    .group_by(ServiceRow.service_type, NodeRow.status)
                    .order_by(ServiceRow.service_type, NodeRow.status)
                )
            ]
            source_service = aliased(ServiceRow)
            target_service = aliased(ServiceRow)
            topology_group_edges = [
                {
                    "source_service": source,
                    "target_service": target,
                    "count": int(count),
                    "confidence": float(confidence),
                }
                for source, target, count, confidence in session.execute(
                    select(
                        source_service.service_type,
                        target_service.service_type,
                        func.count(DependencyEdgeRow.id),
                        func.avg(DependencyEdgeRow.confidence),
                    )
                    .join(
                        source_service,
                        DependencyEdgeRow.source_service_id == source_service.id,
                    )
                    .join(
                        target_service,
                        DependencyEdgeRow.target_service_id == target_service.id,
                    )
                    .where(
                        DependencyEdgeRow.archived_at.is_(None),
                        source_service.archived_at.is_(None),
                        target_service.archived_at.is_(None),
                    )
                    .group_by(source_service.service_type, target_service.service_type)
                    .order_by(source_service.service_type, target_service.service_type)
                )
            ]
            nodes: list[dict[str, Any]] = []
            topology: list[dict[str, Any]] = []
            if total_nodes <= 200:
                node_rows = list(
                    session.scalars(
                        select(NodeRow)
                        .where(NodeRow.archived_at.is_(None))
                        .order_by(NodeRow.id)
                    )
                )
                service_rows = list(
                    session.scalars(
                        select(ServiceRow).where(ServiceRow.archived_at.is_(None))
                    )
                )
                telemetry_rows = (
                    list(
                        session.scalars(
                            select(TelemetrySnapshotRow).where(
                                TelemetrySnapshotRow.node_id.in_([row.id for row in node_rows])
                            )
                        )
                    )
                    if node_rows
                    else []
                )
                service_by_node = {row.node_id: row.service_type for row in service_rows}
                service_by_id = {row.id: row for row in service_rows}
                telemetry_by_node = {row.node_id: row.metrics for row in telemetry_rows}
                dependency_rows = list(
                    session.scalars(
                        select(DependencyEdgeRow).where(
                            DependencyEdgeRow.archived_at.is_(None)
                        )
                    )
                )
                nodes = [
                    {
                        "id": row.id,
                        "hostname": row.hostname or row.id,
                        "status": row.status,
                        "service": service_by_node.get(row.id),
                        "architecture": row.architecture,
                        "kylin_version": row.kylin_version,
                        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                        "metrics": telemetry_by_node.get(row.id, {}),
                    }
                    for row in node_rows
                ]
                topology = [
                    {
                        "source": source.node_id,
                        "target": target.node_id,
                        "confidence": edge.confidence,
                    }
                    for edge in dependency_rows
                    if (source := service_by_id.get(edge.source_service_id)) is not None
                    and (target := service_by_id.get(edge.target_service_id)) is not None
                ]
            return {
                "online_nodes": online_nodes,
                "total_nodes": total_nodes,
                "active_incidents": int(
                    session.scalar(
                        select(func.count())
                        .select_from(IncidentRow)
                        .where(
                            IncidentRow.status.in_(("open", "acknowledged", "resolving")),
                            IncidentRow.archived_at.is_(None),
                        )
                    )
                    or 0
                ),
                "today_alerts": int(
                    session.scalar(
                        select(func.count())
                        .select_from(IncidentRow)
                        .where(IncidentRow.started_at >= today)
                    )
                    or 0
                ),
                "pending_actions": int(
                    session.scalar(
                        select(func.count())
                        .select_from(ActionRequestRow)
                        .where(ActionRequestRow.status == "pending")
                    )
                    or 0
                ),
                "nodes": nodes,
                "topology": topology,
                "topology_groups": topology_groups,
                "topology_group_edges": topology_group_edges,
            }

    def receive_alerts(self, payload: AlertWebhook) -> dict[str, Any]:
        created = 0
        incident_ids: list[str] = []
        with self.sessions() as session:
            for alert in payload.alerts:
                incident_id = f"inc-{alert.fingerprint}"
                row = session.get(IncidentRow, incident_id)
                node_id = alert.labels.get("instance", "unknown")
                if row is None:
                    root_node_id = node_id if session.get(NodeRow, node_id) is not None else None
                    row = IncidentRow(
                        id=incident_id,
                        title=alert.annotations.get(
                            "summary", alert.labels.get("alertname", "Alert")
                        ),
                        fault_type=alert.labels.get("alertname", "unknown"),
                        severity=alert.labels.get("severity", "medium"),
                        status="open",
                        started_at=alert.startsAt,
                        ended_at=None,
                        root_node_id=root_node_id,
                        source="alert",
                        assignee_user_id=None,
                        handling_notes="",
                        version=1,
                        archived_at=None,
                        archived_by=None,
                    )
                    session.add(row)
                    session.add(
                        DiagnosisRow(
                            id=f"diag-{incident_id}",
                            incident_id=incident_id,
                            summary="等待证据关联",
                            root_cause=node_id,
                            severity=row.severity,
                            confidence=0.4,
                            propagation_path=[node_id],
                            evidence_refs=[],
                            recommended_steps=["采集节点遥测和服务证据"],
                            action_candidates=[],
                            source="rule_baseline",
                            created_at=datetime.now(UTC),
                        )
                    )
                    created += 1
                row.status = "resolved" if alert.status == "resolved" else "open"
                row.ended_at = datetime.now(UTC) if alert.status == "resolved" else None
                incident_ids.append(incident_id)
            session.commit()
        return {
            "accepted": len(payload.alerts),
            "created": created,
            "incident_ids": incident_ids,
        }

    def record_telemetry(
        self,
        node_id: str,
        observed_at: datetime,
        metrics: dict[str, float],
    ) -> None:
        """只更新目标节点及其最新遥测，保留人工维护的节点字段。"""

        with self.sessions() as session:
            row = session.get(NodeRow, node_id)
            if row is None:
                raise KeyError(node_id)
            row.status = "online"
            row.last_seen_at = observed_at
            session.merge(
                TelemetrySnapshotRow(
                    node_id=node_id,
                    observed_at=observed_at,
                    metrics=metrics,
                )
            )
            session.commit()

    def enroll_node(self, payload: Enrollment) -> None:
        """创建或更新目标节点的观测字段，不覆盖已有管理配置。"""

        with self.sessions() as session:
            row = session.get(NodeRow, payload.node_id)
            if row is None:
                row = NodeRow(
                    id=payload.node_id,
                    display_name=payload.hostname,
                    description="",
                    tags=[],
                    enabled=True,
                    version=1,
                    archived_at=None,
                    archived_by=None,
                )
                session.add(row)
            row.hostname = payload.hostname
            row.architecture = payload.architecture
            row.kylin_version = payload.kylin_version
            row.status = "online"
            session.commit()

    def create_action(self, action: ActionRequest, actor_id: str) -> None:
        """持久化单个待审批动作及对应审计记录。"""

        with self.sessions() as session:
            session.add(_action_row(action))
            session.add(_audit_row(actor_id, "action.previewed", action.id))
            session.commit()

    def get_action(self, action_id: str) -> ActionRequest | None:
        with self.sessions() as session:
            row = session.get(ActionRequestRow, action_id)
            return _action_from_row(row) if row is not None else None

    def save_approved_action(self, action: ActionRequest, actor_id: str) -> None:
        """锁定目标动作并保存审批结果，禁止重写其他动作。"""

        with self.sessions() as session:
            row = session.get(ActionRequestRow, action.id, with_for_update=True)
            if row is None:
                raise KeyError(action.id)
            row.status = action.status.value
            row.approved_by = action.approved_by
            row.approved_at = action.approved_at
            session.add(
                _audit_row(
                    actor_id,
                    "action.approved",
                    action.id,
                    {"node_id": action.node_id},
                )
            )
            session.commit()

    def record_action_result(self, action_id: str, result: ActionResult) -> None:
        """幂等覆盖目标动作执行结果，并把该动作标记为已执行。"""

        with self.sessions() as session:
            row = session.get(ActionRequestRow, action_id, with_for_update=True)
            if row is None:
                raise KeyError(action_id)
            session.merge(
                ActionExecutionRow(
                    id=f"exec-{action_id}",
                    action_request_id=action_id,
                    exit_code=result.exit_code,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    health_check_passed=result.health_check == "passed",
                    executed_at=datetime.now(UTC),
                )
            )
            row.status = ActionStatus.EXECUTED.value
            session.commit()

    def append_audit(
        self,
        actor_id: str,
        action: str,
        target: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """追加一条独立审计记录，避免为了审计写入重写其他业务表。"""

        with self.sessions() as session:
            session.add(_audit_row(actor_id, action, target, details))
            session.commit()

    @staticmethod
    def serialize_action(action: ActionRequest) -> dict[str, Any]:
        """把动作领域对象转换为稳定的 API 响应结构。"""

        data = asdict(action)
        data["status"] = action.status.value
        for key in ("created_at", "expires_at", "approved_at"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data


def _action_row(action: ActionRequest) -> ActionRequestRow:
    return ActionRequestRow(
        id=action.id,
        incident_id=action.incident_id,
        node_id=action.node_id,
        action_name=action.action_name,
        parameters=action.parameters,
        status=action.status.value,
        approved_by=action.approved_by,
        approved_at=action.approved_at,
        created_at=action.created_at,
        expires_at=action.expires_at,
    )


def _action_from_row(row: ActionRequestRow) -> ActionRequest:
    return ActionRequest(
        id=row.id,
        incident_id=row.incident_id,
        node_id=row.node_id,
        action_name=row.action_name,
        parameters=row.parameters,
        created_at=_as_utc(row.created_at),
        expires_at=_as_utc(row.expires_at),
        status=ActionStatus(row.status),
        approved_by=row.approved_by,
        approved_at=_as_utc(row.approved_at) if row.approved_at is not None else None,
    )


def _as_utc(value: datetime) -> datetime:
    """统一数据库时间为 UTC，兼容 SQLite 读取后丢失时区信息的行为。"""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _audit_row(
    actor_id: str,
    action: str,
    target: str,
    details: dict[str, Any] | None = None,
) -> AuditLogRow:
    return AuditLogRow(
        id=str(uuid.uuid4()),
        actor_id=actor_id,
        action=action,
        target=target,
        request_id=str(uuid.uuid4()),
        details=details or {},
        created_at=datetime.now(UTC),
    )
