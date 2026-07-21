import pytest
from kylin_aiops_api.database import Base, NodeRow
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError


def test_database_metadata_contains_all_planned_core_types() -> None:
    assert set(Base.metadata.tables) == {
        "nodes",
        "services",
        "dependency_edges",
        "incidents",
        "evidence",
        "diagnoses",
        "action_requests",
        "action_executions",
        "evaluation_runs",
        "trial_results",
        "audit_logs",
        "users",
        "auth_sessions",
        "agent_credentials",
    }


def test_two_sessions_cannot_commit_the_same_resource_version(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'concurrency.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as setup:
        setup.add(NodeRow(id="node-01", display_name="节点一", status="offline", version=1))
        setup.commit()

    first = Session(engine)
    second = Session(engine)
    first_row = first.get(NodeRow, "node-01")
    second_row = second.get(NodeRow, "node-01")
    assert first_row is not None and second_row is not None
    first_row.display_name = "第一个提交"
    first_row.version += 1
    second_row.display_name = "第二个提交"
    second_row.version += 1
    first.commit()

    with pytest.raises(StaleDataError):
        second.commit()
    first.close()
    second.close()
