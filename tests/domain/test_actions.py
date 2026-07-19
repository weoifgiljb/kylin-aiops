from datetime import UTC, datetime, timedelta

import pytest
from kylin_aiops_api.actions import (
    ActionSigner,
    ActionStatus,
    ApprovalError,
    ExecutionGuard,
    create_action_request,
)


def test_unapproved_action_cannot_be_signed() -> None:
    action = create_action_request(
        incident_id="inc-1",
        node_id="app-01",
        action_name="restart_demo_service",
        parameters={"service": "kylin-demo-app"},
    )

    with pytest.raises(ApprovalError, match="approved"):
        ActionSigner(b"test-secret").sign(action)


def test_approved_action_is_signed_and_verified_once() -> None:
    now = datetime.now(UTC)
    action = create_action_request(
        incident_id="inc-1",
        node_id="app-01",
        action_name="restart_demo_service",
        parameters={"service": "kylin-demo-app"},
        now=now,
    )
    action.approve(operator_id="operator-1", now=now)
    envelope = ActionSigner(b"test-secret").sign(action, now=now)
    guard = ExecutionGuard(secret=b"test-secret")

    verified = guard.verify(envelope, node_id="app-01", now=now)
    assert verified.action_id == action.id
    assert action.status is ActionStatus.APPROVED

    guard.mark_executed(envelope.action_id)
    with pytest.raises(ApprovalError, match="already executed"):
        guard.verify(envelope, node_id="app-01", now=now)


def test_expired_or_wrong_target_action_is_rejected() -> None:
    now = datetime.now(UTC)
    action = create_action_request(
        incident_id="inc-1",
        node_id="db-01",
        action_name="terminate_fault_db_sessions",
        parameters={"db_user": "ops_fault"},
        now=now,
        ttl=timedelta(minutes=1),
    )
    action.approve(operator_id="operator-1", now=now)
    envelope = ActionSigner(b"test-secret").sign(action, now=now)
    guard = ExecutionGuard(secret=b"test-secret")

    with pytest.raises(ApprovalError, match="target"):
        guard.verify(envelope, node_id="app-01", now=now)
    with pytest.raises(ApprovalError, match="expired"):
        guard.verify(envelope, node_id="db-01", now=now + timedelta(minutes=2))
