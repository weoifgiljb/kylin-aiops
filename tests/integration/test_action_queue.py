from datetime import UTC, datetime, timedelta

from kylin_aiops_api.actions import ActionEnvelope
from kylin_aiops_api.queue import InMemoryActionQueue


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
