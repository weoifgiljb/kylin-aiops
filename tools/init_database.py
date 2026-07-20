"""Initialize the center PostgreSQL schema for offline or manual deployments."""

import argparse

from kylin_aiops_api.database import Base
from sqlalchemy import create_engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    engine = create_engine(args.database_url)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    main()
