"""通过显式确认执行压测数据写入或清理，且不负责创建数据库表。"""

import argparse
import json

from kylin_aiops_api.load_data import LoadDataConfig, purge_load_data, seed_load_data
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数，并在创建数据库连接前拒绝未经确认的修改操作。"""
    parser = argparse.ArgumentParser(description="写入或清理压测演示数据")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--confirm-load-data", action="store_true")
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=1_000)
    parser.add_argument("--purge", action="store_true")
    arguments = parser.parse_args()
    if not arguments.confirm_load_data:
        parser.error("必须显式传入 --confirm-load-data 才能修改数据库")
    return arguments


def main() -> None:
    """执行压测数据操作；数据表必须预先由迁移流程创建。"""
    arguments = parse_arguments()
    engine = create_engine(arguments.database_url)
    try:
        with Session(engine) as session:
            if arguments.purge:
                mode = "purge"
                counts = purge_load_data(session)
            else:
                mode = "seed"
                counts = seed_load_data(
                    session,
                    LoadDataConfig(
                        count=arguments.count,
                        seed=arguments.seed,
                        batch_size=arguments.batch_size,
                    ),
                )
    finally:
        engine.dispose()

    print(json.dumps({"mode": mode, "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
