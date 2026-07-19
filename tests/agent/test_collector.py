from kylin_aiops_agent.collector import SystemCollector


class FixedProvider:
    def cpu_percent(self) -> float:
        return 42.0

    def memory_percent(self) -> float:
        return 61.5

    def disk_percent(self, path: str) -> float:
        assert path == "/"
        return 70.0

    def load_average(self) -> tuple[float, float, float]:
        return (1.0, 0.8, 0.5)

    def process_count(self) -> int:
        return 123

    def connection_count(self) -> int:
        return 45


def test_collector_emits_normalized_metric_batch() -> None:
    batch = SystemCollector(node_id="app-01", provider=FixedProvider()).collect()

    assert batch.node_id == "app-01"
    assert batch.metrics == {
        "cpu_percent": 42.0,
        "memory_percent": 61.5,
        "disk_percent": 70.0,
        "load_1m": 1.0,
        "load_5m": 0.8,
        "load_15m": 0.5,
        "process_count": 123.0,
        "connection_count": 45.0,
    }
    assert batch.observed_at.tzinfo is not None
