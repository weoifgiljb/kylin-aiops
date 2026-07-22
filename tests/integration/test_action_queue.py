from datetime import UTC, datetime, timedelta

from kylin_aiops_api.actions import ActionEnvelope
from kylin_aiops_api.queue import InMemoryActionQueue, RedisActionQueue


class MemoryRedis:
    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}

    def rpush(self, key: str, payload: str) -> None:
        self.lists.setdefault(key, []).append(payload)

    def lpop(self, key: str) -> str | None:
        items = self.lists.get(key, [])
        return items.pop(0) if items else None


def envelope(action_id: str, node_id: str) -> ActionEnvelope:
    now = datetime.now(UTC)
    return ActionEnvelope(
        action_id,
        node_id,
        "restart",
        {},
        now,
        now + timedelta(minutes=5),
        "signature",
    )


def test_queue_only_dequeues_actions_for_target_node() -> None:
    now = datetime.now(UTC)
    queue = InMemoryActionQueue()
    queue.enqueue(
        ActionEnvelope("one", "db-01", "terminate", {}, now, now + timedelta(minutes=5), "a")
    )
    queue.enqueue(
        ActionEnvelope("two", "app-01", "restart", {}, now, now + timedelta(minutes=5), "b")
    )

    selected = queue.dequeue("app-01")

    assert selected is not None and selected.action_id == "two"
    assert queue.dequeue("app-01") is None
    assert queue.dequeue("db-01").action_id == "one"


def test_redis_queue_does_not_scan_other_node_actions() -> None:
    queue = RedisActionQueue(MemoryRedis())
    for index in range(150):
        queue.enqueue(envelope(f"a-{index}", "node-a"))
    queue.enqueue(envelope("target", "node-b"))

    selected = queue.dequeue("node-b")

    assert selected is not None
    assert selected.action_id == "target"


def test_redis_queue_atomically_consumes_one_action() -> None:
    queue = RedisActionQueue(MemoryRedis())
    queue.enqueue(envelope("only", "node-a"))

    assert queue.dequeue("node-a") is not None
    assert queue.dequeue("node-a") is None
