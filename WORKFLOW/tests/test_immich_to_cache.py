#!/usr/bin/env python3
"""Tests for immich_to_cache script and service layer."""

import json
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
repo_root = project_root.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))
sys.path.insert(0, str(repo_root / "COMMON" / "src"))

import immich_to_cache
from cache_store import CacheStore
from immich_to_cache_service import ImmichToCacheService


class StubLogger:
    def __init__(self):
        self.audit_messages = []

    def info(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None

    def audit(self, message, *args):
        self.audit_messages.append(message % args if args else message)


class StubClient:
    def __init__(self, assets):
        self.assets = assets

    def fetch_assets(self, **_kwargs):
        return self.assets


def test_script_info_fields():
    info = immich_to_cache.SCRIPT_INFO
    assert info["name"]
    assert info["description"]
    assert isinstance(info.get("examples"), list)
    assert len(info["examples"]) > 0


def test_script_arguments_expected_flags():
    args = immich_to_cache.SCRIPT_ARGUMENTS
    assert args["cache"]["flag"] == "--cache"
    assert args["album_name"]["flag"] == "--album-name"
    assert args["before"]["flag"] == "--before"
    assert args["after"]["flag"] == "--after"
    assert args["albums"]["flag"] == "--albums"
    assert args["people"]["flag"] == "--people"
    assert args["all"]["flag"] == "--all"


def test_validate_iso8601_date_rejects_bad_value():
    parser = immich_to_cache.ScriptArgumentParser(
        immich_to_cache.SCRIPT_INFO,
        immich_to_cache.ARGUMENTS,
    )

    with pytest.raises(SystemExit):
        immich_to_cache.validate_iso8601_date("2026-03-01", "--before", parser)


def test_build_runtime_options_sets_default_cache(monkeypatch):
    monkeypatch.setattr(immich_to_cache, "default_cache_path", lambda: ".cache/cache_2026-03-20.json")
    options = immich_to_cache.build_runtime_options({"albums": True}, "/photos/library")
    assert options["cache"] == ".cache/cache_2026-03-20.json"
    assert options["albums"] is True
    assert options["immich_library_root"] == "/photos/library"


def test_main_requires_immich_env(monkeypatch):
    monkeypatch.setattr(immich_to_cache, "load_immich_credentials", lambda: ("", "", ""))
    monkeypatch.setattr(sys, "argv", ["immich_to_cache.py"])

    with pytest.raises(SystemExit):
        immich_to_cache.main()


def test_service_run_writes_cache_and_audit(tmp_path):
    cache_file = tmp_path / "cache.json"
    logger = StubLogger()
    client = StubClient(
        [
            {
                "immich_asset_id": "asset-1",
                "immich_name": "IMG_0001.JPG",
                "immich_path": "/photos/library/Trips/IMG_0001.JPG",
            },
            {
                "immich_asset_id": "asset-2",
                "immich_name": "IMG_0002.JPG",
                "immich_path": "/photos/library/Trips/IMG_0002.JPG",
            },
        ]
    )
    store = CacheStore(str(cache_file), logger)
    service = ImmichToCacheService(client, store, logger)

    result = service.run({"immich_library_root": "/photos/library"})

    assert result.fetched == 2
    assert result.inserted == 2
    assert result.updated == 0
    assert cache_file.exists()
    assert len(logger.audit_messages) == 2

    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert payload["metadata"]["total_assets"] == 2
    assert "asset-1" in payload["assets"]
    assert payload["assets"]["asset-1"]["path_key"] == "Trips/IMG_0001.JPG"


def test_main_success(monkeypatch, tmp_path):
    class MockClient:
        def __init__(self, _url, _api_key, _logger):
            return None

        def validate_connection(self):
            return True

        def fetch_assets(self, **_kwargs):
            return []

    class MockService:
        def __init__(self, _client, _cache_store, _logger):
            return None

        def run(self, options):
            class Result:
                fetched = 0
                inserted = 0
                updated = 0
                cache_path = options["cache"]

            return Result()

    monkeypatch.setattr(
        immich_to_cache,
        "load_immich_credentials",
        lambda: ("https://immich.example", "key", "/photos/library"),
    )
    monkeypatch.setattr(immich_to_cache, "ImmichClient", MockClient)
    monkeypatch.setattr(immich_to_cache, "ImmichToCacheService", MockService)

    cache_path = tmp_path / "cache.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["immich_to_cache.py", "--cache", str(cache_path)],
    )

    exit_code = immich_to_cache.main()
    assert exit_code == 0
