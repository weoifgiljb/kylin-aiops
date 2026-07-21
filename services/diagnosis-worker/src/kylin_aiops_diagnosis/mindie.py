"""兼容 OpenAI 协议的解释客户端，并严格校验引用证据和动作白名单。"""

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


class MindIEChatOutput(BaseModel):
    answer: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


def validate_mindie_output(
    output: MindIEOutput, available_evidence_ids: set[str]
) -> MindIEOutput:
    """拒绝模型虚构的 Evidence ID 和不在白名单内的动作名称。"""

    unknown = set(output.evidence_refs) - available_evidence_ids
    if unknown:
        raise ValueError(f"MindIE returned unknown Evidence ID: {sorted(unknown)}")
    invalid_actions = set(output.action_candidates) - ALLOWED_ACTIONS
    if invalid_actions:
        raise ValueError(f"MindIE returned non-allowlisted actions: {sorted(invalid_actions)}")
    return output


def validate_chat_output(
    output: MindIEChatOutput, available_evidence_ids: set[str]
) -> MindIEChatOutput:
    """问答可以在无证据时明确说明未知，但不能引用不存在的证据。"""

    unknown = set(output.evidence_refs) - available_evidence_ids
    if unknown:
        raise ValueError(f"MindIE returned unknown Evidence ID: {sorted(unknown)}")
    return output


class MindIEClient:
    """通过 OpenAI 兼容接口访问 MindIE 或 Ollama，并校验结构化输出。"""

    def __init__(self, base_url: str, model: str, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, context: dict, available_evidence_ids: set[str]) -> MindIEOutput:
        """根据事件上下文生成并校验一份结构化诊断解释。"""

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

    def chat(
        self,
        message: str,
        context: dict,
        available_evidence_ids: set[str],
    ) -> MindIEChatOutput:
        """回答运维问题；模型只能引用上下文中实际存在的 Evidence ID。"""

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
                            "你是麒麟系统运维问答助手。必须只依据输入的事件、诊断和证据回答，"
                            "只能引用输入中真实存在的 Evidence ID。若证据不足应明确说明，"
                            "不得编造证据或声称已经执行操作。输出 JSON，字段为 answer "
                            "和 evidence_refs。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"问题：{message}\n"
                            f"上下文：{json.dumps(context, ensure_ascii=False)}"
                        ),
                    },
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        output = MindIEChatOutput.model_validate_json(content)
        return validate_chat_output(output, available_evidence_ids)
