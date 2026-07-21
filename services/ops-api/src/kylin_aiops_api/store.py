"""Development state store with optional SQL persistence for the MVP control plane."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .actions import ActionRequest, ActionStatus
from .database import (
    ActionExecutionRow,
    ActionRequestRow,
    AuditLogRow,
    DiagnosisRow,
    EvidenceRow,
    IncidentRow,
    NodeRow,
    ServiceRow,
)
from .queue import ActionQueue, InMemoryActionQueue


class InMemoryStore:
    """Deterministic development store; production wiring uses PostgreSQL/Redis."""

    def __init__(
        self,
        seed_demo: bool = False,
        action_queue: ActionQueue | None = None,
        database_url: str | None = None,
    ) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.incidents: dict[str, dict[str, Any]] = {}
        self.actions: dict[str, ActionRequest] = {}
        self.action_queue = action_queue or InMemoryActionQueue()
        self.executions: dict[str, dict[str, Any]] = {}
        self.agent_tokens: dict[str, str] = {}
        self.telemetry: dict[str, dict[str, Any]] = {}
        self.alert_incidents: dict[str, str] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self.engine = create_engine(database_url) if database_url else None
        if self.engine:
            self._load_database()
        if seed_demo and not self.nodes:
            self._seed_demo()

    def _load_database(self) -> None:
        assert self.engine is not None
        with Session(self.engine) as session:
            services = {
                item.node_id: item.service_type for item in session.scalars(select(ServiceRow))
            }
            for row in session.scalars(select(NodeRow)):
                self.nodes[row.id] = {
                    "id": row.id,
                    "hostname": row.hostname,
                    "architecture": row.architecture,
                    "kylin_version": row.kylin_version,
                    "status": row.status,
                    "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                    "service": services.get(row.id),
                }
            evidence_by_incident: dict[str, list[dict[str, Any]]] = {}
            for row in session.scalars(select(EvidenceRow)):
                evidence_by_incident.setdefault(row.incident_id, []).append(
                    {
                        "id": row.id,
                        "kind": row.kind,
                        "node_id": row.node_id,
                        "summary": row.summary,
                        "observed_at": row.observed_at.isoformat(),
                    }
                )
            diagnoses = {row.incident_id: row for row in session.scalars(select(DiagnosisRow))}
            for row in session.scalars(select(IncidentRow)):
                diagnosis = diagnoses.get(row.id)
                self.incidents[row.id] = {
                    "id": row.id,
                    "title": row.title,
                    "severity": row.severity,
                    "status": row.status,
                    "started_at": row.started_at.isoformat(),
                    "root_node": row.root_node_id,
                    "propagation_path": (
                        diagnosis.propagation_path if diagnosis else [row.root_node_id]
                    ),
                    "evidence": evidence_by_incident.get(row.id, []),
                    "diagnosis": {
                        "summary": diagnosis.summary if diagnosis else "Awaiting diagnosis",
                        "root_cause": diagnosis.root_cause if diagnosis else row.root_node_id,
                        "severity": diagnosis.severity if diagnosis else row.severity,
                        "propagation_path": (
                            diagnosis.propagation_path if diagnosis else [row.root_node_id]
                        ),
                        "evidence_refs": diagnosis.evidence_refs if diagnosis else [],
                        "recommended_steps": diagnosis.recommended_steps if diagnosis else [],
                        "action_candidates": diagnosis.action_candidates if diagnosis else [],
                        "confidence": diagnosis.confidence if diagnosis else 0.0,
                        "source": diagnosis.source if diagnosis else "pending",
                    },
                }
            for row in session.scalars(select(ActionRequestRow)):
                self.actions[row.id] = ActionRequest(
                    id=row.id,
                    incident_id=row.incident_id,
                    node_id=row.node_id,
                    action_name=row.action_name,
                    parameters=row.parameters,
                    created_at=row.created_at,
                    expires_at=row.expires_at,
                    status=ActionStatus(row.status),
                    approved_by=row.approved_by,
                    approved_at=row.approved_at,
                )
            for row in session.scalars(select(AuditLogRow).order_by(AuditLogRow.created_at)):
                self.audit_logs.append(
                    {
                        "id": row.id,
                        "actor_id": row.actor_id,
                        "action": row.action,
                        "target": row.target,
                        "request_id": row.request_id,
                        "details": row.details,
                        "created_at": row.created_at.isoformat(),
                    }
                )

    def _seed_demo(self) -> None:
        now = datetime.now(UTC)
        self.nodes = {
            "web-01": {
                "id": "web-01",
                "hostname": "web-01",
                "status": "online",
                "service": "nginx",
            },
            "app-01": {"id": "app-01", "hostname": "app-01", "status": "online", "service": "java"},
            "db-01": {"id": "db-01", "hostname": "db-01", "status": "online", "service": "mysql"},
        }
        self.incidents["inc-db-pool"] = {
            "id": "inc-db-pool",
            "title": "数据库连接池耗尽",
            "severity": "high",
            "status": "open",
            "started_at": now.isoformat(),
            "root_node": "db-01",
            "propagation_path": ["db-01", "app-01", "web-01"],
            "evidence": [
                {
                    "id": "ev-db-connections",
                    "kind": "metric",
                    "node_id": "db-01",
                    "summary": "mysql_connections=498/500",
                    "observed_at": now.isoformat(),
                },
                {
                    "id": "ev-db-log",
                    "kind": "log",
                    "node_id": "db-01",
                    "summary": "ERROR 1040: Too many connections",
                    "observed_at": now.isoformat(),
                },
            ],
            "diagnosis": {
                "summary": "测试账号连接占满导致应用连接超时。",
                "root_cause": "db-01",
                "severity": "high",
                "propagation_path": ["db-01", "app-01", "web-01"],
                "evidence_refs": ["ev-db-connections", "ev-db-log"],
                "recommended_steps": [
                    "确认连接来源仅为 ops_fault 测试账号",
                    "审批后终止测试连接",
                    "复查连接数和应用健康检查",
                ],
                "action_candidates": ["terminate_fault_db_sessions"],
                "confidence": 0.86,
                "source": "deterministic_fallback",
            },
        }

    def overview(self) -> dict[str, Any]:
        """Build a current overview from enrolled nodes, telemetry, incidents, and actions."""

        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=30)
        for node in self.nodes.values():
            last_seen = node.get("last_seen_at")
            if last_seen and datetime.fromisoformat(last_seen) < cutoff:
                node["status"] = "offline"
        nodes = []
        for node in self.nodes.values():
            item = dict(node)
            telemetry = self.telemetry.get(node["id"])
            if telemetry:
                item["metrics"] = dict(telemetry["metrics"])
            nodes.append(item)
        # 只输出两端服务都已真实发现的拓扑边，空环境不能重新生成三节点演示链。
        service_nodes = {
            str(node.get("service", "")).lower(): node["id"]
            for node in self.nodes.values()
            if node.get("service")
        }
        topology = [
            {"source": service_nodes[source], "target": service_nodes[target], "confidence": 1.0}
            for source, target in (("nginx", "java"), ("java", "mysql"))
            if source in service_nodes and target in service_nodes
        ]
        return {
            "online_nodes": sum(node["status"] == "online" for node in self.nodes.values()),
            "total_nodes": len(self.nodes),
            "active_incidents": sum(
                incident["status"] in {"open", "diagnosing"} for incident in self.incidents.values()
            ),
            "today_alerts": sum(
                datetime.fromisoformat(incident["started_at"]).date() == now.date()
                for incident in self.incidents.values()
            ),
            "pending_actions": sum(
                action.status.value == "pending" for action in self.actions.values()
            ),
            "nodes": nodes,
            "topology": topology,
        }

    def persist_all(self) -> None:
        """Persist the current MVP state when a database URL was configured."""

        if not self.engine:
            return
        with Session(self.engine) as session:
            for node in self.nodes.values():
                last_seen = node.get("last_seen_at")
                session.merge(
                    NodeRow(
                        id=node["id"],
                        hostname=node["hostname"],
                        architecture=node.get("architecture"),
                        kylin_version=node.get("kylin_version"),
                        status=node["status"],
                        last_seen_at=datetime.fromisoformat(last_seen) if last_seen else None,
                    )
                )
                if node.get("service"):
                    session.merge(
                        ServiceRow(
                            id=f"svc-{node['id']}",
                            node_id=node["id"],
                            name=str(node["service"]),
                            service_type=str(node["service"]),
                            status=node["status"],
                        )
                    )
            for incident in self.incidents.values():
                session.merge(
                    IncidentRow(
                        id=incident["id"],
                        title=incident["title"],
                        fault_type=incident.get("fault_type", "unknown"),
                        severity=incident["severity"],
                        status=incident["status"],
                        started_at=datetime.fromisoformat(incident["started_at"]),
                        ended_at=None,
                        root_node_id=incident.get("root_node"),
                    )
                )
                for evidence in incident.get("evidence", []):
                    session.merge(
                        EvidenceRow(
                            id=evidence["id"],
                            incident_id=incident["id"],
                            node_id=evidence["node_id"],
                            kind=evidence["kind"],
                            summary=evidence["summary"],
                            source_uri=evidence.get("source_uri"),
                            observed_at=datetime.fromisoformat(evidence["observed_at"]),
                        )
                    )
                diagnosis = incident.get("diagnosis")
                if diagnosis:
                    session.merge(
                        DiagnosisRow(
                            id=f"diag-{incident['id']}",
                            incident_id=incident["id"],
                            summary=diagnosis["summary"],
                            root_cause=diagnosis["root_cause"],
                            severity=diagnosis["severity"],
                            confidence=diagnosis["confidence"],
                            propagation_path=diagnosis["propagation_path"],
                            evidence_refs=diagnosis["evidence_refs"],
                            recommended_steps=diagnosis["recommended_steps"],
                            action_candidates=diagnosis["action_candidates"],
                            source=diagnosis["source"],
                            created_at=datetime.now(UTC),
                        )
                    )
            for action in self.actions.values():
                session.merge(
                    ActionRequestRow(
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
                )
            for action_id, execution in self.executions.items():
                session.merge(
                    ActionExecutionRow(
                        id=f"exec-{action_id}",
                        action_request_id=action_id,
                        exit_code=execution["exit_code"],
                        stdout=execution["stdout"],
                        stderr=execution["stderr"],
                        health_check_passed=execution["health_check"] == "passed",
                        executed_at=datetime.now(UTC),
                    )
                )
            for audit in self.audit_logs:
                session.merge(
                    AuditLogRow(
                        id=audit["id"],
                        actor_id=audit["actor_id"],
                        action=audit["action"],
                        target=audit["target"],
                        request_id=audit["request_id"],
                        details=audit["details"],
                        created_at=datetime.fromisoformat(audit["created_at"]),
                    )
                )
            session.commit()

    def audit(
        self,
        actor_id: str,
        action: str,
        target: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append an immutable-in-practice audit event for a security-sensitive operation."""

        self.audit_logs.append(
            {
                "id": str(uuid.uuid4()),
                "actor_id": actor_id,
                "action": action,
                "target": target,
                "request_id": str(uuid.uuid4()),
                "details": details or {},
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    @staticmethod
    def serialize_action(action: ActionRequest) -> dict[str, Any]:
        data = asdict(action)
        data["status"] = action.status.value
        for key in ("created_at", "expires_at", "approved_at"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data
