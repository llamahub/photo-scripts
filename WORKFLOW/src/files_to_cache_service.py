"""Business logic for extracting file metadata into WORKFLOW cache."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from cache_store import CacheStore


@dataclass
class FilesToCacheResult:
    """Summary for one files_to_cache run."""

    scanned: int
    inserted: int
    updated: int
    cache_path: str


class FilesToCacheService:
    """Extract file metadata from source folder and persist to cache."""

    SIDECAR_EXTENSIONS = {"xmp", "json"}

    def __init__(self, cache_store: CacheStore, logger: Any):
        self.cache_store = cache_store
        self.logger = logger

    def run(self, options: Dict[str, Any]) -> FilesToCacheResult:
        """Execute file scan and cache write."""
        source_path = Path(options["source"])

        self.cache_store.load()

        records: List[Dict[str, Any]] = []
        for file_path in source_path.rglob("*"):
            if not file_path.is_file() or self._should_skip(file_path):
                continue

            record = self._build_record(file_path, source_path)
            records.append(record)
            self.logger.audit(
                "file_extract status=success file_hash=%s filename=%s",
                record["file_hash"],
                record["filename"],
            )

        upsert_stats = self.cache_store.merge_from_files(records, str(source_path))
        self.cache_store.save()

        return FilesToCacheResult(
            scanned=len(records),
            inserted=upsert_stats["inserted"],
            updated=upsert_stats["updated"],
            cache_path=str(self.cache_store.cache_path),
        )

    def _build_record(self, file_path: Path, source_root: Path) -> Dict[str, Any]:
        file_hash = self._hash_file(file_path)
        folder_date = self._extract_folder_date(file_path.parent.name)
        filename_date, filename_time = self._extract_filename_datetime(file_path.name)
        relative_path = file_path.relative_to(source_root).as_posix()

        return {
            "file_hash": file_hash,
            "source_root": str(source_root),
            "relative_path": relative_path,
            "path_key": relative_path,
            "folder_path": str(file_path.parent),
            "filename": file_path.name,
            "filename_date": filename_date,
            "filename_time": filename_time,
            "folder_date": folder_date,
            "folder_event": file_path.parent.name,
            "exif_ext": file_path.suffix.lower().lstrip("."),
            "last_extract_status": "match",
            "last_extract_file_action": "keep",
            "last_extract_exif_action": "keep",
        }

    def _hash_file(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _should_skip(self, file_path: Path) -> bool:
        name_lower = file_path.name.lower()
        if name_lower.startswith("."):
            return True
        if ".xmp." in name_lower or ".json." in name_lower:
            return True

        ext = file_path.suffix.lower().lstrip(".")
        return ext in self.SIDECAR_EXTENSIONS

    @staticmethod
    def _extract_folder_date(folder_name: str) -> str:
        if re.match(r"^\d{4}-\d{2}-\d{2}", folder_name):
            return folder_name[:10]
        if re.match(r"^\d{4}-\d{2}$", folder_name):
            return f"{folder_name}-01"
        return ""

    @staticmethod
    def _extract_filename_datetime(filename: str) -> tuple[str, str]:
        pattern = re.compile(r"(\d{4}-\d{2}-\d{2})[_-]?(\d{4})")
        match = pattern.search(filename)
        if not match:
            return "", ""

        return match.group(1), match.group(2)
