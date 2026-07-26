from datetime import UTC, datetime

import pytest
from kylin_aiops_api.actions import create_action_request
from kylin_aiops_api.database import (
    ActionExecutionRow,
    ActionRequestRow,
    Base,
    DependencyEdgeRow,
    IncidentRow,
    NodeRow,
    ServiceRow,
    TelemetrySnapshotRow,
)
from kylin_aiops_api.persistence import Database
from kylin_aiops_api.queue import InMemoryActionQueue
from kylin_aiops_api.schemas import ActionResult
from kylin_aiops_api.sql_store import SqlControlPlaneStore


@pytest.fixture
def sql_store(tmp_path):
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'sql-store.db'}")
    Base.metadata.create_all(database.engine)
    store = SqlControlPlaneStore(database.sessions, InMemoryActionQueue())
    try:
        yield store, database.sessions
    finally:
        database.dispose()


def test_telemetry_updates_only_observed_node_fields(sql_store) -> None:
    store, sessions = sql_store
    with sessions() as session:
        session.add(
            NodeRow(
                id="node-01",
                hostname="node-01",
                architecture="aarch64",
                kylin_version="V10",
                status="offline",
                last_seen_at=None,
                display_name="教学楼节点",
                description="保留管理描述",
                tags=["教学楼"],
                enabled=True,
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )
        session.commit()

    observed_at = datetime(2026, 7, 22, tzinfo=UTC)
    store.record_telemetry("node-01", observed_at, {"cpu_percent": 12.0})
    overview_node = store.overview()["nodes"][0]

    with sessions() as session:
        node = session.get(NodeRow, "node-01")
        telemetry = session.get(TelemetrySnapshotRow, "node-01")
        assert node is not None
        assert node.display_name == "教学楼节点"
        assert node.description == "保留管理描述"
        assert node.tags == ["教学楼"]
        assert node.status == "online"
        assert telemetry is not None
        assert telemetry.metrics == {"cpu_percent": 12.0}
        assert overview_node["metrics"] == {"cpu_percent": 12.0}


def test_action_lifecycle_writes_only_target_rows(sql_store) -> None:
    store, sessions = sql_store
    now = datetime.now(UTC)
    with sessions() as session:
        session.add(
            NodeRow(
                id="db-01",
                hostname="db-01",
                architecture="aarch64",
                kylin_version="V10",
                status="online",
                last_seen_at=now,
                display_name="数据库节点",
                description="",
                tags=[],
                enabled=True,
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )
        session.add(
            IncidentRow(
                id="inc-01",
                title="连接池耗尽",
                fault_type="db_pool",
                severity="high",
                status="open",
                started_at=now,
                ended_at=None,
                root_node_id="db-01",
                source="manual",
                assignee_user_id=None,
                handling_notes="",
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )
        session.commit()

    action = create_action_request(
        incident_id="inc-01",
        node_id="db-01",
        action_name="terminate_fault_db_sessions",
        parameters={"db_user": "ops_fault"},
    )
    store.create_action(action, "operator-01")
    loaded = store.get_action(action.id)
    assert loaded is not None
    loaded.approve("operator-01", now=now)
    store.save_approved_action(loaded, "operator-01")
    store.record_action_result(
        action.id,
        ActionResult(exit_code=0, health_check="passed"),
    )

    with sessions() as session:
        request_row = session.get(ActionRequestRow, action.id)
        execution = session.get(ActionExecutionRow, f"exec-{action.id}")
        assert request_row is not None and request_row.status == "executed"
        assert execution is not None and execution.health_check_passed is True


def test_overview_aggregates_large_sqlite_topology_without_physical_nodes(sql_store) -> None:
    store, sessions = sql_store
    now = datetime.now(UTC)
    nodes = []
    services = []
    for index in range(240):
        service_type = "nginx" if index < 180 else "mysql"
        status = "offline" if 120 <= index < 180 else "online"
        node_id = f"node-{index:03d}"
        nodes.append(
            NodeRow(
                id=node_id,
                hostname=node_id,
                architecture="aarch64",
                kylin_version="V10",
                status=status,
                last_seen_at=now,
                display_name=node_id,
                description="",
                tags=[],
                enabled=True,
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )
        services.append(
            ServiceRow(
                id=f"svc-{index:03d}",
                node_id=node_id,
                name=service_type,
                service_type=service_type,
                status=status,
                description="",
                enabled=True,
                version=1,
                archived_at=None,
                archived_by=None,
            )
        )
    with sessions() as session:
        session.add_all(nodes)
        session.add_all(services)
        session.flush()
        session.add_all(
            [
                DependencyEdgeRow(
                    source_service_id=f"svc-{index:03d}",
                    target_service_id=f"svc-{180 + index % 60:03d}",
                    source="observed",
                    confidence=0.75,
                    observed_at=now,
                    version=1,
                    archived_at=None,
                    archived_by=None,
                )
                for index in range(120)
            ]
            + [
                DependencyEdgeRow(
                    source_service_id=f"svc-{180 + index:03d}",
                    target_service_id=f"svc-{index:03d}",
                    source="observed",
                    confidence=0.9,
                    observed_at=now,
                    version=1,
                    archived_at=None,
                    archived_by=None,
                )
                for index in range(60)
            ]
        )
        session.commit()

    overview = store.overview()

    assert overview["nodes"] == []
    assert overview["topology"] == []
    assert overview["total_nodes"] == 240
    assert overview["online_nodes"] == 180
    assert {
        (group["service"], group["status"]): group["count"]
        for group in overview["topology_groups"]
    } == {
        ("nginx", "online"): 120,
        ("nginx", "offline"): 60,
        ("mysql", "online"): 60,
    }
    grouped_edges = {
        (edge["source_service"], edge["target_service"]): edge
        for edge in overview["topology_group_edges"]
    }
    assert grouped_edges[("nginx", "mysql")]["count"] == 120
    assert grouped_edges[("nginx", "mysql")]["confidence"] == pytest.approx(0.75)
    assert grouped_edges[("mysql", "nginx")]["count"] == 60
    assert grouped_edges[("mysql", "nginx")]["confidence"] == pytest.approx(0.9)
