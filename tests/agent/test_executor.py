from datetime import UTC, datetime

import pytest
from kylin_aiops_agent.executor import AllowlistedExecutor, UnsafeAction
from kylin_aiops_api.actions import ActionSigner, ExecutionGuard, create_action_request


def approved_envelope(action_name: str, node_id: str, parameters: dict):
    now = datetime.now(UTC)
    action = create_action_request(
        incident_id="inc-1",
        node_id=node_id,
        action_name=action_name,
        parameters=parameters,
        now=now,
    )
    action.approve("operator-1", now)
    return ActionSigner(b"test-secret").sign(action, now), now


def test_executor_builds_fixed_argv_without_shell() -> None:
    envelope, now = approved_envelope(
        "restart_demo_service", "app-01", {"service": "kylin-demo-app"}
    )
    executor = AllowlistedExecutor("app-01", ExecutionGuard(b"test-secret"))

    command = executor.prepare(envelope, now)

    assert command.argv == ["/usr/bin/systemctl", "restart", "kylin-demo-app.service"]
    assert command.shell is False


def test_executor_rejects_arbitrary_service_or_database_user() -> None:
    service, now = approved_envelope(
        "restart_demo_service", "app-01", {"service": "sshd"}
    )
    database, _ = approved_envelope(
        "terminate_fault_db_sessions", "db-01", {"db_user": "root"}
    )

    with pytest.raises(UnsafeAction, match="service"):
        AllowlistedExecutor("app-01", ExecutionGuard(b"test-secret")).prepare(service, now)
    with pytest.raises(UnsafeAction, match="ops_fault"):
        AllowlistedExecutor("db-01", ExecutionGuard(b"test-secret")).prepare(database, now)


def test_fault_file_cannot_escape_controlled_directory() -> None:
    envelope, now = approved_envelope(
        "remove_fault_file",
        "db-01",
        {"experiment_id": "../../etc", "filename": "passwd"},
    )

    with pytest.raises(UnsafeAction, match="experiment"):
        AllowlistedExecutor("db-01", ExecutionGuard(b"test-secret")).prepare(envelope, now)
