"""Host metric collection abstraction and psutil implementation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import psutil


class MetricsProvider(Protocol):
    def cpu_percent(self) -> float: ...
    def memory_percent(self) -> float: ...
    def disk_percent(self, path: str) -> float: ...
    def load_average(self) -> tuple[float, float, float]: ...
    def process_count(self) -> int: ...
    def connection_count(self) -> int: ...


class PsutilProvider:
    def cpu_percent(self) -> float:
        return psutil.cpu_percent(interval=None)

    def memory_percent(self) -> float:
        return psutil.virtual_memory().percent

    def disk_percent(self, path: str) -> float:
        return psutil.disk_usage(path).percent

    def load_average(self) -> tuple[float, float, float]:
        return psutil.getloadavg()

    def process_count(self) -> int:
        return len(psutil.pids())

    def connection_count(self) -> int:
        try:
            return len(psutil.net_connections(kind="inet"))
        except (psutil.AccessDenied, PermissionError):
            return 0


@dataclass(frozen=True)
class MetricBatch:
    node_id: str
    observed_at: datetime
    metrics: dict[str, float]


class SystemCollector:
    """Collect one normalized metrics batch without retaining host state."""

    def __init__(self, node_id: str, provider: MetricsProvider | None = None) -> None:
        if not node_id.strip():
            raise ValueError("node_id is required")
        self.node_id = node_id
        self.provider = provider or PsutilProvider()

    def collect(self) -> MetricBatch:
        """Read the current CPU, memory, disk, load, process, and connection metrics."""

        load_1m, load_5m, load_15m = self.provider.load_average()
        return MetricBatch(
            node_id=self.node_id,
            observed_at=datetime.now(UTC),
            metrics={
                "cpu_percent": float(self.provider.cpu_percent()),
                "memory_percent": float(self.provider.memory_percent()),
                "disk_percent": float(self.provider.disk_percent("/")),
                "load_1m": float(load_1m),
                "load_5m": float(load_5m),
                "load_15m": float(load_15m),
                "process_count": float(self.provider.process_count()),
                "connection_count": float(self.provider.connection_count()),
            },
        )
