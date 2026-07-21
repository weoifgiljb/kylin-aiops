import httpx
import pytest
from kylin_aiops_diagnosis.mindie import (
    MindIEChatOutput,
    MindIEClient,
    MindIEOutput,
    validate_chat_output,
    validate_mindie_output,
)


def test_mindie_output_must_only_reference_available_evidence() -> None:
    output = MindIEOutput(
        summary="数据库连接耗尽",
        root_cause="db-01",
        severity="high",
        propagation_path=["db-01", "app-01"],
        evidence_refs=["ev-invented"],
        recommended_steps=["检查连接"],
        action_candidates=[],
        confidence=0.8,
    )

    with pytest.raises(ValueError, match="unknown Evidence ID"):
        validate_mindie_output(output, available_evidence_ids={"ev-real"})


def test_mindie_output_with_real_evidence_is_accepted() -> None:
    output = MindIEOutput(
        summary="数据库连接耗尽",
        root_cause="db-01",
        severity="high",
        propagation_path=["db-01", "app-01"],
        evidence_refs=["ev-real"],
        recommended_steps=["检查连接"],
        action_candidates=["terminate_fault_db_sessions"],
        confidence=0.8,
    )

    assert validate_mindie_output(output, {"ev-real"}) is output


def test_chat_sends_question_and_only_accepts_known_evidence(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, json, timeout):
        captured.update({"url": url, "json": json, "timeout": timeout})
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"answer":"由 ev-real 可确认连接耗尽。",'
                                '"evidence_refs":["ev-real"]}'
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = MindIEClient("http://127.0.0.1:11434", "llama3.1:latest")

    result = client.chat(
        "为什么失败？",
        {"incident": {"id": "inc-live"}},
        available_evidence_ids={"ev-real"},
    )

    assert result.answer == "由 ev-real 可确认连接耗尽。"
    assert result.evidence_refs == ["ev-real"]
    assert captured["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert captured["json"]["messages"][-1]["content"].startswith("问题：为什么失败？")


def test_chat_rejects_unknown_evidence_reference() -> None:
    output = MindIEChatOutput(answer="由 ev-invented 可确认故障。", evidence_refs=["ev-invented"])

    with pytest.raises(ValueError, match="unknown Evidence ID"):
        validate_chat_output(output, {"ev-real"})
