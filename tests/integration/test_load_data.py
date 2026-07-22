from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kylin_aiops_api.database import (
    Base,
    IncidentRow,
    NodeRow,
    ServiceRow,
    TelemetrySnapshotRow,
)
from kylin_aiops_api.load_data import LoadDataConfig, purge_load_data, seed_load_data
from sqlalchemy import create_engine, event, func, select
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


@pytest.mark.parametrize("count,batch_size", [(0, 4), (10, 0)])
def test_config_rejects_non_positive_sizes(count: int, batch_size: int) -> None:
    with pytest.raises(ValueError):
        LoadDataConfig(count=count, seed=42, batch_size=batch_size)
