from pathlib import Path
from typing import Any

from kylin_aiops_api.actions import ActionStatus
from kylin_aiops_api.store import InMemoryStore


class McpToolService:
    def __init__(self, store: InMemoryStore, runbook_dir: Path | None = None) -> None:
        self.store = store
        self.runbook_dir = runbook_dir

    def query_metrics(self, incident_id: str) -> list[dict[str, Any]]:
        incident = self._incident(incident_id)
        return [item for item in incident["evidence"] if item["kind"] == "metric"]

    def search_logs(self, incident_id: str) -> list[dict[str, Any]]:
        incident = self._incident(incident_id)
        return [item for item in incident["evidence"] if item["kind"] == "log"]

    def get_traces(self, incident_id: str) -> list[dict[str, Any]]:
        incident = self._incident(incident_id)
        return [item for item in incident["evidence"] if item["kind"] == "trace"]

    def get_topology(self) -> list[dict[str, Any]]:
        return self.store.overview()["topology"]

    def get_runbook(self, name: str) -> str:
        if not self.runbook_dir or not name.replace("-", "").isalnum():
            return "Runbook not found"
        path = (self.runbook_dir / f"{name}.md").resolve()
        if path.parent != self.runbook_dir.resolve() or not path.is_file():
            return "Runbook not found"
        return path.read_text(encoding="utf-8")

    def preview_action(self, action_id: str) -> dict[str, Any]:
        action = self.store.actions.get(action_id)
        if action is None:
            raise KeyError("Action request not found")
        return self.store.serialize_action(action)

    def execute_approved_action(self, action_id: str) -> dict[str, str]:
        action = self.store.actions.get(action_id)
        if action is None:
            raise KeyError("Action request not found")
        if action.status is not ActionStatus.APPROVED:
            raise PermissionError("Action must already be approved")
        return {"action_id": action_id, "status": "approved_for_agent_delivery"}

    def _incident(self, incident_id: str) -> dict[str, Any]:
        incident = self.store.incidents.get(incident_id)
        if incident is None:
            raise KeyError("Incident not found")
        return incident


def build_mcp_server(service: McpToolService):
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("kylin-aiops", stateless_http=True, json_response=True)

    mcp.tool()(service.query_metrics)
    mcp.tool()(service.search_logs)
    mcp.tool()(service.get_traces)
    mcp.tool()(service.get_topology)
    mcp.tool()(service.get_runbook)
    mcp.tool()(service.preview_action)
    mcp.tool()(service.execute_approved_action)
    return mcp


def main() -> None:
    service = McpToolService(InMemoryStore(seed_demo=True))
    build_mcp_server(service).run(transport="streamable-http")


if __name__ == "__main__":
    main()
