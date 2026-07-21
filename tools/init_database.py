"""通过 Alembic 把中心 PostgreSQL Schema 升级到当前版本。"""

import argparse
import os

from alembic import command
from alembic.config import Config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("请设置 DATABASE_URL 或传入 --database-url")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", args.database_url)
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
