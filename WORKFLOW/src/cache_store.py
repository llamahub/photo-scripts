"""JSON cache persistence for WORKFLOW metadata extraction."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class CacheStore:
    """Load and save shared WORKFLOW cache records."""

    def __init__(self, cache_path: str, logger: Any):
        self.cache_path = Path(cache_path)
        self.logger = logger
        self.metadata: Dict[str, Any] = {
            "created": None,
            "last_updated": None,
            "source": "immich",
            "source_path": "",
            "total_assets": 0,
        }
        self.assets: Dict[str, Dict[str, Any]] = {}

    def load(self) -> None:
        """Load cache file when present, otherwise keep empty in-memory state."""
        if not self.cache_path.exists():
            return

        with self.cache_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.metadata = payload.get("metadata", self.metadata)
        self.assets = payload.get("assets", {})

    def merge_from_immich(self, asset_records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Insert or update Immich-derived records using strict path_key matching."""
        inserted = 0
        updated = 0
        path_index = self._build_path_index()

        for record in asset_records:
            asset_id = record.get("immich_asset_id")
            path_key = record.get("path_key")
            if not asset_id or not path_key:
                continue

            existing_key = path_index.get(str(path_key))
            if existing_key:
                merged = dict(self.assets[existing_key])
                merged.update(record)
                self.assets[existing_key] = merged
                updated += 1
                continue

            key = self._create_insert_key(asset_id, str(path_key))
            self.assets[key] = record
            path_index[str(path_key)] = key
            inserted += 1

        return {"inserted": inserted, "updated": updated}

    def merge_from_files(self, records: List[Dict[str, Any]], source_path: str) -> Dict[str, int]:
        """Insert or update file-derived records with path_key-first matching."""
        inserted = 0
        updated = 0

        self.metadata["source_path"] = source_path

        path_index = self._build_path_index()
        file_hash_index = self._build_file_hash_index()

        for record in records:
            file_hash = record.get("file_hash")
            path_key = record.get("path_key")
            if not file_hash or not path_key:
                continue

            existing_key = self._find_existing_key(record, path_index, file_hash_index)

            if existing_key:
                merged_record = dict(self.assets[existing_key])
                merged_record.update(record)
                self.assets[existing_key] = merged_record
                updated += 1
                file_hash_index[str(file_hash)] = existing_key
                path_index[str(path_key)] = existing_key
                continue

            self.assets[str(file_hash)] = record
            inserted += 1
            file_hash_index[str(file_hash)] = str(file_hash)
            path_index[str(path_key)] = str(file_hash)

        return {"inserted": inserted, "updated": updated}

    def _build_file_hash_index(self) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for cache_key, record in self.assets.items():
            file_hash = record.get("file_hash")
            if file_hash:
                index[str(file_hash)] = cache_key
        return index

    @staticmethod
    def _find_existing_key(
        record: Dict[str, Any],
        path_index: Dict[str, str],
        file_hash_index: Dict[str, str],
    ) -> str:
        file_hash = str(record.get("file_hash", ""))
        path_key = str(record.get("path_key", ""))

        if path_key and path_key in path_index:
            return path_index[path_key]

        if file_hash and file_hash in file_hash_index:
            return file_hash_index[file_hash]

        return ""

    def _build_path_index(self) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for cache_key, record in self.assets.items():
            path_key = record.get("path_key")
            if path_key:
                index[str(path_key)] = cache_key
        return index

    def _create_insert_key(self, asset_id: str, path_key: str) -> str:
        if asset_id not in self.assets:
            return asset_id
        return f"{asset_id}::{path_key}"

    def save(self) -> None:
        """Write cache JSON to disk."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.metadata.get("created"):
            self.metadata["created"] = now_iso
        self.metadata["last_updated"] = now_iso
        self.metadata["total_assets"] = len(self.assets)

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": self.metadata,
            "assets": self.assets,
        }

        with self.cache_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
