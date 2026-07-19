import pytest
from kylin_aiops_api.actions import create_action_request
from kylin_aiops_api.store import InMemoryStore
from kylin_aiops_diagnosis.mcp_server import McpToolService


def test_execute_tool_cannot_bypass_action_approval() -> None:
    store = InMemoryStore(seed_demo=True)
    action = create_action_request(
        incident_id="inc-db-pool",
        node_id="db-01",
        action_name="terminate_fault_db_sessions",
        parameters={"db_user": "ops_fault"},
    )
    store.actions[action.id] = action

    with pytest.raises(PermissionError, match="approved"):
        McpToolService(store).execute_approved_action(action.id)


def test_query_tools_return_evidence_and_topology_without_side_effects() -> None:
    service = McpToolService(InMemoryStore(seed_demo=True))

    assert service.search_logs("inc-db-pool")[0]["id"] == "ev-db-log"
    assert service.get_topology()[1] == {
        "source": "app-01",
        "target": "db-01",
        "confidence": 1.0,
    }
