from datetime import UTC, datetime, timedelta

import httpx
from fastapi.testclient import TestClient
from kylin_aiops_api.main import app as default_app
from kylin_aiops_api.main import create_app
from kylin_aiops_diagnosis.mindie import MindIEOutput


def client() -> TestClient:
    return TestClient(create_app(seed_demo=True))


def auth(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev-{role}-token"}


def test_overview_and_incident_detail_are_evidence_backed() -> None:
    api = client()

    overview = api.get("/api/v1/overview", headers=auth("viewer"))
    detail = api.get("/api/v1/incidents/inc-db-pool", headers=auth("viewer"))

    assert overview.status_code == 200
    assert overview.json()["online_nodes"] == 3
    assert overview.json()["active_incidents"] == 1
    assert overview.json()["topology_groups"] == [
        {"id": "nginx:online", "service": "nginx", "status": "online", "count": 1},
        {"id": "java:online", "service": "java", "status": "online", "count": 1},
        {"id": "mysql:online", "service": "mysql", "status": "online", "count": 1},
    ]
    assert overview.json()["topology_group_edges"] == [
        {"source_service": "nginx", "target_service": "java", "count": 1, "confidence": 1.0},
        {"source_service": "java", "target_service": "mysql", "count": 1, "confidence": 1.0},
    ]
    assert detail.status_code == 200
    assert detail.json()["diagnosis"]["root_cause"] == "db-01"
    assert detail.json()["diagnosis"]["evidence_refs"] == ["ev-db-connections", "ev-db-log"]


def test_overview_without_demo_seed_contains_no_fabricated_data() -> None:
    api = TestClient(create_app(seed_demo=False))

    overview = api.get("/api/v1/overview", headers=auth("viewer")).json()

    assert overview == {
        "online_nodes": 0,
        "total_nodes": 0,
        "active_incidents": 0,
        "today_alerts": 0,
        "pending_actions": 0,
        "nodes": [],
        "topology": [],
        "topology_groups": [],
        "topology_group_edges": [],
    }


def test_default_application_starts_in_live_mode() -> None:
    overview = TestClient(default_app).get("/api/v1/overview", headers=auth("viewer")).json()

    assert overview["nodes"] == []
    assert overview["active_incidents"] == 0


def test_local_web_origin_receives_cors_response_header() -> None:
    response = TestClient(create_app()).get(
        "/healthz",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_untrusted_origin_does_not_receive_cors_response_header() -> None:
    response = TestClient(create_app()).get(
        "/healthz",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_system_status_reports_actual_downstream_backends(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_SERVICE_URL", "http://model-service:8001")
    monkeypatch.setenv("MINDIE_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("MINDIE_MODEL", "llama3.1:latest")
    monkeypatch.setenv("MINDIE_PROVIDER", "Ollama")

    def status_get(url: str, timeout: float) -> httpx.Response:
        request = httpx.Request("GET", url)
        if url.endswith("/healthz"):
            return httpx.Response(
                200,
                request=request,
                json={"status": "ok", "backend": "DeterministicFallback"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"data": [{"id": "llama3.1:latest"}]},
        )

    response = TestClient(
        create_app(seed_demo=False, status_get=status_get)
    ).get("/api/v1/system/status", headers=auth("viewer"))

    assert response.status_code == 200
    components = response.json()["components"]
    assert components["deterministic_diagnosis"]["status"] == "available"
    assert components["mindspore"] == {
        "status": "degraded",
        "backend": "DeterministicFallback",
        "detail": "模型服务在线，但正在使用确定性降级推理",
    }
    assert components["generative_ai"] == {
        "status": "available",
        "backend": "Ollama",
        "model": "llama3.1:latest",
        "detail": "OpenAI 兼容接口可达，配置模型已加载",
    }


def test_system_status_detects_ollama_when_provider_is_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_SERVICE_URL", raising=False)
    monkeypatch.setenv("MINDIE_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("MINDIE_MODEL", "llama3.1:latest")
    monkeypatch.delenv("MINDIE_PROVIDER", raising=False)

    def status_get(url: str, timeout: float) -> httpx.Response:
        request = httpx.Request("GET", url)
        if url.endswith("/api/version"):
            return httpx.Response(200, request=request, json={"version": "0.32.0"})
        return httpx.Response(
            200,
            request=request,
            json={"data": [{"id": "llama3.1:latest"}]},
        )

    response = TestClient(
        create_app(seed_demo=False, status_get=status_get)
    ).get("/api/v1/system/status", headers=auth("viewer"))

    assert response.json()["components"]["generative_ai"]["backend"] == "Ollama"


def test_missing_resource_uses_uniform_error_shape() -> None:
    response = client().get("/api/v1/incidents/missing", headers=auth("viewer"))

    assert response.status_code == 404
    assert set(response.json()) == {"code", "message", "request_id", "details"}
    assert response.json()["code"] == "INCIDENT_NOT_FOUND"


def test_validation_errors_use_uniform_error_shape() -> None:
    response = client().post(
        "/api/v1/chat/sessions/demo/messages",
        headers=auth("viewer"),
        json={"message": ""},
    )

    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "request_id", "details"}
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_chat_uses_a_live_incident_when_no_incident_id_is_selected() -> None:
    api = TestClient(create_app(seed_demo=False))
    api.post(
        "/internal/v1/alerts",
        json={
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "LiveAlert", "instance": "local-dev-01"},
                    "annotations": {"summary": "Live CPU alert"},
                    "startsAt": datetime.now(UTC).isoformat(),
                    "fingerprint": "fp-live-chat",
                }
            ],
        },
    )

    response = api.post(
        "/api/v1/chat/sessions/live/messages",
        headers=auth("viewer"),
        json={"message": "What happened?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Awaiting evidence correlation"


def test_chat_uses_configured_generative_model_with_question_and_incident_context() -> None:
    class FakeMindIE:
        def chat(self, message, context, available_evidence_ids):
            assert message == "数据库为什么连接失败？"
            assert context["incident"]["id"] == "inc-db-pool"
            assert available_evidence_ids == {"ev-db-connections", "ev-db-log"}
            return {
                "answer": "数据库连接数已接近上限，证据为 ev-db-connections。",
                "evidence_refs": ["ev-db-connections"],
            }

    response = TestClient(create_app(seed_demo=True, mindie_client=FakeMindIE())).post(
        "/api/v1/chat/sessions/ollama/messages",
        headers=auth("viewer"),
        json={"message": "数据库为什么连接失败？", "incident_id": "inc-db-pool"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "ollama",
        "answer": "数据库连接数已接近上限，证据为 ev-db-connections。",
        "source": "generative_ai",
        "evidence_refs": ["ev-db-connections"],
    }


def test_chat_falls_back_when_generative_model_is_unavailable() -> None:
    class UnavailableMindIE:
        def chat(self, message, context, available_evidence_ids):
            raise httpx.ConnectError("model offline")

    response = TestClient(
        create_app(seed_demo=True, mindie_client=UnavailableMindIE())
    ).post(
        "/api/v1/chat/sessions/fallback/messages",
        headers=auth("viewer"),
        json={"message": "发生了什么？", "incident_id": "inc-db-pool"},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "deterministic_fallback"
    assert response.json()["answer"] == "测试账号连接占满导致应用连接超时。"


def test_diagnosis_can_run_without_mindie() -> None:
    response = client().post(
        "/api/v1/incidents/inc-db-pool/diagnose", headers=auth("operator")
    )

    assert response.status_code == 200
    assert response.json()["source"] == "deterministic_fallback"
    assert response.json()["root_cause"] == "db-01"
    assert response.json()["evidence_refs"]


def test_diagnosis_uses_validated_mindie_output_when_configured() -> None:
    class FakeMindIE:
        def generate(self, context, available_evidence_ids):
            assert context["incident"]["id"] == "inc-db-pool"
            assert available_evidence_ids == {"ev-db-connections", "ev-db-log"}
            return MindIEOutput(
                summary="连接耗尽已由结构化证据确认",
                root_cause="db-01",
                severity="high",
                propagation_path=["db-01", "app-01", "web-01"],
                evidence_refs=["ev-db-connections", "ev-db-log"],
                recommended_steps=["审批后终止 ops_fault 连接"],
                action_candidates=["terminate_fault_db_sessions"],
                confidence=0.91,
            )

    response = TestClient(create_app(seed_demo=True, mindie_client=FakeMindIE())).post(
        "/api/v1/incidents/inc-db-pool/diagnose",
        headers=auth("operator"),
    )

    assert response.status_code == 200
    assert response.json()["source"] == "mindie"
    assert response.json()["confidence"] == 0.91


def test_only_operator_or_admin_can_approve_actions() -> None:
    api = client()
    preview = api.post(
        "/api/v1/incidents/inc-db-pool/actions/preview",
        headers=auth("operator"),
        json={
            "node_id": "db-01",
            "action_name": "terminate_fault_db_sessions",
            "parameters": {"db_user": "ops_fault"},
        },
    )
    action_id = preview.json()["id"]

    denied = api.post(f"/api/v1/action-requests/{action_id}/approve", headers=auth("viewer"))
    approved = api.post(
        f"/api/v1/action-requests/{action_id}/approve", headers=auth("operator")
    )

    assert denied.status_code == 403
    assert denied.json()["code"] == "INSUFFICIENT_ROLE"
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_preview_rejects_unsafe_experiment_parameters_before_signing() -> None:
    response = client().post(
        "/api/v1/incidents/inc-db-pool/actions/preview",
        headers=auth("operator"),
        json={
            "node_id": "db-01",
            "action_name": "remove_fault_file",
            "parameters": {"experiment_id": "../../etc", "filename": "disk-fill.bin"},
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "ACTION_PARAMETERS_INVALID"


def test_agent_only_receives_approved_actions_for_its_node() -> None:
    api = client()
    preview = api.post(
        "/api/v1/incidents/inc-db-pool/actions/preview",
        headers=auth("operator"),
        json={
            "node_id": "db-01",
            "action_name": "terminate_fault_db_sessions",
            "parameters": {"db_user": "ops_fault"},
        },
    ).json()
    empty = api.get("/agent/v1/actions/next?node_id=db-01", headers=auth("agent"))
    api.post(f"/api/v1/action-requests/{preview['id']}/approve", headers=auth("operator"))
    queued = api.get("/agent/v1/actions/next?node_id=db-01", headers=auth("agent"))

    assert empty.status_code == 204
    assert queued.status_code == 200
    assert queued.json()["action_name"] == "terminate_fault_db_sessions"
    assert queued.json()["signature"]


def test_evaluation_run_does_not_fabricate_a_missing_report(monkeypatch) -> None:
    monkeypatch.delenv("EVALUATION_REPORT_DIR", raising=False)

    response = client().get("/api/v1/evaluations/runs/demo-run", headers=auth("viewer"))

    assert response.status_code == 404
    assert response.json()["code"] == "EVALUATION_RUN_NOT_FOUND"


def test_evaluation_endpoint_loads_generated_report(tmp_path, monkeypatch) -> None:
    run_dir = tmp_path / "blind-run"
    run_dir.mkdir()
    (run_dir / "report.json").write_text(
        '{"trial_count":120,"metrics":{"detection_f1":0.9},"thresholds":{"detection_f1":0.85},"passed":true}',
        encoding="utf-8",
    )
    monkeypatch.setenv("EVALUATION_REPORT_DIR", str(tmp_path))

    response = client().get("/api/v1/evaluations/runs/blind-run", headers=auth("viewer"))

    assert response.status_code == 200
    assert response.json()["trial_count"] == 120
    assert response.json()["metrics"]["detection_f1"] == 0.9


def test_evaluation_runs_lists_only_generated_reports(tmp_path, monkeypatch) -> None:
    run_dir = tmp_path / "blind-run"
    run_dir.mkdir()
    (run_dir / "report.json").write_text(
        '{"trial_count":120,"metrics":{"detection_f1":0.9},'
        '"thresholds":{"detection_f1":0.85},"passed":true}',
        encoding="utf-8",
    )
    invalid_dir = tmp_path / "incomplete-run"
    invalid_dir.mkdir()
    (invalid_dir / "report.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("EVALUATION_REPORT_DIR", str(tmp_path))

    response = client().get("/api/v1/evaluations/runs", headers=auth("viewer"))

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == "blind-run"
    assert response.json()["items"][0]["metrics"]["detection_f1"] == 0.9


def test_agent_telemetry_refreshes_node_state() -> None:
    api = client()
    response = api.post(
        "/agent/v1/telemetry",
        headers=auth("agent"),
        json={
            "node_id": "app-01",
            "observed_at": datetime.now(UTC).isoformat(),
            "metrics": {"cpu_percent": 42.0, "memory_percent": 61.0},
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True
    assert api.get("/api/v1/overview", headers=auth("viewer")).json()["online_nodes"] == 3


def test_overview_exposes_latest_metrics_from_a_real_agent() -> None:
    api = TestClient(create_app(seed_demo=False))
    enrollment = api.post(
        "/agent/v1/enroll",
        headers=auth("agent"),
        json={
            "node_id": "local-dev-01",
            "hostname": "developer-pc",
            "architecture": "AMD64",
            "kylin_version": "Windows-dev",
        },
    ).json()
    observed_at = datetime.now(UTC).isoformat()

    response = api.post(
        "/agent/v1/telemetry",
        headers={"Authorization": f"Bearer {enrollment['enrollment_token']}"},
        json={
            "node_id": "local-dev-01",
            "observed_at": observed_at,
            "metrics": {"cpu_percent": 12.5, "memory_percent": 34.5},
        },
    )
    overview = api.get("/api/v1/overview", headers=auth("viewer")).json()

    assert response.status_code == 202
    assert overview["nodes"] == [
        {
            "id": "local-dev-01",
            "hostname": "developer-pc",
            "architecture": "AMD64",
            "kylin_version": "Windows-dev",
            "status": "online",
            "last_seen_at": observed_at,
            "metrics": {"cpu_percent": 12.5, "memory_percent": 34.5},
        }
    ]
    assert overview["topology"] == []


def test_alert_webhook_deduplicates_and_recovers_incident() -> None:
    api = client()
    firing = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "JavaServiceDown",
                    "instance": "app-01",
                    "severity": "critical",
                },
                "annotations": {"summary": "Java demo service is down"},
                "startsAt": "2026-07-19T14:30:00Z",
                "fingerprint": "fp-java-down",
            }
        ],
    }

    first = api.post("/internal/v1/alerts", json=firing)
    second = api.post("/internal/v1/alerts", json=firing)
    assert first.status_code == 202
    assert second.json()["created"] == 0

    firing["status"] = "resolved"
    firing["alerts"][0]["status"] = "resolved"
    resolved = api.post("/internal/v1/alerts", json=firing)
    incident_id = first.json()["incident_ids"][0]
    detail = api.get(f"/api/v1/incidents/{incident_id}", headers=auth("viewer"))

    assert resolved.status_code == 202
    assert detail.json()["status"] == "resolved"


def test_today_alert_count_uses_received_incidents_instead_of_a_constant() -> None:
    api = TestClient(create_app(seed_demo=False))
    now = datetime.now(UTC)
    api.post(
        "/internal/v1/alerts",
        json={
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "LiveAlert", "instance": "local-dev-01"},
                    "startsAt": now.isoformat(),
                    "fingerprint": "fp-live-alert",
                }
            ],
        },
    )

    overview = api.get("/api/v1/overview", headers=auth("viewer")).json()

    assert overview["today_alerts"] == 1


def test_node_is_offline_when_telemetry_is_older_than_30_seconds() -> None:
    api = client()
    api.post(
        "/agent/v1/enroll",
        headers=auth("agent"),
        json={
            "node_id": "stale-01",
            "hostname": "stale-01",
            "architecture": "aarch64",
            "kylin_version": "V10",
        },
    )
    api.post(
        "/agent/v1/telemetry",
        headers=auth("agent"),
        json={
            "node_id": "stale-01",
            "observed_at": (datetime.now(UTC) - timedelta(seconds=31)).isoformat(),
            "metrics": {"cpu_percent": 1.0},
        },
    )

    overview = api.get("/api/v1/overview", headers=auth("viewer")).json()

    stale_node = next(node for node in overview["nodes"] if node["id"] == "stale-01")
    assert stale_node["status"] == "offline"


def test_enrolled_agent_token_is_bound_to_one_node() -> None:
    api = client()
    enrollment = api.post(
        "/agent/v1/enroll",
        headers=auth("agent"),
        json={
            "node_id": "bound-01",
            "hostname": "bound-01",
            "architecture": "aarch64",
            "kylin_version": "V10",
        },
    ).json()

    response = api.post(
        "/agent/v1/telemetry",
        headers={"Authorization": f"Bearer {enrollment['enrollment_token']}"},
        json={
            "node_id": "app-01",
            "observed_at": datetime.now(UTC).isoformat(),
            "metrics": {"cpu_percent": 1.0},
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AGENT_TARGET_MISMATCH"


def test_admin_can_read_action_audit_trail() -> None:
    api = client()
    preview = api.post(
        "/api/v1/incidents/inc-db-pool/actions/preview",
        headers=auth("operator"),
        json={
            "node_id": "db-01",
            "action_name": "terminate_fault_db_sessions",
            "parameters": {"db_user": "ops_fault"},
        },
    ).json()
    api.post(f"/api/v1/action-requests/{preview['id']}/approve", headers=auth("operator"))

    response = api.get("/api/v1/audit-logs", headers=auth("admin"))

    assert response.status_code == 200
    assert [item["action"] for item in response.json()["items"]][-2:] == [
        "action.previewed",
        "action.approved",
    ]
