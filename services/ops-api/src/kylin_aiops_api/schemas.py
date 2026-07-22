"""定义跨路由与存储层共享的 API 输入模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Enrollment(BaseModel):
    node_id: str
    hostname: str
    architecture: str
    kylin_version: str


class ActionResult(BaseModel):
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    health_check: Literal["passed", "failed"]


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    fingerprint: str = Field(min_length=1)


class AlertWebhook(BaseModel):
    status: Literal["firing", "resolved"]
    alerts: list[Alert]
