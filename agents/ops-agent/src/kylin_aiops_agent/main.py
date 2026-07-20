"""Long-running agent loop for telemetry upload and approved-action polling."""

import logging
import time
from datetime import UTC, datetime

import httpx
from kylin_aiops_api.actions import ExecutionGuard

from .client import AgentApiClient
from .collector import SystemCollector
from .config import AgentSettings
from .executor import AllowlistedExecutor

LOGGER = logging.getLogger("kylin-aiops-agent")


def build_http_client(settings: AgentSettings) -> httpx.Client:
    """Create the outbound-only mTLS client from agent configuration."""

    cert: str | tuple[str, str] | None = None
    if settings.cert_file and settings.key_file:
        cert = (str(settings.cert_file), str(settings.key_file))
    verify: bool | str = str(settings.ca_file) if settings.ca_file else True
    return httpx.Client(base_url=settings.api_url, cert=cert, verify=verify, timeout=15)


def run() -> None:
    """Collect telemetry and execute at most allowlisted, signed commands forever."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = AgentSettings()
    collector = SystemCollector(settings.node_id)
    executor = AllowlistedExecutor(
        settings.node_id,
        ExecutionGuard(settings.action_signing_secret.encode()),
    )
    with build_http_client(settings) as http:
        api = AgentApiClient(http=http, token=settings.token, node_id=settings.node_id)
        while True:
            try:
                api.send_telemetry(collector.collect())
                envelope = api.next_action()
                if envelope is not None:
                    result = executor.execute(envelope, now=datetime.now(UTC))
                    api.send_result(envelope.action_id, result)
            except (httpx.HTTPError, ValueError, OSError) as exc:
                LOGGER.error("agent cycle failed: %s", exc)
            time.sleep(settings.interval_seconds)


if __name__ == "__main__":
    run()
