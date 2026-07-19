import json
from dataclasses import asdict
from datetime import datetime
from typing import Protocol

from redis import Redis

from .actions import ActionEnvelope


class ActionQueue(Protocol):
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
    def __init__(self) -> None:
        self.items: list[ActionEnvelope] = []

    def enqueue(self, envelope: ActionEnvelope) -> None:
        self.items.append(envelope)

    def dequeue(self, node_id: str) -> ActionEnvelope | None:
        for index, envelope in enumerate(self.items):
            if envelope.node_id == node_id:
                return self.items.pop(index)
        return None


class RedisStreamActionQueue:
    stream = "kylin-aiops:approved-actions"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @classmethod
    def from_url(cls, url: str) -> "RedisStreamActionQueue":
        return cls(Redis.from_url(url, decode_responses=True))

    def enqueue(self, envelope: ActionEnvelope) -> None:
        self.redis.xadd(self.stream, {"node_id": envelope.node_id, "payload": _serialize(envelope)})

    def dequeue(self, node_id: str) -> ActionEnvelope | None:
        for message_id, fields in self.redis.xrange(self.stream, min="-", max="+", count=100):
            if fields["node_id"] == node_id:
                self.redis.xdel(self.stream, message_id)
                return _deserialize(fields["payload"])
        return None
