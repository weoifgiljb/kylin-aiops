"""Runtime health aggregation for components shown in the operations console.

The settings page must report observed process state, not deployment guidance or
configuration intent.  This module performs bounded, read-only probes and maps
downstream responses to a small status vocabulary that the frontend can render.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel

RuntimeState = Literal["available", "degraded", "unconfigured", "unreachable"]
StatusGet = Callable[..., httpx.Response]


class ComponentStatus(BaseModel):
    """Observed state of one runtime dependency."""

    status: RuntimeState
    detail: str
    backend: str | None = None
    model: str | None = None


class SystemStatus(BaseModel):
    """Status snapshot returned to authenticated console users."""

    checked_at: datetime
    components: dict[str, ComponentStatus]


class RuntimeStatusProbe:
    """Probe model runtimes without turning an optional outage into an API outage."""

    def __init__(
        self,
        *,
        model_service_url: str | None,
        generative_base_url: str | None,
        generative_model: str,
        generative_provider: str | None,
        get: StatusGet,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.model_service_url = model_service_url.rstrip("/") if model_service_url else None
        self.generative_base_url = generative_base_url.rstrip("/") if generative_base_url else None
        self.generative_model = generative_model
        self.generative_provider = generative_provider
        self.get = get
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls, get: StatusGet) -> RuntimeStatusProbe:
        """Build a probe from the same environment used to wire runtime clients."""

        return cls(
            model_service_url=os.getenv("MODEL_SERVICE_URL"),
            generative_base_url=os.getenv("MINDIE_BASE_URL"),
            generative_model=os.getenv("MINDIE_MODEL", "kylin-ops-llm"),
            generative_provider=os.getenv("MINDIE_PROVIDER"),
            get=get,
        )

    def snapshot(self) -> SystemStatus:
        """Return one bounded status snapshot; optional dependencies may degrade independently."""

        return SystemStatus(
            checked_at=datetime.now(UTC),
            components={
                "deterministic_diagnosis": ComponentStatus(
                    status="available",
                    backend="rules_topology",
                    detail="规则与拓扑诊断模块已加载",
                ),
                "mindspore": self._probe_model_service(),
                "generative_ai": self._probe_generative_runtime(),
            },
        )

    def _probe_model_service(self) -> ComponentStatus:
        if not self.model_service_url:
            return ComponentStatus(
                status="unconfigured",
                detail="未配置 MODEL_SERVICE_URL",
            )
        try:
            response = self.get(
                f"{self.model_service_url}/healthz",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            backend = str(response.json()["backend"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            return ComponentStatus(
                status="unreachable",
                detail=f"模型服务探测失败：{type(exc).__name__}",
            )

        # HTTP 进程健康时仍可能只提供确定性降级能力，需要与昇腾 MindSpore 推理区分。
        if backend == "MindSporePredictor":
            return ComponentStatus(
                status="available",
                backend=backend,
                detail="MindSpore checkpoint 已加载",
            )
        return ComponentStatus(
            status="degraded",
            backend=backend,
            detail="模型服务在线，但正在使用确定性降级推理",
        )

    def _probe_generative_runtime(self) -> ComponentStatus:
        if not self.generative_base_url:
            return ComponentStatus(
                status="unconfigured",
                backend=self.generative_provider,
                model=self.generative_model,
                detail="未配置 MINDIE_BASE_URL",
            )
        try:
            response = self.get(
                f"{self.generative_base_url}/v1/models",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            models = {
                str(item.get("id") or item.get("model"))
                for item in response.json().get("data", [])
                if isinstance(item, dict)
            }
        except (httpx.HTTPError, AttributeError, TypeError, ValueError) as exc:
            return ComponentStatus(
                status="unreachable",
                backend=self.generative_provider,
                model=self.generative_model,
                detail=f"生成式模型探测失败：{type(exc).__name__}",
            )

        provider = self.generative_provider or self._detect_generative_provider()
        if self.generative_model not in models:
            return ComponentStatus(
                status="degraded",
                backend=provider,
                model=self.generative_model,
                detail="接口可达，但未发现配置的模型",
            )
        return ComponentStatus(
            status="available",
            backend=provider,
            model=self.generative_model,
            detail="OpenAI 兼容接口可达，配置模型已加载",
        )

    def _detect_generative_provider(self) -> str:
        """Identify Ollama only from its version API; otherwise use a neutral label."""

        assert self.generative_base_url is not None
        try:
            response = self.get(
                f"{self.generative_base_url}/api/version",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            if isinstance(response.json().get("version"), str):
                return "Ollama"
        except (httpx.HTTPError, AttributeError, TypeError, ValueError):
            pass
        return "OpenAI 兼容"
