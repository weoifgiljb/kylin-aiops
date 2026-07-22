"""提供可重复执行且可安全清理的压测演示数据。"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session, relationship

from kylin_aiops_api.database import (
    IncidentRow,
    NodeRow,
    ServiceRow,
    TelemetrySnapshotRow,
)

LOAD_NODE_PREFIX = "load-node-"
LOAD_SERVICE_PREFIX = "load-service-"
LOAD_INCIDENT_PREFIX = "load-inc-"

_START_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _configure_insert_dependencies() -> None:
    """补齐模型未声明的父子依赖，保证 SQLite 外键模式下父记录先写入。"""
    dependencies = (
        ("_load_data_services", ServiceRow, ServiceRow.node_id),
        ("_load_data_telemetry", TelemetrySnapshotRow, TelemetrySnapshotRow.node_id),
        ("_load_data_incidents", IncidentRow, IncidentRow.root_node_id),
    )
    for name, target, foreign_key in dependencies:
        if name not in NodeRow.__mapper__.attrs:
            NodeRow.__mapper__.add_property(
                name,
                relationship(target, foreign_keys=[foreign_key]),
            )


_configure_insert_dependencies()


@dataclass(frozen=True)
class LoadDataConfig:
    """定义压测数据的规模、确定性种子与事务批次大小。"""

    count: int = 10_000
    seed: int = 42
    batch_size: int = 1_000

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("count 必须为正数")
        if self.batch_size <= 0:
            raise ValueError("batch_size 必须为正数")


def seed_load_data(session: Session, config: LoadDataConfig) -> dict[str, int]:
    """写入由配置唯一决定的节点、服务、遥测和事件数据。"""
    for index in range(config.count):
        node_id = f"{LOAD_NODE_PREFIX}{index:06d}"
        service_id = f"{LOAD_SERVICE_PREFIX}{index:06d}"
        incident_id = f"{LOAD_INCIDENT_PREFIX}{index:06d}"
        observed_at = _START_TIME + timedelta(seconds=index)

        session.merge(
            NodeRow(
                id=node_id,
                hostname=node_id,
                architecture=("x86_64", "aarch64")[index % 2],
                kylin_version="V10",
                status=("online", "online", "offline")[index % 3],
                last_seen_at=observed_at,
                display_name=f"压测节点 {index:06d}",
                description="由负载数据生成器创建的演示节点",
                tags=["load-data"],
                enabled=True,
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )
        session.merge(
            ServiceRow(
                id=service_id,
                node_id=node_id,
                name=f"load-service-{index:06d}",
                service_type=("nginx", "java", "mysql")[index % 3],
                status="running",
                description="由负载数据生成器创建的演示服务",
                enabled=True,
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )
        session.merge(
            TelemetrySnapshotRow(
                node_id=node_id,
                observed_at=observed_at,
                metrics={
                    "cpu_percent": float((config.seed + index * 17) % 101),
                    "memory_percent": float((config.seed + index * 23) % 101),
                    "disk_percent": float((config.seed + index * 29) % 101),
                    "load_1m": float((config.seed + index * 31) % 101),
                },
            )
        )
        incident_status = ("open", "acknowledged", "resolved")[index % 3]
        session.merge(
            IncidentRow(
                id=incident_id,
                title=f"压测事件 {index:06d}",
                fault_type="load-test",
                severity=("low", "medium", "high", "critical")[index % 4],
                status=incident_status,
                started_at=observed_at,
                ended_at=observed_at if incident_status == "resolved" else None,
                root_node_id=node_id,
                source="load-data",
                assignee_user_id=None,
                handling_notes="由负载数据生成器创建的演示事件",
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )

        if (index + 1) % config.batch_size == 0:
            session.commit()

    if config.count % config.batch_size:
        session.commit()

    return _counts(config.count)


def purge_load_data(session: Session) -> dict[str, int]:
    """仅删除带压测前缀的数据，并依照外键依赖顺序完成单次提交。"""
    counts = {
        "nodes": _count_prefix(session, NodeRow.id, LOAD_NODE_PREFIX),
        "services": _count_prefix(session, ServiceRow.id, LOAD_SERVICE_PREFIX),
        "telemetry": _count_prefix(session, TelemetrySnapshotRow.node_id, LOAD_NODE_PREFIX),
        "incidents": _count_prefix(session, IncidentRow.id, LOAD_INCIDENT_PREFIX),
    }

    session.execute(delete(IncidentRow).where(IncidentRow.id.like(f"{LOAD_INCIDENT_PREFIX}%")))
    session.execute(
        delete(TelemetrySnapshotRow).where(TelemetrySnapshotRow.node_id.like(f"{LOAD_NODE_PREFIX}%"))
    )
    session.execute(delete(ServiceRow).where(ServiceRow.id.like(f"{LOAD_SERVICE_PREFIX}%")))
    session.execute(delete(NodeRow).where(NodeRow.id.like(f"{LOAD_NODE_PREFIX}%")))
    session.commit()

    return counts


def _count_prefix(session: Session, column: InstrumentedAttribute[str], prefix: str) -> int:
    """统计指定主键或外键前缀的数据量，避免清理时触及真实记录。"""
    statement = select(func.count()).select_from(column.class_).where(column.like(f"{prefix}%"))
    return int(session.scalar(statement) or 0)


def _counts(count: int) -> dict[str, int]:
    """构造公开接口约定的四类写入数量。"""
    return {"nodes": count, "services": count, "telemetry": count, "incidents": count}
