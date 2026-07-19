from kylin_aiops_api.database import Base


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
    }
