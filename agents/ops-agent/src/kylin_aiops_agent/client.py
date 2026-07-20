"""Typed HTTP client for the outbound agent protocol."""

from dataclasses import asdict
from datetime import datetime

import httpx
from kylin_aiops_api.actions import ActionEnvelope

from .collector import MetricBatch
from .executor import ExecutionResult


class AgentApiClient:
    """Send telemetry, poll signed actions, and return execution results."""

    def __init__(self, http: httpx.Client, token: str, node_id: str) -> None:
        self.http = http
        self.node_id = node_id
        self.headers = {"Authorization": f"Bearer {token}"}

    def send_telemetry(self, batch: MetricBatch) -> bool:
        payload = asdict(batch)
        payload["observed_at"] = batch.observed_at.isoformat()
        response = self.http.post("/agent/v1/telemetry", headers=self.headers, json=payload)
        response.raise_for_status()
        return bool(response.json()["accepted"])

    def next_action(self) -> ActionEnvelope | None:
        response = self.http.get(
            "/agent/v1/actions/next",
            headers=self.headers,
            params={"node_id": self.node_id},
        )
        if response.status_code == 204:
            return None
        response.raise_for_status()
        data = response.json()
        data["issued_at"] = datetime.fromisoformat(data["issued_at"])
        data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return ActionEnvelope(**data)

    def send_result(self, action_id: str, result: ExecutionResult) -> None:
        response = self.http.post(
            f"/agent/v1/actions/{action_id}/result",
            headers=self.headers,
            json=asdict(result),
        )
        response.raise_for_status()
