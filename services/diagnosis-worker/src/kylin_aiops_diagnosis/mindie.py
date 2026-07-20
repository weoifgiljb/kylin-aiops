"""OpenAI-compatible explanation client with evidence and action allowlist validation."""

import json
from typing import Literal

import httpx
from pydantic import BaseModel, Field

ALLOWED_ACTIONS = {
    "restart_demo_service",
    "reload_nginx",
    "stop_fault_stressor",
    "remove_fault_file",
    "clear_fault_netem",
    "terminate_fault_db_sessions",
}


class MindIEOutput(BaseModel):
    summary: str = Field(min_length=1)
    root_cause: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "critical"]
    propagation_path: list[str]
    evidence_refs: list[str] = Field(min_length=1)
    recommended_steps: list[str] = Field(min_length=1)
    action_candidates: list[str]
    confidence: float = Field(ge=0, le=1)


def validate_mindie_output(
    output: MindIEOutput, available_evidence_ids: set[str]
) -> MindIEOutput:
    """Reject hallucinated evidence references and non-allowlisted action names."""

    unknown = set(output.evidence_refs) - available_evidence_ids
    if unknown:
        raise ValueError(f"MindIE returned unknown Evidence ID: {sorted(unknown)}")
    invalid_actions = set(output.action_candidates) - ALLOWED_ACTIONS
    if invalid_actions:
        raise ValueError(f"MindIE returned non-allowlisted actions: {sorted(invalid_actions)}")
    return output


class MindIEClient:
    """OpenAI-compatible MindIE adapter with strict JSON output validation."""

    def __init__(self, base_url: str, model: str, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, context: dict, available_evidence_ids: set[str]) -> MindIEOutput:
        """Generate and validate one structured explanation from incident context."""

        response = httpx.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是运维诊断说明器。只能引用输入中的 Evidence ID，"
                            "不能执行动作，必须输出约定 JSON 字段。"
                        ),
                    },
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        output = MindIEOutput.model_validate_json(content)
        return validate_mindie_output(output, available_evidence_ids)
