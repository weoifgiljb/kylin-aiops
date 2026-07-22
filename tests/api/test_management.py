from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from kylin_aiops_api.auth import seed_admin
from kylin_aiops_api.database import Base
from kylin_aiops_api.main import create_app
from sqlalchemy import create_engine


def management_client(tmp_path: Path) -> TestClient:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'management.db'}"
    Base.metadata.create_all(create_engine(database_url))
    seed_admin(database_url, "admin", "correct-horse-battery-staple", "系统管理员")
    return TestClient(
        create_app(
            database_url=database_url,
            jwt_secret="test-jwt-secret-that-is-at-least-32-bytes",
            secure_cookies=False,
        )
    )


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_real_account_login_and_refresh_session(tmp_path: Path) -> None:
    client = management_client(tmp_path)

    token = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token.json()['access_token']}"},
    )
    refreshed = client.post("/api/v1/auth/refresh")

    assert token.status_code == 200
    assert token.json()["token_type"] == "bearer"
    assert "refresh_token" in token.cookies
    assert me.json()["role"] == "admin"
    assert refreshed.status_code == 200


def test_database_mode_shares_one_session_factory(tmp_path: Path) -> None:
    client = management_client(tmp_path)

    assert client.app.state.auth_manager.sessions is client.app.state.database.sessions
    assert client.app.state.store.sessions is client.app.state.database.sessions
    assert not hasattr(client.app.state.store, "engine")


def test_human_jwt_skips_agent_credential_lookup(tmp_path: Path, monkeypatch) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")

    def reject_agent_lookup(_: str) -> None:
        pytest.fail("人类 JWT 不应查询 Agent 凭证表")

    monkeypatch.setattr(client.app.state.auth_manager, "current_agent", reject_agent_lookup)

    response = client.get("/api/v1/auth/me", headers=admin)

    assert response.status_code == 200


def test_admin_manages_users_and_operator_cannot_manage_resources(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")

    created = client.post(
        "/api/v1/admin/users",
        headers=admin,
        json={
            "username": "operator",
            "display_name": "值班人员",
            "password": "operator-password-123",
            "role": "operator",
        },
    )
    operator = login(client, "operator", "operator-password-123")
    denied = client.post(
        "/api/v1/resources/nodes",
        headers=operator,
        json={"id": "node-01", "display_name": "节点一"},
    )

    assert created.status_code == 201
    assert "password_hash" not in created.json()
    assert denied.status_code == 403
    assert denied.json()["code"] == "INSUFFICIENT_ROLE"


def test_password_reset_revokes_sessions_and_last_admin_is_protected(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")
    created = client.post(
        "/api/v1/admin/users",
        headers=admin,
        json={
            "username": "viewer",
            "display_name": "只读用户",
            "password": "viewer-password-123",
            "role": "viewer",
        },
    ).json()
    viewer = login(client, "viewer", "viewer-password-123")

    reset = client.post(
        f"/api/v1/admin/users/{created['id']}/reset-password",
        headers={**admin, "If-Match": '"1"'},
        json={"password": "new-viewer-password-456"},
    )
    revoked = client.get("/api/v1/auth/me", headers=viewer)
    admin_id = client.get("/api/v1/auth/me", headers=admin).json()["id"]
    last_admin = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        headers={**admin, "If-Match": '"1"'},
        json={"role": "operator"},
    )

    assert reset.status_code == 200
    assert revoked.status_code == 401
    assert login(client, "viewer", "new-viewer-password-456")["Authorization"]
    assert last_admin.status_code == 409
    assert last_admin.json()["code"] == "LAST_ADMIN_REQUIRED"


def test_login_rate_limit_uses_uniform_429_problem(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    for _ in range(5):
        rejected = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "wrong-password"},
        )
        assert rejected.status_code == 401

    limited = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "wrong-password"},
    )

    assert limited.status_code == 429
    assert limited.json()["code"] == "LOGIN_RATE_LIMITED"
    assert limited.json()["request_id"]


def test_resource_crud_uses_soft_delete_and_optimistic_version(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")
    created = client.post(
        "/api/v1/resources/nodes",
        headers=admin,
        json={
            "id": "node-01",
            "display_name": "节点一",
            "description": "校内测试节点",
            "tags": ["教学楼"],
        },
    )

    updated = client.patch(
        "/api/v1/resources/nodes/node-01",
        headers={**admin, "If-Match": '"1"'},
        json={"display_name": "节点一（更新）"},
    )
    conflict = client.patch(
        "/api/v1/resources/nodes/node-01",
        headers={**admin, "If-Match": '"1"'},
        json={"display_name": "过期更新"},
    )
    archived = client.delete(
        "/api/v1/resources/nodes/node-01",
        headers={**admin, "If-Match": '"2"'},
    )
    visible = client.get("/api/v1/resources/nodes", headers=admin)
    restored = client.post(
        "/api/v1/resources/nodes/node-01/restore",
        headers={**admin, "If-Match": '"3"'},
    )

    assert created.status_code == 201
    assert updated.json()["version"] == 2
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "VERSION_CONFLICT"
    assert archived.status_code == 200
    assert visible.json()["items"] == []
    assert restored.json()["archived_at"] is None


def test_manual_dependency_can_be_updated_with_version_guard(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")
    client.post(
        "/api/v1/resources/nodes",
        headers=admin,
        json={"id": "node-01", "display_name": "节点一"},
    )
    for service_id in ("web", "app", "db"):
        response = client.post(
            "/api/v1/resources/services",
            headers=admin,
            json={
                "id": service_id,
                "node_id": "node-01",
                "name": service_id,
                "service_type": "test",
            },
        )
        assert response.status_code == 201
    dependency = client.post(
        "/api/v1/resources/dependencies",
        headers=admin,
        json={"source_service_id": "web", "target_service_id": "app"},
    ).json()

    updated = client.patch(
        f"/api/v1/resources/dependencies/{dependency['id']}",
        headers={**admin, "If-Match": '"1"'},
        json={"target_service_id": "db"},
    )
    stale = client.patch(
        f"/api/v1/resources/dependencies/{dependency['id']}",
        headers={**admin, "If-Match": '"1"'},
        json={"target_service_id": "app"},
    )
    self_reference = client.patch(
        f"/api/v1/resources/dependencies/{dependency['id']}",
        headers={**admin, "If-Match": '"2"'},
        json={"target_service_id": "web"},
    )

    assert updated.status_code == 200
    assert updated.json()["target_service_id"] == "db"
    assert stale.status_code == 409
    assert self_reference.status_code == 422


def test_operator_manages_manual_incident_but_cannot_rewrite_alert(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")
    client.post(
        "/api/v1/admin/users",
        headers=admin,
        json={
            "username": "operator",
            "display_name": "值班人员",
            "password": "operator-password-123",
            "role": "operator",
        },
    )
    operator = login(client, "operator", "operator-password-123")

    manual = client.post(
        "/api/v1/incidents",
        headers=operator,
        json={
            "title": "人工巡检异常",
            "fault_type": "manual_check",
            "severity": "medium",
        },
    )
    resolved = client.patch(
        f"/api/v1/incidents/{manual.json()['id']}",
        headers={**operator, "If-Match": '"1"'},
        json={"status": "resolved", "handling_notes": "已现场确认"},
    )
    archived = client.delete(
        f"/api/v1/incidents/{manual.json()['id']}",
        headers={**operator, "If-Match": '"2"'},
    )
    client.post(
        "/internal/v1/alerts",
        json={
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "CpuHigh", "instance": "node-01"},
                    "annotations": {"summary": "CPU 使用率过高"},
                    "startsAt": "2026-07-21T08:00:00Z",
                    "fingerprint": "cpu-high-01",
                }
            ],
        },
    )
    alert_update = client.patch(
        "/api/v1/incidents/inc-cpu-high-01",
        headers={**operator, "If-Match": '"1"'},
        json={"title": "试图覆盖原始告警"},
    )

    assert manual.status_code == 201
    assert resolved.json()["status"] == "resolved"
    assert archived.status_code == 200
    assert alert_update.status_code == 422
    assert alert_update.json()["code"] == "ALERT_FIELDS_IMMUTABLE"


def test_database_incident_is_visible_to_overview_and_diagnosis(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")

    created = client.post(
        "/api/v1/incidents",
        headers=admin,
        json={
            "title": "数据库状态源回归",
            "fault_type": "review",
            "severity": "high",
        },
    )
    incident_id = created.json()["id"]

    overview = client.get("/api/v1/overview", headers=admin)
    diagnosis = client.post(f"/api/v1/incidents/{incident_id}/diagnose", headers=admin)

    assert created.status_code == 201
    assert overview.json()["active_incidents"] == 1
    assert diagnosis.status_code == 200
    assert diagnosis.json()["source"] == "pending"


def test_database_chat_uses_latest_incident_when_id_is_omitted(tmp_path: Path) -> None:
    client = management_client(tmp_path)
    admin = login(client, "admin", "correct-horse-battery-staple")
    client.post(
        "/api/v1/incidents",
        headers=admin,
        json={
            "title": "数据库问答回归",
            "fault_type": "review",
            "severity": "medium",
        },
    )

    response = client.post(
        "/api/v1/chat/sessions/default/messages",
        headers=admin,
        json={"message": "当前发生了什么？"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "等待诊断"


def test_agent_credential_survives_api_restart(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agents.db'}"
    Base.metadata.create_all(create_engine(database_url))
    seed_admin(database_url, "admin", "correct-horse-battery-staple", "系统管理员")
    bootstrap = "agent-bootstrap-secret-at-least-32-bytes"
    monkeypatch.setenv("AGENT_BOOTSTRAP_TOKEN", bootstrap)
    first = TestClient(
        create_app(
            database_url=database_url,
            jwt_secret="test-jwt-secret-that-is-at-least-32-bytes",
            secure_cookies=False,
        )
    )
    enrollment = first.post(
        "/agent/v1/enroll",
        headers={"Authorization": f"Bearer {bootstrap}"},
        json={
            "node_id": "persistent-agent",
            "hostname": "persistent-agent",
            "architecture": "aarch64",
            "kylin_version": "V10",
        },
    )

    restarted = TestClient(
        create_app(
            database_url=database_url,
            jwt_secret="test-jwt-secret-that-is-at-least-32-bytes",
            secure_cookies=False,
        )
    )
    telemetry = restarted.post(
        "/agent/v1/telemetry",
        headers={"Authorization": f"Bearer {enrollment.json()['enrollment_token']}"},
        json={
            "node_id": "persistent-agent",
            "observed_at": "2026-07-21T08:00:00Z",
            "metrics": {"cpu_percent": 12.0},
        },
    )

    assert enrollment.status_code == 200
    assert telemetry.status_code == 202


def test_school_test_mode_rejects_missing_shared_dependencies(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "school_test")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("AGENT_BOOTSTRAP_TOKEN", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_app()
