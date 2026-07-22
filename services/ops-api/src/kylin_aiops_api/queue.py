"""提供中心 API 与轮询 Agent 共享的已审批动作队列适配器。"""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Protocol

from redis import Redis

from .actions import ActionEnvelope


class ActionQueue(Protocol):
    """内存测试与 Redis 实现共享的最小队列契约。"""

    def enqueue(self, envelope: ActionEnvelope) -> None: ...
    def dequeue(self, node_id: str) -> ActionEnvelope | None: ...


def _serialize(envelope: ActionEnvelope) -> str:
    data = asdict(envelope)
    data["issued_at"] = envelope.issued_at.isoformat()
    data["expires_at"] = envelope.expires_at.isoformat()
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _deserialize(payload: str) -> ActionEnvelope:
    data = json.loads(payload)
    data["issued_at"] = datetime.fromisoformat(data["issued_at"])
    data["expires_at"] = datetime.fromisoformat(data["expires_at"])
    return ActionEnvelope(**data)


class InMemoryActionQueue:
    """用于本地开发和单元测试的确定性队列。"""

    def __init__(self) -> None:
        self.items: list[ActionEnvelope] = []

    def enqueue(self, envelope: ActionEnvelope) -> None:
        self.items.append(envelope)

    def dequeue(self, node_id: str) -> ActionEnvelope | None:
        for index, envelope in enumerate(self.items):
            if envelope.node_id == node_id:
                return self.items.pop(index)
        return None


class RedisActionQueue:
    """按节点隔离的 Redis List 队列，使用 LPOP 原子取走动作。"""

    prefix = "kylin-aiops:approved-actions"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @classmethod
    def from_url(cls, url: str) -> "RedisActionQueue":
        return cls(Redis.from_url(url, decode_responses=True))

    def _key(self, node_id: str) -> str:
        return f"{self.prefix}:{node_id}"

    def enqueue(self, envelope: ActionEnvelope) -> None:
        self.redis.rpush(self._key(envelope.node_id), _serialize(envelope))

    def dequeue(self, node_id: str) -> ActionEnvelope | None:
        payload = self.redis.lpop(self._key(node_id))
        return _deserialize(payload) if payload is not None else None
