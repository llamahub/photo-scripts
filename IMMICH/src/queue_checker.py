#!/usr/bin/env python3
"""Queue status evaluation for Immich queues."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class QueueInfo:
    name: str
    is_paused: bool
    active: int
    waiting: int
    delayed: int
    failed: int
    completed: int

    @property
    def is_idle(self) -> bool:
        return self.active == 0 and self.waiting == 0 and self.delayed == 0


@dataclass(frozen=True)
class QueueOverview:
    queues: List[QueueInfo]
    all_idle: bool


class QueueChecker:
    """Evaluate Immich queues to determine whether the system is idle."""

    def __init__(self, connection, logger) -> None:
        self.connection = connection
        self.logger = logger

    def fetch_queue_overview(self) -> QueueOverview:
        queues = self.connection.get_queues()
        return self.summarize(queues)

    def summarize(self, queues: List[Dict[str, Any]]) -> QueueOverview:
        queue_infos = [self._to_queue_info(queue) for queue in queues]
        all_idle = all(queue.is_idle for queue in queue_infos)
        return QueueOverview(queues=queue_infos, all_idle=all_idle)

    def _to_queue_info(self, queue: Dict[str, Any]) -> QueueInfo:
        stats = queue.get("statistics") or {}
        return QueueInfo(
            name=str(queue.get("name", "unknown")),
            is_paused=bool(queue.get("isPaused", False)),
            active=self._get_int(stats, "active"),
            waiting=self._get_int(stats, "waiting"),
            delayed=self._get_int(stats, "delayed"),
            failed=self._get_int(stats, "failed"),
            completed=self._get_int(stats, "completed"),
        )

    @staticmethod
    def _get_int(stats: Dict[str, Any], key: str) -> int:
        value = stats.get(key)
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
