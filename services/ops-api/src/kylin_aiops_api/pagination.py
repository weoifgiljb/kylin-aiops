"""提供数据库原生分页，避免在应用进程加载完整结果集。"""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

T = TypeVar("T")


@dataclass(frozen=True)
class PageRows(Generic[T]):
    items: list[T]
    total: int


def page_scalars(
    session: Session,
    statement: Select[tuple[T]],
    page: int,
    page_size: int,
) -> PageRows[T]:
    """分别查询总数与当前页；传入语句必须已包含业务筛选和稳定排序。"""

    total_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(session.scalar(total_statement) or 0)
    items = list(session.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return PageRows(items, total)


def page_response(
    items: list[dict[str, Any]],
    total: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """构造所有列表接口共享的分页响应。"""

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
