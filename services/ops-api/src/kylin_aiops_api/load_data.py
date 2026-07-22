"""提供可重复执行且可安全清理的压测演示数据。"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import InstrumentedAttribute, Session

from kylin_aiops_api.database import (
    ActionRequestRow,
    AgentCredentialRow,
    DependencyEdgeRow,
    DiagnosisRow,
    EvidenceRow,
    IncidentRow,
    NodeRow,
    ServiceRow,
    TelemetrySnapshotRow,
)

LOAD_NODE_PREFIX = "load-node-"
LOAD_SERVICE_PREFIX = "load-service-"
LOAD_INCIDENT_PREFIX = "load-inc-"

_START_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class LoadDataConfig:
    """定义压测数据的规模、确定性种子与事务批次大小。"""

    count: int = 10_000
    seed: int = 42
    batch_size: int = 1_000

    def __post_init__(self) -> None:
        for name, value in (
            ("count", self.count),
            ("seed", self.seed),
            ("batch_size", self.batch_size),
        ):
            if type(value) is not int:
                raise ValueError(f"{name} 必须为 int")
        if self.count <= 0:
            raise ValueError("count 必须为正数")
        if self.batch_size <= 0:
            raise ValueError("batch_size 必须为正数")


def seed_load_data(session: Session, config: LoadDataConfig) -> dict[str, int]:
    """批量写入确定性数据；调用方须传入新建、专用且未处于事务中的 Session。"""
    _reject_pending_changes(session)
    insert = _insert_for_session(session)

    try:
        for start in range(0, config.count, config.batch_size):
            end = min(start + config.batch_size, config.count)
            node_rows, service_rows, telemetry_rows, incident_rows = _build_batch(
                config, start, end
            )
            _upsert(session, insert, NodeRow, node_rows)
            _upsert(session, insert, ServiceRow, service_rows)
            _upsert(session, insert, TelemetrySnapshotRow, telemetry_rows)
            _upsert(session, insert, IncidentRow, incident_rows)
            session.commit()
    except Exception:
        session.rollback()
        raise

    return _counts(config.count)


def purge_load_data(session: Session) -> dict[str, int]:
    """安全清理压测数据；调用方须传入新建、专用且未处于事务中的 Session。"""
    _reject_pending_changes(session)

    try:
        _lock_cleanup_tables(session)
        _reject_external_references(session)
        counts = {
            "nodes": _count_prefix(session, NodeRow.id, LOAD_NODE_PREFIX),
            "services": _count_prefix(session, ServiceRow.id, LOAD_SERVICE_PREFIX),
            "telemetry": _count_prefix(session, TelemetrySnapshotRow.node_id, LOAD_NODE_PREFIX),
            "incidents": _count_prefix(session, IncidentRow.id, LOAD_INCIDENT_PREFIX),
        }

        session.execute(
            delete(IncidentRow).where(_has_prefix(IncidentRow.id, LOAD_INCIDENT_PREFIX))
        )
        session.execute(
            delete(TelemetrySnapshotRow).where(
                _has_prefix(TelemetrySnapshotRow.node_id, LOAD_NODE_PREFIX)
            )
        )
        session.execute(delete(ServiceRow).where(_has_prefix(ServiceRow.id, LOAD_SERVICE_PREFIX)))
        session.execute(delete(NodeRow).where(_has_prefix(NodeRow.id, LOAD_NODE_PREFIX)))
        session.commit()
    except Exception:
        session.rollback()
        raise

    return counts


def _build_batch(
    config: LoadDataConfig, start: int, end: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """构造一个批次的四类行字典，避免逐条 ORM 合并带来的查询开销。"""
    node_rows: list[dict[str, Any]] = []
    service_rows: list[dict[str, Any]] = []
    telemetry_rows: list[dict[str, Any]] = []
    incident_rows: list[dict[str, Any]] = []

    for index in range(start, end):
        node_id = f"{LOAD_NODE_PREFIX}{index:06d}"
        observed_at = _START_TIME + timedelta(seconds=index)
        incident_status = ("open", "acknowledged", "resolved")[index % 3]
        node_rows.append(
            {
                "id": node_id,
                "hostname": node_id,
                "architecture": ("x86_64", "aarch64")[index % 2],
                "kylin_version": "V10",
                "status": ("online", "online", "offline")[index % 3],
                "last_seen_at": observed_at,
                "display_name": f"压测节点 {index:06d}",
                "description": "由负载数据生成器创建的演示节点",
                "tags": ["load-data"],
                "enabled": True,
                "version": 1,
                "archived_at": None,
                "archived_by": None,
            }
        )
        service_rows.append(
            {
                "id": f"{LOAD_SERVICE_PREFIX}{index:06d}",
                "node_id": node_id,
                "name": f"load-service-{index:06d}",
                "service_type": ("nginx", "java", "mysql")[index % 3],
                "status": "running",
                "description": "由负载数据生成器创建的演示服务",
                "enabled": True,
                "version": 1,
                "archived_at": None,
                "archived_by": None,
            }
        )
        telemetry_rows.append(
            {
                "node_id": node_id,
                "observed_at": observed_at,
                "metrics": {
                    "cpu_percent": float((config.seed + index * 17) % 101),
                    "memory_percent": float((config.seed + index * 23) % 101),
                    "disk_percent": float((config.seed + index * 29) % 101),
                    "load_1m": float((config.seed + index * 31) % 101),
                },
            }
        )
        incident_rows.append(
            {
                "id": f"{LOAD_INCIDENT_PREFIX}{index:06d}",
                "title": f"压测事件 {index:06d}",
                "fault_type": "load-test",
                "severity": ("low", "medium", "high", "critical")[index % 4],
                "status": incident_status,
                "started_at": observed_at,
                "ended_at": observed_at if incident_status == "resolved" else None,
                "root_node_id": node_id,
                "source": "load-data",
                "assignee_user_id": None,
                "handling_notes": "由负载数据生成器创建的演示事件",
                "version": 1,
                "archived_at": None,
                "archived_by": None,
            }
        )

    return node_rows, service_rows, telemetry_rows, incident_rows


def _insert_for_session(session: Session) -> Callable[..., Any]:
    """选择支持 ON CONFLICT 的方言专属 insert，避免静默降级为非幂等写入。"""
    if session.bind is None:
        raise ValueError("session 必须绑定 SQLite 或 PostgreSQL 数据库")
    dialect_name = session.bind.dialect.name
    if dialect_name == "sqlite":
        return sqlite_insert
    if dialect_name == "postgresql":
        return postgresql_insert
    raise ValueError(f"不支持的数据库方言: {dialect_name}")


def _upsert(
    session: Session,
    insert: Callable[..., Any],
    model: type[Any],
    rows: Sequence[dict[str, Any]],
) -> None:
    """以主键冲突更新的方式批量写入同类行，保持重复执行的行数稳定。"""
    statement = insert(model)
    primary_keys = [column.name for column in model.__table__.primary_key.columns]
    update_values = {
        name: getattr(statement.excluded, name)
        for name in rows[0]
        if name not in primary_keys
    }
    session.execute(
        statement.on_conflict_do_update(index_elements=primary_keys, set_=update_values),
        rows,
    )


def _reject_pending_changes(session: Session) -> None:
    """拒绝调用方事务或未提交变更，防止本模块的 commit 扩大事务范围。"""
    if session.in_transaction():
        raise ValueError("session 已处于事务中，拒绝执行压测数据操作")
    if session.new or session.dirty or session.deleted:
        raise ValueError("session 存在未提交变更，拒绝执行压测数据操作")


def _lock_cleanup_tables(session: Session) -> None:
    """在 PostgreSQL 锁定相关表，防止检查与删除之间插入引用记录的竞态。"""
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text(
                "LOCK TABLE nodes, services, incidents, telemetry_snapshots, dependency_edges, "
                "agent_credentials, evidence, diagnoses, action_requests IN SHARE ROW "
                "EXCLUSIVE MODE"
            )
        )


def _reject_external_references(session: Session) -> None:
    """发现真实关联记录时拒绝清理，防止数据库级联删除超出压测范围的数据。"""
    checks = (
        (
            ServiceRow,
            and_(
                _has_prefix(ServiceRow.node_id, LOAD_NODE_PREFIX),
                ~_has_prefix(ServiceRow.id, LOAD_SERVICE_PREFIX),
            ),
        ),
        (
            IncidentRow,
            and_(
                _has_prefix(IncidentRow.root_node_id, LOAD_NODE_PREFIX),
                ~_has_prefix(IncidentRow.id, LOAD_INCIDENT_PREFIX),
            ),
        ),
        (
            DependencyEdgeRow,
            or_(
                _has_prefix(DependencyEdgeRow.source_service_id, LOAD_SERVICE_PREFIX),
                _has_prefix(DependencyEdgeRow.target_service_id, LOAD_SERVICE_PREFIX),
            ),
        ),
        (AgentCredentialRow, _has_prefix(AgentCredentialRow.node_id, LOAD_NODE_PREFIX)),
        (
            EvidenceRow,
            or_(
                _has_prefix(EvidenceRow.node_id, LOAD_NODE_PREFIX),
                _has_prefix(EvidenceRow.incident_id, LOAD_INCIDENT_PREFIX),
            ),
        ),
        (DiagnosisRow, _has_prefix(DiagnosisRow.incident_id, LOAD_INCIDENT_PREFIX)),
        (
            ActionRequestRow,
            or_(
                _has_prefix(ActionRequestRow.node_id, LOAD_NODE_PREFIX),
                _has_prefix(ActionRequestRow.incident_id, LOAD_INCIDENT_PREFIX),
            ),
        ),
    )
    for model, condition in checks:
        statement = select(func.count()).select_from(model).where(condition)
        if session.scalar(statement):
            raise ValueError("压测数据仍存在真实关联记录，拒绝清理")


def _has_prefix(column: InstrumentedAttribute[str], prefix: str) -> Any:
    """使用大小写敏感的前缀比较，避免 SQLite 的 LIKE 默认大小写折叠。"""
    return func.substr(column, 1, len(prefix)) == prefix


def _count_prefix(session: Session, column: InstrumentedAttribute[str], prefix: str) -> int:
    """统计指定主键或外键前缀的数据量，避免清理时触及真实记录。"""
    statement = select(func.count()).select_from(column.class_).where(_has_prefix(column, prefix))
    return int(session.scalar(statement) or 0)


def _counts(count: int) -> dict[str, int]:
    """构造公开接口约定的四类写入数量。"""
    return {"nodes": count, "services": count, "telemetry": count, "incidents": count}
