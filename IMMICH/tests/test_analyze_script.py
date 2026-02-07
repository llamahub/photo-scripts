#!/usr/bin/env python3
"""Tests for IMMICH analyze CLI script."""

from pathlib import Path
import sys

import analyze


def test_main_success(tmp_path, monkeypatch):
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    output_file = tmp_path / "out.csv"

    class DummyLogger:
        def info(self, *_args, **_kwargs):
            return None

        def error(self, *_args, **_kwargs):
            return None

    class DummyAnalyzer:
        def __init__(self, *_args, **_kwargs):
            pass

        def analyze_to_csv(self, _output):
            return 42

    monkeypatch.setattr(analyze.ScriptLogging, "get_script_logger", lambda **_kwargs: DummyLogger())
    monkeypatch.setattr(analyze, "ImageAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(sys, "argv", ["analyze.py", "--source", str(source_dir), "--output", str(output_file)])

    assert analyze.main() == 0


def test_main_missing_source(tmp_path, monkeypatch):
    missing_dir = tmp_path / "missing"

    class DummyLogger:
        def info(self, *_args, **_kwargs):
            return None

        def error(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(analyze.ScriptLogging, "get_script_logger", lambda **_kwargs: DummyLogger())
    monkeypatch.setattr(sys, "argv", ["analyze.py", "--source", str(missing_dir)])

    assert analyze.main() == 1
