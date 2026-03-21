"""Business logic for extracting Immich metadata into WORKFLOW cache."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Dict

from cache_store import CacheStore
from immich_client import ImmichClient


@dataclass
class ImmichToCacheResult:
    """Result summary for one extraction run."""

    fetched: int
    inserted: int
    updated: int
    cache_path: str


class ImmichToCacheService:
    """Coordinates Immich extraction and cache persistence."""

    def __init__(self, client: ImmichClient, cache_store: CacheStore, logger: Any):
        self.client = client
        self.cache_store = cache_store
        self.logger = logger

    def run(self, options: Dict[str, Any]) -> ImmichToCacheResult:
        """Execute extraction from Immich and persist into cache."""
        before = options.get("before")
        after = options.get("after")
        album_name = options.get("album_name")
        immich_library_root = options.get("immich_library_root")
        include_albums = options.get("albums", False) or options.get("all", False)
        include_people = options.get("people", False) or options.get("all", False)

        if not immich_library_root:
            raise ValueError("Missing immich_library_root in runtime options")

        self.cache_store.load()

        assets = self.client.fetch_assets(
            before=before,
            after=after,
            album_name=album_name,
            include_albums=include_albums,
            include_people=include_people,
        )

        for asset in assets:
            immich_relative_path = self._to_relative_path(
                asset.get("immich_path", ""),
                str(immich_library_root),
            )
            asset["immich_relative_path"] = immich_relative_path
            asset["path_key"] = immich_relative_path

            self.logger.audit(
                "asset_extract status=success immich_asset_id=%s immich_name=%s",
                asset.get("immich_asset_id"),
                asset.get("immich_name"),
            )

        merge_stats = self.cache_store.merge_from_immich(assets)
        self.cache_store.save()

        return ImmichToCacheResult(
            fetched=len(assets),
            inserted=merge_stats["inserted"],
            updated=merge_stats["updated"],
            cache_path=str(self.cache_store.cache_path),
        )

    @staticmethod
    def _to_relative_path(full_path: str, root_path: str) -> str:
        if not full_path:
            raise ValueError("Immich asset missing immich_path")

        full_posix = PurePosixPath(str(full_path).replace("\\", "/"))
        root_posix = PurePosixPath(str(root_path).replace("\\", "/"))

        try:
            return full_posix.relative_to(root_posix).as_posix()
        except ValueError as exc:
            raise ValueError(
                f"Immich path '{full_path}' is not under configured root '{root_path}'"
            ) from exc
