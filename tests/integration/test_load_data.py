from datetime import UTC, datetime

import pytest
from kylin_aiops_api.database import (
    Base,
    IncidentRow,
    NodeRow,
    ServiceRow,
    TelemetrySnapshotRow,
)
from kylin_aiops_api.load_data import LoadDataConfig, purge_load_data, seed_load_data
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'load-data.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session
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
    assert session.scalars(select(ServiceRow).order_by(ServiceRow.id)).first().node_id.startswith(
        "load-node-"
    )
    assert session.scalars(select(IncidentRow).order_by(IncidentRow.id)).first().root_node_id.startswith(
        "load-node-"
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
    seed_load_data(session, LoadDataConfig(count=10, seed=42, batch_size=4))

    counts = purge_load_data(session)

    assert counts == {"nodes": 10, "services": 10, "telemetry": 10, "incidents": 10}
    assert session.get(NodeRow, "real-node-01") is not None
    assert session.scalar(select(func.count()).select_from(NodeRow)) == 1


@pytest.mark.parametrize("count,batch_size", [(0, 4), (10, 0)])
def test_config_rejects_non_positive_sizes(count: int, batch_size: int) -> None:
    with pytest.raises(ValueError):
        LoadDataConfig(count=count, seed=42, batch_size=batch_size)
