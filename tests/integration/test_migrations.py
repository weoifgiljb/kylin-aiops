import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from kylin_aiops_api.database import NodeRow
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError


def test_alembic_upgrades_an_empty_database(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migrated.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert {"users", "auth_sessions", "nodes", "incidents", "audit_logs"} <= tables


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="设置 TEST_POSTGRES_URL 后在一次性空 PostgreSQL 库运行",
)
def test_postgresql_empty_database_migration_restart_and_concurrency() -> None:
    database_url = os.environ["TEST_POSTGRES_URL"]
    engine = create_engine(database_url)
    assert engine.dialect.name == "postgresql"
    assert inspect(engine).get_table_names() == []
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")

    with Session(engine) as session:
        session.add(NodeRow(id="pg-node-01", display_name="重启持久化节点", status="offline"))
        session.commit()
    restarted_engine = create_engine(database_url)
    first = Session(restarted_engine)
    second = Session(restarted_engine)
    first_row = first.get(NodeRow, "pg-node-01")
    second_row = second.get(NodeRow, "pg-node-01")
    assert first_row is not None and second_row is not None
    first_row.display_name = "第一个提交"
    first_row.version += 1
    second_row.display_name = "第二个提交"
    second_row.version += 1
    first.commit()
    with pytest.raises(StaleDataError):
        second.commit()
    first.close()
    second.close()
