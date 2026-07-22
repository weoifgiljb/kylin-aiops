"""导出作为前后端唯一契约来源的 FastAPI OpenAPI 文档。"""

import json
import tempfile
from pathlib import Path
from typing import Any

from kylin_aiops_api.database import Base
from kylin_aiops_api.main import create_app
from sqlalchemy import create_engine


def build_openapi_document() -> dict[str, Any]:
    """使用临时空库启用管理路由，确保导出内容不依赖开发机环境变量。"""

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        database_url = f"sqlite+pysqlite:///{Path(directory) / 'openapi.db'}"
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        engine.dispose()
        app = create_app(
            seed_demo=False,
            database_url=database_url,
            jwt_secret="openapi-export-secret-at-least-32-bytes",
            secure_cookies=False,
        )
        document = app.openapi()
        app.state.database.dispose()
        return document


def main() -> None:
    output = Path("services/ops-api/openapi.json")
    output.write_text(
        json.dumps(build_openapi_document(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
