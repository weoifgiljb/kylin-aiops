# API 管理与 curl 手册

以下示例以 Bash 为例。密码和 token 只从环境变量读取，不把真实秘密写入脚本或仓库。推荐日常验收直接运行 `tools/api_smoke.py`，它会通过 curl 配置标准输入传递秘密，并在结束后删除临时 Cookie 文件。

## 登录与当前用户

```bash
export AIOPS_BASE_URL='https://aiops.example.edu'
export AIOPS_USERNAME='admin'
export AIOPS_PASSWORD='从密码管理器读取的密码'
COOKIE_JAR="$(mktemp)"

LOGIN_JSON="$(curl --silent --show-error --fail \
  --cookie-jar "$COOKIE_JAR" \
  --data-urlencode "username=$AIOPS_USERNAME" \
  --data-urlencode "password=$AIOPS_PASSWORD" \
  "$AIOPS_BASE_URL/api/v1/auth/token")"
export AIOPS_ACCESS_TOKEN="$(printf '%s' "$LOGIN_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"

curl --silent --show-error --fail \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" \
  "$AIOPS_BASE_URL/api/v1/auth/me"
```

access token 有效期为 30 分钟。浏览器使用的 refresh token 只存在 `HttpOnly + Secure + SameSite=Strict` Cookie；curl 示例通过临时 Cookie 文件保存它。退出并清理：

```bash
curl --silent --show-error --fail -X POST \
  --cookie "$COOKIE_JAR" \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" \
  "$AIOPS_BASE_URL/api/v1/auth/logout"
rm -f "$COOKIE_JAR"
unset AIOPS_ACCESS_TOKEN AIOPS_PASSWORD LOGIN_JSON
```

## 资源 CRUD

创建节点：

```bash
curl --silent --show-error --fail -X POST \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"id":"test-node-01","display_name":"测试节点一","description":"隔离测试资源","tags":["school-test"]}' \
  "$AIOPS_BASE_URL/api/v1/resources/nodes"
```

列表统一使用 `items / total / page / page_size`，每页最大 100：

```bash
curl --silent --show-error --fail \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" \
  "$AIOPS_BASE_URL/api/v1/resources/nodes?page=1&page_size=20&include_archived=true"
```

更新、归档和恢复必须携带当前 `version`。下面假设当前版本是 1：

```bash
curl --silent --show-error --fail -X PATCH \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" \
  -H 'If-Match: "1"' -H 'Content-Type: application/json' \
  -d '{"display_name":"测试节点一（更新）","enabled":false}' \
  "$AIOPS_BASE_URL/api/v1/resources/nodes/test-node-01"

curl --silent --show-error --fail -X DELETE \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" -H 'If-Match: "2"' \
  "$AIOPS_BASE_URL/api/v1/resources/nodes/test-node-01"

curl --silent --show-error --fail -X POST \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" -H 'If-Match: "3"' \
  "$AIOPS_BASE_URL/api/v1/resources/nodes/test-node-01/restore"
```

服务使用 `/api/v1/resources/services`，人工依赖使用 `/api/v1/resources/dependencies`，版本和软删除规则与节点一致。过期版本返回 HTTP 409 和 `VERSION_CONFLICT`，客户端应保留未提交的表单内容。

## 事件处置

```bash
curl --silent --show-error --fail -X POST \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"人工巡检异常","fault_type":"manual_check","severity":"medium","handling_notes":"等待现场复核"}' \
  "$AIOPS_BASE_URL/api/v1/incidents"

curl --silent --show-error --fail -X PATCH \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" \
  -H 'If-Match: "1"' -H 'Content-Type: application/json' \
  -d '{"status":"resolved","handling_notes":"已现场确认并恢复"}' \
  "$AIOPS_BASE_URL/api/v1/incidents/事件编号"
```

人工事件允许 operator/admin 修改业务字段；自动告警事件的原始标题、故障类型、根节点、时间和证据不可修改。事件只有在 `resolved` 后才能归档，自动事件仅 admin 可归档。

## 用户与审计

用户管理仅限 admin。创建用户时密码放在请求体，并通过安全终端环境执行；重置密码会撤销该用户全部会话。

```bash
curl --silent --show-error --fail \
  -H "Authorization: Bearer $AIOPS_ACCESS_TOKEN" \
  "$AIOPS_BASE_URL/api/v1/audit-logs?action=node.updated&target=node%3Atest-node-01&page=1&page_size=20"
```

审计日志只读且不可通过公共 API 修改。可按操作者、动作、目标和时间范围筛选。

## 自动冒烟

默认模式只读取 HTTPS 健康状态、登录用户和分页接口：

```bash
export AIOPS_BASE_URL='https://aiops.example.edu'
export AIOPS_USERNAME='admin'
export AIOPS_PASSWORD='从密码管理器读取的密码'
python tools/api_smoke.py
```

CRUD 模式会创建、更新、制造版本冲突、软删除、恢复、再次归档并检查审计。只能对隔离测试库运行：

```bash
export AIOPS_SMOKE_ALLOW_CRUD='isolated-test'
python tools/api_smoke.py --crud
```

脚本不会输出密码、refresh token 或完整 JWT；无论成功失败都会删除临时 Cookie 文件。
