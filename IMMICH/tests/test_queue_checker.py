#!/usr/bin/env python3
"""Tests for queue_checker module."""

from queue_checker import QueueChecker


class _DummyConnection:
    def __init__(self, queues):
        self._queues = queues

    def get_queues(self):
        return self._queues


class _DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None


def test_queue_checker_idle():
    queues = [
        {
            "name": "library",
            "isPaused": False,
            "statistics": {
                "active": 0,
                "waiting": 0,
                "delayed": 0,
                "failed": 0,
                "completed": 10,
            },
        }
    ]
    checker = QueueChecker(_DummyConnection(queues), _DummyLogger())
    overview = checker.fetch_queue_overview()
    assert overview.all_idle is True
    assert overview.queues[0].is_idle is True


def test_queue_checker_busy():
    queues = [
        {
            "name": "library",
            "isPaused": False,
            "statistics": {
                "active": 1,
                "waiting": 0,
                "delayed": 0,
                "failed": 0,
                "completed": 10,
            },
        }
    ]
    checker = QueueChecker(_DummyConnection(queues), _DummyLogger())
    overview = checker.fetch_queue_overview()
    assert overview.all_idle is False
    assert overview.queues[0].is_idle is False


def test_queue_checker_missing_stats():
    queues = [{"name": "library"}]
    checker = QueueChecker(_DummyConnection(queues), _DummyLogger())
    overview = checker.fetch_queue_overview()
    assert overview.queues[0].active == 0
    assert overview.queues[0].waiting == 0
    assert overview.queues[0].delayed == 0
    assert overview.all_idle is True
