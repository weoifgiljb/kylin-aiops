# 开发与代码注释规范

## 真实数据原则

- 运行状态、指标、事件、评测结果必须来自 API 或明确标注的离线报告，禁止在 React 组件中写死“在线”“可用”、固定数量或固定准确率。
- 演示数据只能由显式的 `DEMO_SEED=true` 开启；默认开发、测试部署和生产部署均使用 `false`。
- 后端依赖不可用时返回 `degraded`、`unconfigured` 或 `unreachable`，不得用部署说明冒充当前运行状态。
- 新增接口先修改 FastAPI Schema，再运行 `tools/export_openapi.py`；OpenAPI 是前后端契约的唯一事实来源。

## 注释与文档字符串

- 每个 Python 生产模块必须包含模块级 docstring，说明模块职责和边界。
- 公共类、公共函数以及有副作用的关键方法必须说明输入、输出、副作用或拒绝条件。
- TypeScript 导出的非直观类型、工具函数和共享组件使用 TSDoc 说明数据来源与约束。
- 安全边界必须解释“为什么”：审批、签名、验签、幂等、白名单参数、`shell=False`、路径和目标匹配逻辑不得无说明。
- 行内注释用于解释原因、不变量和降级策略，不重复代码表面含义；能通过清晰命名表达的简单赋值不添加噪声注释。
- 修改逻辑时同步维护注释。与代码不一致的注释按缺陷处理。

## 结构与测试

- 禁止把完整页面压成单行 JSX；状态获取、展示映射和交互处理应使用有名称的变量或组件。
- 功能和缺陷修复遵循红—绿—重构：先添加会因缺失行为而失败的测试，再实现最小修复。
- 外部服务测试使用注入的 HTTP transport/probe，不访问开发者个人环境。
- 提交前运行：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
cd apps/web
pnpm test
pnpm lint
pnpm build
```
