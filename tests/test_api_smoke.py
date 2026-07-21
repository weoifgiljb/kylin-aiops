import json
import subprocess

from tools.api_smoke import CurlClient


def test_curl_client_keeps_credentials_out_of_process_arguments(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["input"] = kwargs["input"]
        output = f'{json.dumps({"access_token": "jwt-secret"})}\n200'
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = CurlClient("https://aiops.example.edu", tmp_path / "cookies.txt")

    body, status = client.request(
        "POST",
        "/api/v1/auth/token",
        form={"username": "admin", "password": "password-secret"},
    )

    assert status == 200
    assert body["access_token"] == "jwt-secret"
    assert captured["args"] == ["curl", "--config", "-"]
    assert "password-secret" not in " ".join(captured["args"])
    assert "password-secret" in str(captured["input"])


def test_curl_client_accepts_expected_conflict_status(monkeypatch, tmp_path) -> None:
    problem = {"code": "VERSION_CONFLICT", "message": "版本冲突"}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            f"{json.dumps(problem, ensure_ascii=False)}\n409",
            "",
        ),
    )
    client = CurlClient("https://aiops.example.edu", tmp_path / "cookies.txt", "jwt-secret")

    body, status = client.request(
        "PATCH",
        "/api/v1/resources/nodes/node-01",
        json_body={"display_name": "冲突更新"},
        headers={"If-Match": '"1"'},
        expected={409},
    )

    assert status == 409
    assert body["code"] == "VERSION_CONFLICT"
