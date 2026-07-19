# OpenAPI TypeScript 客户端

先在仓库根目录运行 `python tools/export_openapi.py`，再在本目录执行 `pnpm install && pnpm generate`。`services/ops-api/openapi.json` 是前后端契约的唯一来源；禁止手工修改生成的 `src/schema.ts`。
