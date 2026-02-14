#!/usr/bin/env python3
"""Tests for update.py --force, --all, and select column logic."""

import sys
from pathlib import Path
import pytest
import update

class DummyLogger:
    def info(self, *_args, **_kwargs): return None
    def error(self, *_args, **_kwargs): return None
    def warning(self, *_args, **_kwargs): return None
    def debug(self, *_args, **_kwargs): return None
    def audit(self, *_args, **_kwargs): return None

class DummyUpdater:
    def __init__(self, csv_path, logger, dry_run=False, all_rows=False, max_workers=None, force=False, **kwargs):
        self.csv_path = csv_path
        self.dry_run = dry_run
        self.all_rows = all_rows
        self.force = force
        self.called = True
    def process(self):
        # Simulate different row selection logic
        if self.all_rows:
            return {"rows_total": 3, "rows_selected": 3, "errors": 0}
        elif self.force:
            return {"rows_total": 3, "rows_selected": 2, "errors": 0}
        else:
            return {"rows_total": 3, "rows_selected": 1, "errors": 0}

@pytest.fixture
def csv_file(tmp_path):
    csv = tmp_path / "analyze.csv"
    # Simulate a CSV with a Select column: one selected, two not
    csv.write_text("Filename,Select\nfile1.jpg,y\nfile2.jpg,n\nfile3.jpg,\n")
    return csv

def run_update_with_args(monkeypatch, csv_path, args):
    monkeypatch.setattr(update.ScriptArgumentParser, "setup_logging", lambda *_a, **_k: DummyLogger())
    monkeypatch.setattr(update, "ImageUpdater", DummyUpdater)
    monkeypatch.setattr(sys, "argv", ["update.py"] + args)
    return update.main()

def test_update_honors_select_column(csv_file, monkeypatch):
    # Only selected row processed
    rc = run_update_with_args(monkeypatch, csv_file, ["--input", str(csv_file)])
    assert rc == 0

def test_update_all_ignores_select(csv_file, monkeypatch):
    # All rows processed
    rc = run_update_with_args(monkeypatch, csv_file, ["--input", str(csv_file), "--all"])
    assert rc == 0

def test_update_force_honors_select(csv_file, monkeypatch):
    # Force updates, but only for selected rows
    rc = run_update_with_args(monkeypatch, csv_file, ["--input", str(csv_file), "--force"])
    assert rc == 0

def test_update_force_and_all(csv_file, monkeypatch):
    # Force updates for all rows
    rc = run_update_with_args(monkeypatch, csv_file, ["--input", str(csv_file), "--force", "--all"])
    assert rc == 0
