"""提供无数据库测试与演示使用的进程内状态存储。"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from .actions import ActionRequest, ActionStatus
from .queue import ActionQueue, InMemoryActionQueue
from .schemas import ActionResult, AlertWebhook, Enrollment


class InMemoryStore:
    """确定性的开发存储；生产环境使用独立的 SQL 状态服务。"""

    def __init__(
        self,
        seed_demo: bool = False,
        action_queue: ActionQueue | None = None,
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
        if seed_demo and not self.nodes:
            self._seed_demo()

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

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        """按标识读取当前内存事件，供无数据库测试和演示模式使用。"""

        return self.incidents.get(incident_id)

    def first_incident(self) -> dict[str, Any] | None:
        """返回首个内存事件，维持未指定问答上下文时的既有行为。"""

        return next(iter(self.incidents.values()), None)

    def receive_alerts(self, payload: AlertWebhook) -> dict[str, Any]:
        """在内存模式中按 fingerprint 幂等接收告警。"""

        created = 0
        incident_ids: list[str] = []
        for alert in payload.alerts:
            incident_id = self.alert_incidents.get(alert.fingerprint)
            if incident_id is None:
                incident_id = f"inc-{alert.fingerprint}"
                self.alert_incidents[alert.fingerprint] = incident_id
                created += 1
                node_id = alert.labels.get("instance", "unknown")
                self.incidents[incident_id] = {
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
            incident = self.incidents[incident_id]
            incident["status"] = "resolved" if alert.status == "resolved" else "open"
            incident_ids.append(incident_id)
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
        """更新内存节点和最新遥测，供无数据库模式复用。"""

        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(node_id)
        observed_text = observed_at.isoformat()
        node.update({"status": "online", "last_seen_at": observed_text})
        self.telemetry[node_id] = {"observed_at": observed_text, "metrics": metrics}

    def enroll_node(self, payload: Enrollment) -> None:
        """登记内存节点，供无数据库测试和演示复用。"""

        self.nodes[payload.node_id] = {
            "id": payload.node_id,
            "hostname": payload.hostname,
            "architecture": payload.architecture,
            "kylin_version": payload.kylin_version,
            "status": "online",
        }

    def create_action(self, action: ActionRequest, actor_id: str) -> None:
        """保存内存动作并记录预览审计。"""

        self.actions[action.id] = action
        self.audit(actor_id, "action.previewed", action.id, {"incident_id": action.incident_id})

    def get_action(self, action_id: str) -> ActionRequest | None:
        return self.actions.get(action_id)

    def save_approved_action(self, action: ActionRequest, actor_id: str) -> None:
        """保存已审批内存动作及审计记录。"""

        self.actions[action.id] = action
        self.audit(actor_id, "action.approved", action.id, {"node_id": action.node_id})

    def record_action_result(self, action_id: str, result: ActionResult) -> None:
        """记录内存执行结果并更新动作状态。"""

        action = self.actions.get(action_id)
        if action is None:
            raise KeyError(action_id)
        self.executions[action_id] = result.model_dump()
        action.status = ActionStatus.EXECUTED

    def audit(
        self,
        actor_id: str,
        action: str,
        target: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """为安全敏感操作追加一条只增不改的进程内审计记录。"""

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

    def append_audit(
        self,
        actor_id: str,
        action: str,
        target: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """提供与 SQL 状态服务一致的审计写入接口。"""

        self.audit(actor_id, action, target, details)

    @staticmethod
    def serialize_action(action: ActionRequest) -> dict[str, Any]:
        data = asdict(action)
        data["status"] = action.status.value
        for key in ("created_at", "expires_at", "approved_at"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data
