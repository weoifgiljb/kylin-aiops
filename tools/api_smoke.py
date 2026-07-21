"""使用系统 curl 验证校内测试环境的认证、分页、并发保护与审计链路。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


class SmokeFailure(RuntimeError):
    """表示冒烟检查未满足接口契约，不携带认证秘密。"""


def _config_value(value: str) -> str:
    """按 curl 配置文件语法转义值，避免秘密出现在进程命令行。"""

    return json.dumps(value, ensure_ascii=False)


class CurlClient:
    """通过标准输入向系统 curl 传递配置，并只返回解析后的响应。"""

    def __init__(self, base_url: str, cookie_file: Path, access_token: str | None = None):
        self.base_url = base_url.rstrip("/") + "/"
        self.cookie_file = cookie_file
        self.access_token = access_token

    def request(
        self,
        method: str,
        path: str,
        *,
        form: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        expected: set[int] | None = None,
    ) -> tuple[Any, int]:
        accepted = expected or {200, 201, 202, 204}
        lines = [
            "silent",
            "show-error",
            f"url = {_config_value(urljoin(self.base_url, path.lstrip('/')))}",
            f"request = {_config_value(method)}",
            f"cookie = {_config_value(str(self.cookie_file))}",
            f"cookie-jar = {_config_value(str(self.cookie_file))}",
            'write-out = "\\n%{http_code}"',
        ]
        if self.access_token:
            lines.append(f"header = {_config_value(f'Authorization: Bearer {self.access_token}')}")
        for name, value in (headers or {}).items():
            lines.append(f"header = {_config_value(f'{name}: {value}')}")
        if form is not None:
            lines.append('header = "Content-Type: application/x-www-form-urlencoded"')
            for name, value in form.items():
                lines.append(f"data-urlencode = {_config_value(f'{name}={value}')}")
        if json_body is not None:
            lines.append('header = "Content-Type: application/json"')
            payload = json.dumps(json_body, ensure_ascii=False, separators=(",", ":"))
            lines.append(f"data = {_config_value(payload)}")

        try:
            completed = subprocess.run(
                ["curl", "--config", "-"],
                input="\n".join(lines) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError as exc:
            raise SmokeFailure("未找到系统 curl，请先安装 curl 并加入 PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise SmokeFailure(f"请求超时：{method} {path}") from exc

        if completed.returncode != 0:
            detail = completed.stderr.strip() or "curl 执行失败"
            raise SmokeFailure(f"{method} {path}：{detail}")
        raw_body, separator, raw_status = completed.stdout.rpartition("\n")
        if not separator or not raw_status.isdigit():
            raise SmokeFailure(f"{method} {path}：无法读取 HTTP 状态码")
        status = int(raw_status)
        if status not in accepted:
            code = "UNKNOWN_ERROR"
            try:
                code = json.loads(raw_body).get("code", code)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise SmokeFailure(f"{method} {path} 返回 {status}（{code}）")
        if status == 204 or not raw_body:
            return None, status
        try:
            return json.loads(raw_body), status
        except json.JSONDecodeError as exc:
            raise SmokeFailure(f"{method} {path}：响应不是 JSON") from exc


def _read_only_checks(client: CurlClient, username: str, password: str) -> dict[str, Any]:
    health, _ = client.request("GET", "/healthz")
    if health.get("status") != "ok":
        raise SmokeFailure("健康检查未返回 ok")
    token, _ = client.request(
        "POST",
        "/api/v1/auth/token",
        form={"username": username, "password": password},
    )
    client.access_token = token["access_token"]
    me, _ = client.request("GET", "/api/v1/auth/me")
    incidents, _ = client.request("GET", "/api/v1/incidents?page=1&page_size=1")
    if not {"items", "total", "page", "page_size"}.issubset(incidents):
        raise SmokeFailure("事件分页响应不符合 items/total/page/page_size 契约")
    return me


def _crud_checks(client: CurlClient) -> None:
    suffix = f"{int(time.time())}-{os.getpid()}"
    node_id = f"smoke-{suffix}"
    created, _ = client.request(
        "POST",
        "/api/v1/resources/nodes",
        json_body={
            "id": node_id,
            "display_name": "curl 冒烟节点",
            "description": "仅用于隔离测试环境的 CRUD 验证",
            "tags": ["smoke"],
        },
    )
    updated, _ = client.request(
        "PATCH",
        f"/api/v1/resources/nodes/{node_id}",
        headers={"If-Match": f'"{created["version"]}"'},
        json_body={"display_name": "curl 冒烟节点（已更新）"},
    )
    conflict, _ = client.request(
        "PATCH",
        f"/api/v1/resources/nodes/{node_id}",
        headers={"If-Match": f'"{created["version"]}"'},
        json_body={"display_name": "过期写入"},
        expected={409},
    )
    if conflict.get("code") != "VERSION_CONFLICT":
        raise SmokeFailure("过期版本没有返回 VERSION_CONFLICT")
    archived, _ = client.request(
        "DELETE",
        f"/api/v1/resources/nodes/{node_id}",
        headers={"If-Match": f'"{updated["version"]}"'},
    )
    restored, _ = client.request(
        "POST",
        f"/api/v1/resources/nodes/{node_id}/restore",
        headers={"If-Match": f'"{archived["version"]}"'},
    )
    client.request(
        "DELETE",
        f"/api/v1/resources/nodes/{node_id}",
        headers={"If-Match": f'"{restored["version"]}"'},
    )
    audit, _ = client.request(
        "GET",
        f"/api/v1/audit-logs?target=node%3A{node_id}&page_size=100",
    )
    actions = {item["action"] for item in audit["items"]}
    required = {"node.created", "node.updated", "node.archived", "node.restored"}
    if not required.issubset(actions):
        raise SmokeFailure("审计日志没有覆盖 CRUD 写操作")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="使用系统 curl 验证校内测试管理 API")
    parser.add_argument("--base-url", default=os.getenv("AIOPS_BASE_URL", ""))
    parser.add_argument("--crud", action="store_true", help="在隔离测试库验证写操作")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.base_url:
        print("请通过 --base-url 或 AIOPS_BASE_URL 指定地址", file=sys.stderr)
        return 2
    if urlparse(args.base_url).scheme != "https":
        print("冒烟检查只接受 HTTPS 地址", file=sys.stderr)
        return 2
    username = os.getenv("AIOPS_USERNAME")
    password = os.getenv("AIOPS_PASSWORD")
    if not username or not password:
        print("请设置 AIOPS_USERNAME 和 AIOPS_PASSWORD", file=sys.stderr)
        return 2
    if args.crud and os.getenv("AIOPS_SMOKE_ALLOW_CRUD") != "isolated-test":
        print("--crud 仅在 AIOPS_SMOKE_ALLOW_CRUD=isolated-test 时运行", file=sys.stderr)
        return 2

    cookie_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="kylin-aiops-cookies-", delete=False) as handle:
            cookie_path = Path(handle.name)
        client = CurlClient(args.base_url, cookie_path)
        me = _read_only_checks(client, username, password)
        if args.crud:
            _crud_checks(client)
        client.request("POST", "/api/v1/auth/logout")
        mode = "只读 + CRUD" if args.crud else "只读"
        print(f"冒烟检查通过：{mode}，账号角色 {me['role']}")
        return 0
    except SmokeFailure as exc:
        print(f"冒烟检查失败：{exc}", file=sys.stderr)
        return 1
    finally:
        if cookie_path is not None:
            cookie_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
