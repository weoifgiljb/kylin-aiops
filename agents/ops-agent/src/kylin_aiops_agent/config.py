"""Environment and certificate settings for the node agent."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Validated settings loaded from KYLIN_AIOPS_* variables or agent.env."""

    model_config = SettingsConfigDict(
        env_prefix="KYLIN_AIOPS_",
        env_file="/etc/kylin-aiops/agent.env",
    )

    api_url: str = "https://127.0.0.1:8443"
    node_id: str = Field(min_length=1)
    token: str = Field(min_length=8)
    action_signing_secret: str = Field(min_length=8)
    ca_file: Path | None = None
    cert_file: Path | None = None
    key_file: Path | None = None
    interval_seconds: float = Field(default=10, ge=2, le=300)
