"""提供数据库模式下的实时业务读取，避免依赖启动时内存快照。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .database import (
    ActionRequestRow,
    DependencyEdgeRow,
    DiagnosisRow,
    EvidenceRow,
    IncidentRow,
    NodeRow,
    ServiceRow,
)
from .queue import ActionQueue
from .schemas import AlertWebhook
from .serializers import serialize_incident
from .store import InMemoryStore


class SqlControlPlaneStore(InMemoryStore):
    """数据库模式的过渡存储；实时读取走 SQL，旧动作链在后续任务中迁移。"""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        action_queue: ActionQueue,
        engine: Engine,
    ) -> None:
        super().__init__(action_queue=action_queue, engine=engine)
        self.sessions = sessions

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
            node_rows = list(
                session.scalars(
                    select(NodeRow).where(NodeRow.archived_at.is_(None)).order_by(NodeRow.id)
                )
            )
            service_rows = list(
                session.scalars(select(ServiceRow).where(ServiceRow.archived_at.is_(None)))
            )
            service_by_node = {row.node_id: row.service_type for row in service_rows}
            service_by_id = {row.id: row for row in service_rows}
            dependency_rows = list(
                session.scalars(
                    select(DependencyEdgeRow).where(DependencyEdgeRow.archived_at.is_(None))
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
                }
                for row in node_rows
            ]
            topology = []
            for edge in dependency_rows:
                source = service_by_id.get(edge.source_service_id)
                target = service_by_id.get(edge.target_service_id)
                if source is not None and target is not None:
                    topology.append(
                        {
                            "source": source.node_id,
                            "target": target.node_id,
                            "confidence": edge.confidence,
                        }
                    )
            return {
                "online_nodes": sum(row.status == "online" for row in node_rows),
                "total_nodes": len(node_rows),
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
