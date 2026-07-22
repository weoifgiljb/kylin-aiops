from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from kylin_aiops_api import load_data
from kylin_aiops_api.database import (
    Base,
    EvidenceRow,
    IncidentRow,
    NodeRow,
    ServiceRow,
    TelemetrySnapshotRow,
)
from kylin_aiops_api.load_data import LoadDataConfig, purge_load_data, seed_load_data
from sqlalchemy import create_engine, event, func, insert, select
from sqlalchemy.orm import Session


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'load-data.db'}")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    try:
        with Session(engine) as database_session:
            yield database_session
    finally:
        engine.dispose()


def table_counts(session: Session) -> dict[str, int]:
    return {
        "nodes": session.scalar(select(func.count()).select_from(NodeRow)),
        "services": session.scalar(select(func.count()).select_from(ServiceRow)),
        "telemetry": session.scalar(select(func.count()).select_from(TelemetrySnapshotRow)),
        "incidents": session.scalar(select(func.count()).select_from(IncidentRow)),
    }


def test_seed_creates_each_required_type(session: Session) -> None:
    counts = seed_load_data(session, LoadDataConfig(count=10, seed=42, batch_size=4))

    assert counts == {"nodes": 10, "services": 10, "telemetry": 10, "incidents": 10}
    assert table_counts(session) == {"nodes": 10, "services": 10, "telemetry": 10, "incidents": 10}
    assert (
        session.scalar(
            select(func.count())
            .select_from(ServiceRow)
            .join(NodeRow, ServiceRow.node_id == NodeRow.id)
            .where(NodeRow.id.like("load-node-%"))
        )
        == 10
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(IncidentRow)
            .join(NodeRow, IncidentRow.root_node_id == NodeRow.id)
            .where(NodeRow.id.like("load-node-%"))
        )
        == 10
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(TelemetrySnapshotRow)
            .join(NodeRow, TelemetrySnapshotRow.node_id == NodeRow.id)
            .where(NodeRow.id.like("load-node-%"))
        )
        == 10
    )


def test_seed_is_idempotent(session: Session) -> None:
    config = LoadDataConfig(count=10, seed=42, batch_size=4)

    seed_load_data(session, config)
    seed_load_data(session, config)

    assert table_counts(session) == {"nodes": 10, "services": 10, "telemetry": 10, "incidents": 10}


def test_purge_preserves_non_load_records(session: Session) -> None:
    session.add(
        NodeRow(
            id="real-node-01",
            hostname="real-node-01",
            architecture="aarch64",
            kylin_version="V10",
            status="online",
            last_seen_at=datetime(2026, 7, 22, tzinfo=UTC),
            display_name="生产节点",
            description="非压测数据",
            tags=["production"],
            enabled=True,
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )
    session.commit()
    session.add(
        ServiceRow(
            id="real-service-01",
            node_id="real-node-01",
            name="production-service",
            service_type="web",
            status="running",
            description="非压测服务",
            enabled=True,
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )
    session.add(
        TelemetrySnapshotRow(
            node_id="real-node-01",
            observed_at=datetime(2026, 7, 22, tzinfo=UTC),
            metrics={"cpu_percent": 20.0},
        )
    )
    session.add(
        IncidentRow(
            id="real-inc-01",
            title="生产事件",
            fault_type="network",
            severity="high",
            status="open",
            started_at=datetime(2026, 7, 22, tzinfo=UTC),
            ended_at=None,
            root_node_id="real-node-01",
            source="manual",
            assignee_user_id=None,
            handling_notes="非压测事件",
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )
    session.commit()
    seed_load_data(session, LoadDataConfig(count=10, seed=42, batch_size=4))

    counts = purge_load_data(session)

    assert counts == {"nodes": 10, "services": 10, "telemetry": 10, "incidents": 10}
    assert session.get(NodeRow, "real-node-01") is not None
    assert session.get(ServiceRow, "real-service-01") is not None
    assert session.get(TelemetrySnapshotRow, "real-node-01") is not None
    assert session.get(IncidentRow, "real-inc-01") is not None
    assert table_counts(session) == {"nodes": 1, "services": 1, "telemetry": 1, "incidents": 1}


def test_purge_rejects_load_data_referenced_by_real_evidence(session: Session) -> None:
    seed_load_data(session, LoadDataConfig(count=2, seed=42, batch_size=2))
    session.add(
        NodeRow(
            id="real-node-02",
            hostname="real-node-02",
            architecture="aarch64",
            kylin_version="V10",
            status="online",
            last_seen_at=datetime(2026, 7, 22, tzinfo=UTC),
            display_name="生产节点",
            description="非压测数据",
            tags=["production"],
            enabled=True,
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )
    session.commit()
    session.add(
        EvidenceRow(
            id="real-evidence-01",
            incident_id="load-inc-000000",
            node_id="real-node-02",
            kind="log",
            summary="真实证据引用压测事件",
            source_uri=None,
            observed_at=datetime(2026, 7, 22, tzinfo=UTC),
        )
    )
    session.commit()

    with pytest.raises(ValueError, match="关联"):
        purge_load_data(session)

    assert table_counts(session) == {"nodes": 3, "services": 2, "telemetry": 2, "incidents": 2}
    assert session.get(EvidenceRow, "real-evidence-01") is not None


def test_purge_rejects_real_service_on_load_node(session: Session) -> None:
    seed_load_data(session, LoadDataConfig(count=2, seed=42, batch_size=2))
    session.add(
        ServiceRow(
            id="real-service-on-load-node",
            node_id="load-node-000000",
            name="production-service",
            service_type="web",
            status="running",
            description="真实服务不得随压测节点级联删除",
            enabled=True,
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )
    session.commit()

    with pytest.raises(ValueError, match="关联"):
        purge_load_data(session)

    assert session.get(ServiceRow, "real-service-on-load-node") is not None
    assert table_counts(session) == {"nodes": 2, "services": 3, "telemetry": 2, "incidents": 2}


def test_purge_rejects_real_incident_on_load_node(session: Session) -> None:
    seed_load_data(session, LoadDataConfig(count=2, seed=42, batch_size=2))
    session.add(
        IncidentRow(
            id="real-inc-on-load-node",
            title="真实事件",
            fault_type="network",
            severity="high",
            status="open",
            started_at=datetime(2026, 7, 22, tzinfo=UTC),
            ended_at=None,
            root_node_id="load-node-000000",
            source="manual",
            assignee_user_id=None,
            handling_notes="真实事件不得随压测节点删除",
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )
    session.commit()

    with pytest.raises(ValueError, match="关联"):
        purge_load_data(session)

    assert session.get(IncidentRow, "real-inc-on-load-node") is not None
    assert table_counts(session) == {"nodes": 2, "services": 2, "telemetry": 2, "incidents": 3}


def test_purge_does_not_match_uppercase_prefix(session: Session) -> None:
    session.add(
        NodeRow(
            id="LOAD-NODE-000001",
            hostname="upper-node-01",
            architecture="aarch64",
            kylin_version="V10",
            status="online",
            last_seen_at=datetime(2026, 7, 22, tzinfo=UTC),
            display_name="大小写不同的真实节点",
            description="不应被前缀清理匹配",
            tags=["production"],
            enabled=True,
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )
    session.commit()
    seed_load_data(session, LoadDataConfig(count=2, seed=42, batch_size=2))

    purge_load_data(session)

    assert session.get(NodeRow, "LOAD-NODE-000001") is not None
    assert table_counts(session) == {"nodes": 1, "services": 0, "telemetry": 0, "incidents": 0}


def test_seed_rejects_pending_caller_changes(session: Session) -> None:
    pending_node = NodeRow(
        id="real-node-pending",
        hostname="real-node-pending",
        architecture="aarch64",
        kylin_version="V10",
        status="online",
        last_seen_at=datetime(2026, 7, 22, tzinfo=UTC),
        display_name="待提交生产节点",
        description="不得由压测写入提交",
        tags=["production"],
        enabled=True,
        version=1,
        archived_at=None,
        archived_by=None,
    )
    session.add(pending_node)

    with pytest.raises(ValueError, match="未提交|事务"):
        seed_load_data(session, LoadDataConfig(count=2, seed=42, batch_size=2))

    assert pending_node in session.new


def test_seed_rejects_open_transaction_from_core_dml(session: Session) -> None:
    session.execute(
        insert(NodeRow).values(
            id="real-node-core-dml",
            hostname="real-node-core-dml",
            architecture="aarch64",
            kylin_version="V10",
            status="online",
            last_seen_at=datetime(2026, 7, 22, tzinfo=UTC),
            display_name="核心语句写入节点",
            description="不得由压测操作提交",
            tags=["production"],
            enabled=True,
            version=1,
            archived_at=None,
            archived_by=None,
        )
    )

    with pytest.raises(ValueError, match="事务"):
        seed_load_data(session, LoadDataConfig(count=2, seed=42, batch_size=2))

    session.rollback()
    assert session.get(NodeRow, "real-node-core-dml") is None


class FakeSession:
    """记录内部锁函数的 SQL 执行，避免在集成测试中伪造并发场景。"""

    def __init__(self, dialect_name: str) -> None:
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self.statements: list[str] = []

    def execute(self, statement: object) -> None:
        self.statements.append(str(statement))


def test_postgresql_cleanup_lock_is_skipped_for_sqlite() -> None:
    postgresql_session = FakeSession("postgresql")
    sqlite_session = FakeSession("sqlite")

    load_data._lock_cleanup_tables(postgresql_session)
    load_data._lock_cleanup_tables(sqlite_session)

    assert postgresql_session.statements == [
        "LOCK TABLE nodes, services, incidents, telemetry_snapshots, dependency_edges, "
        "agent_credentials, evidence, diagnoses, action_requests IN SHARE ROW EXCLUSIVE MODE"
    ]
    assert sqlite_session.statements == []


@pytest.mark.parametrize(
    ("count", "seed", "batch_size"),
    [
        (0, 42, 4),
        (10, 42, 0),
        (True, 42, 4),
        (10, True, 4),
        (10, 42, False),
        ("10", 42, 4),
        (10, 42.0, 4),
    ],
)
def test_config_rejects_invalid_values(count: object, seed: object, batch_size: object) -> None:
    with pytest.raises(ValueError):
        LoadDataConfig(count=count, seed=seed, batch_size=batch_size)
