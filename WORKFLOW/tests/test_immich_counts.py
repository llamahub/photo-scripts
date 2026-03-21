#!/usr/bin/env python3
"""Tests for immich_counts script and service logic."""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
repo_root = project_root.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))
sys.path.insert(0, str(repo_root / "COMMON" / "src"))

import immich_counts
from immich_counts_service import ImmichCountsService


class StubLogger:
    def __init__(self):
        self.lines = []

    def info(self, message, *args):
        rendered = message % args if args else message
        self.lines.append(rendered)

    def error(self, *_args, **_kwargs):
        return None


class StubClient:
    def __init__(self, timestamps):
        self.timestamps = timestamps

    def fetch_updated_timestamps(self, **_kwargs):
        return self.timestamps


def test_script_info_fields():
    info = immich_counts.SCRIPT_INFO
    assert info["name"]
    assert info["description"]
    assert isinstance(info.get("examples"), list)


def test_script_arguments_expected_flags():
    args = immich_counts.SCRIPT_ARGUMENTS
    assert args["album_name"]["flag"] == "--album-name"
    assert args["before"]["flag"] == "--before"
    assert args["after"]["flag"] == "--after"


def test_validate_iso8601_date_rejects_bad_value():
    parser = immich_counts.ScriptArgumentParser(
        immich_counts.SCRIPT_INFO,
        immich_counts.ARGUMENTS,
    )
    with pytest.raises(SystemExit):
        immich_counts.validate_iso8601_date("2026-03-20", "--after", parser)


def test_service_groups_by_day():
    logger = StubLogger()
    client = StubClient(
        [
            "2026-03-19T00:01:02Z",
            "2026-03-19T10:10:10Z",
            "2026-03-20T09:00:00+00:00",
        ]
    )
    service = ImmichCountsService(client, logger)

    result = service.run({})

    assert result.total_assets == 3
    assert result.total_days == 2
    assert result.counts_by_day["2026-03-19"] == 2
    assert result.counts_by_day["2026-03-20"] == 1


def test_main_requires_immich_env(monkeypatch):
    monkeypatch.setattr(immich_counts, "load_immich_credentials", lambda: ("", ""))
    monkeypatch.setattr(sys, "argv", ["immich_counts.py"])

    with pytest.raises(SystemExit):
        immich_counts.main()


def test_main_success(monkeypatch):
    class MockClient:
        def __init__(self, _url, _api_key, _logger):
            return None

        def validate_connection(self):
            return True

    class MockService:
        def __init__(self, _client, _logger):
            return None

        def run(self, _options):
            class Result:
                total_assets = 12
                total_days = 2
                counts_by_day = {"2026-03-19": 7, "2026-03-20": 5}

            return Result()

    monkeypatch.setattr(
        immich_counts,
        "load_immich_credentials",
        lambda: ("https://immich.example", "key"),
    )
    monkeypatch.setattr(immich_counts, "ImmichClient", MockClient)
    monkeypatch.setattr(immich_counts, "ImmichCountsService", MockService)
    monkeypatch.setattr(sys, "argv", ["immich_counts.py", "--after", "2026-03-01T00:00:00Z"])

    exit_code = immich_counts.main()
    assert exit_code == 0
