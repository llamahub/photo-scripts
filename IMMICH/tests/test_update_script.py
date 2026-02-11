#!/usr/bin/env python3
"""Tests for IMMICH update CLI script."""

from pathlib import Path
import sys

import update


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def debug(self, *_args, **_kwargs):
        return None

    def audit(self, *_args, **_kwargs):
        return None


def test_main_success(tmp_path, monkeypatch):
    csv_path = tmp_path / "analyze.csv"
    csv_path.write_text("header\n")

    latest_used = {"path": None}

    class DummyUpdater:
        def __init__(self, csv_path, logger, dry_run=False):
            latest_used["path"] = Path(csv_path)

        def process(self):
            return {"rows_total": 1, "rows_selected": 1, "errors": 0}

    monkeypatch.setattr(update.ScriptArgumentParser, "setup_logging", lambda *_args, **_kwargs: _DummyLogger())
    monkeypatch.setattr(update, "ImageUpdater", DummyUpdater)
    monkeypatch.setattr(sys, "argv", ["update.py", "--input", str(csv_path)])

    assert update.main() == 0
    assert latest_used["path"] == csv_path


def test_main_last_uses_latest(tmp_path, monkeypatch):
    log_dir = tmp_path / ".log"
    log_dir.mkdir()
    first = log_dir / "analyze_2024-01-01_1200.csv"
    second = log_dir / "analyze_2024-01-02_1200.csv"
    first.write_text("header\n")
    second.write_text("header\n")

    class DummyUpdater:
        def __init__(self, csv_path, logger, dry_run=False):
            self.csv_path = csv_path

        def process(self):
            return {"rows_total": 1, "rows_selected": 1, "errors": 0}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update.ScriptArgumentParser, "setup_logging", lambda *_args, **_kwargs: _DummyLogger())
    monkeypatch.setattr(update, "ImageUpdater", DummyUpdater)
    monkeypatch.setattr(sys, "argv", ["update.py", "--last"])

    assert update.main() == 0
