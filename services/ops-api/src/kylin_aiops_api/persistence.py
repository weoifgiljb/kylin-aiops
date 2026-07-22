"""集中管理数据库连接池和会话工厂，避免同一进程重复创建 engine。"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    """持有进程级共享 engine，并向认证和业务存储提供同一会话工厂。"""

    def __init__(self, url: str) -> None:
        self.engine: Engine = create_engine(url, pool_pre_ping=True)
        self.sessions: sessionmaker[Session] = sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

    def dispose(self) -> None:
        """显式释放连接池，供短生命周期工具和测试清理资源。"""

        self.engine.dispose()
