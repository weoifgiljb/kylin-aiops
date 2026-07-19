from datetime import UTC, datetime, timedelta

import httpx
from kylin_aiops_agent.client import AgentApiClient
from kylin_aiops_agent.collector import MetricBatch


def test_client_posts_telemetry_and_parses_next_action() -> None:
    now = datetime.now(UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer agent-token"
        if request.url.path.endswith("/telemetry"):
            return httpx.Response(202, json={"accepted": True, "node_id": "app-01"})
        return httpx.Response(
            200,
            json={
                "action_id": "act-1",
                "node_id": "app-01",
                "action_name": "restart_demo_service",
                "parameters": {"service": "kylin-demo-app"},
                "issued_at": now.isoformat(),
                "expires_at": (now + timedelta(minutes=5)).isoformat(),
                "signature": "signed",
            },
        )

    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://ops.local")
    client = AgentApiClient(http=http, token="agent-token", node_id="app-01")

    accepted = client.send_telemetry(MetricBatch("app-01", now, {"cpu_percent": 10.0}))
    envelope = client.next_action()

    assert accepted is True
    assert envelope is not None
    assert envelope.action_id == "act-1"
    assert envelope.expires_at.tzinfo is not None


def test_no_content_means_no_action() -> None:
    http = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(204)),
        base_url="https://ops.local",
    )
    client = AgentApiClient(http=http, token="agent-token", node_id="app-01")

    assert client.next_action() is None
