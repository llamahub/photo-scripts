#!/usr/bin/env python3
"""Tests for files_to_cache script and service layer."""

import json
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
repo_root = project_root.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))
sys.path.insert(0, str(repo_root / "COMMON" / "src"))

import files_to_cache
from cache_store import CacheStore
from files_to_cache_service import FilesToCacheService


class StubLogger:
    def __init__(self):
        self.audit_messages = []

    def info(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None

    def audit(self, message, *args):
        self.audit_messages.append(message % args if args else message)


def test_script_info_fields():
    info = files_to_cache.SCRIPT_INFO
    assert info["name"]
    assert info["description"]
    assert isinstance(info.get("examples"), list)
    assert len(info["examples"]) > 0


def test_script_arguments_required():
    args = files_to_cache.SCRIPT_ARGUMENTS
    assert args["source"]["positional"] is True
    assert args["source"]["flag"] == "--source"
    assert args["cache"]["flag"] == "--cache"


def test_parse_required_positional(tmp_path):
    parser = files_to_cache.ScriptArgumentParser(files_to_cache.SCRIPT_INFO, files_to_cache.ARGUMENTS)
    args = parser.parse_args([str(tmp_path)])
    resolved = parser.validate_required_args(args, {"source": ["source", "source_file"]})
    assert resolved["source"] == str(tmp_path)


def test_parse_required_named(tmp_path):
    parser = files_to_cache.ScriptArgumentParser(files_to_cache.SCRIPT_INFO, files_to_cache.ARGUMENTS)
    args = parser.parse_args(["--source", str(tmp_path)])
    resolved = parser.validate_required_args(args, {"source": ["source", "source_file"]})
    assert resolved["source"] == str(tmp_path)


def test_service_run_writes_cache_and_audit(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    image_file = source / "2026-03-20_1300_trip.jpg"
    image_file.write_bytes(b"image-data")
    sidecar = source / "2026-03-20_1300_trip.xmp"
    sidecar.write_text("xmp", encoding="utf-8")
    hidden = source / ".DS_Store"
    hidden.write_bytes(b"mac")

    cache_file = tmp_path / "cache.json"
    logger = StubLogger()

    store = CacheStore(str(cache_file), logger)
    service = FilesToCacheService(store, logger)
    result = service.run({"source": str(source)})

    assert result.scanned == 1
    assert result.inserted == 1
    assert result.updated == 0
    assert len(logger.audit_messages) == 1
    assert cache_file.exists()

    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert payload["metadata"]["total_assets"] == 1
    assert len(payload["assets"]) == 1


def test_service_updates_existing_immich_entry_by_path_key(tmp_path):
    source = tmp_path / "source"
    source.mkdir()

    image_name = "2026-03-20_1300_trip.jpg"
    image_file = source / image_name
    image_file.write_bytes(b"image-data")

    cache_file = tmp_path / "cache.json"
    existing_cache = {
        "metadata": {
            "created": "2026-03-20T00:00:00+00:00",
            "last_updated": "2026-03-20T00:00:00+00:00",
            "source": "immich",
            "total_assets": 1,
        },
        "assets": {
            "immich-asset-1": {
                "immich_asset_id": "immich-asset-1",
                "immich_name": image_name,
                "path_key": image_name,
            }
        },
    }
    cache_file.write_text(json.dumps(existing_cache), encoding="utf-8")

    logger = StubLogger()
    store = CacheStore(str(cache_file), logger)
    service = FilesToCacheService(store, logger)
    result = service.run({"source": str(source)})

    assert result.scanned == 1
    assert result.inserted == 0
    assert result.updated == 1

    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert len(payload["assets"]) == 1
    assert "immich-asset-1" in payload["assets"]
    assert payload["assets"]["immich-asset-1"]["filename"] == image_name
    assert payload["assets"]["immich-asset-1"]["file_hash"]


def test_main_requires_existing_source(monkeypatch, tmp_path):
    missing = tmp_path / "missing"
    monkeypatch.setattr(sys, "argv", ["files_to_cache.py", str(missing)])

    with pytest.raises(SystemExit):
        files_to_cache.main()


def test_main_success(monkeypatch, tmp_path):
    class MockService:
        def __init__(self, _store, _logger):
            return None

        def run(self, options):
            class Result:
                scanned = 1
                inserted = 1
                updated = 0
                cache_path = options["cache"]

            return Result()

    source = tmp_path / "source"
    source.mkdir()

    monkeypatch.setattr(files_to_cache, "FilesToCacheService", MockService)
    monkeypatch.setattr(sys, "argv", ["files_to_cache.py", str(source)])

    exit_code = files_to_cache.main()
    assert exit_code == 0
