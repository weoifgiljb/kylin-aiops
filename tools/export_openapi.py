import json
from pathlib import Path

from kylin_aiops_api.main import create_app


def main() -> None:
    output = Path("services/ops-api/openapi.json")
    output.write_text(
        json.dumps(create_app(seed_demo=False).openapi(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
