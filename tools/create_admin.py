"""以交互方式创建首个管理员，避免密码出现在命令历史和进程参数中。"""

import argparse
import getpass
import os

from kylin_aiops_api.auth import seed_admin


def main() -> None:
    parser = argparse.ArgumentParser(description="创建 Kylin AIOps 首个管理员")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("请设置 DATABASE_URL 或传入 --database-url")
    password = getpass.getpass("管理员密码（至少 12 个字符）: ")
    confirmed = getpass.getpass("再次输入管理员密码: ")
    if password != confirmed:
        raise SystemExit("两次输入的密码不一致")
    if len(password) < 12:
        raise SystemExit("管理员密码至少需要 12 个字符")
    seed_admin(args.database_url, args.username, password, args.display_name)
    print("管理员创建成功")


if __name__ == "__main__":
    main()
