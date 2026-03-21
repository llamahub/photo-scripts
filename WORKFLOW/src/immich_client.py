"""Immich API client used by WORKFLOW scripts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


class ImmichClient:
    """Small API client for extracting asset metadata from Immich."""

    def __init__(self, base_url: str, api_key: str, logger: Any):
        self.base_url = base_url.rstrip("/")
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})

    def validate_connection(self) -> bool:
        """Return True when Immich responds to ping endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/api/server/ping", timeout=15)
            return response.status_code == 200
        except requests.RequestException as exc:
            self.logger.error("Immich ping failed: %s", exc)
            return False

    def fetch_assets(
        self,
        before: Optional[str] = None,
        after: Optional[str] = None,
        album_name: Optional[str] = None,
        include_albums: bool = False,
        include_people: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch asset metadata from Immich search endpoint with paging."""
        payload: Dict[str, Any] = {
            "page": 1,
            "size": 1000,
            "withExif": True,
        }
        if before:
            payload["updatedBefore"] = before
        if after:
            payload["updatedAfter"] = after
        if album_name:
            payload["albumName"] = album_name

        assets: List[Dict[str, Any]] = []

        while True:
            response = self.session.post(
                f"{self.base_url}/api/search/metadata",
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            page_assets, next_page = self._parse_search_response(response.json())

            for asset in page_assets:
                normalized = self._normalize_asset(
                    asset,
                    include_albums=include_albums,
                    include_people=include_people,
                )
                assets.append(normalized)

            if next_page is None:
                break
            payload["page"] = next_page

        return assets

    def fetch_updated_timestamps(
        self,
        before: Optional[str] = None,
        after: Optional[str] = None,
        album_name: Optional[str] = None,
    ) -> List[str]:
        """Fetch only asset update timestamps for fast daily-count reporting."""
        payload: Dict[str, Any] = {
            "page": 1,
            "size": 1000,
            "withExif": False,
        }
        if before:
            payload["updatedBefore"] = before
        if after:
            payload["updatedAfter"] = after
        if album_name:
            payload["albumName"] = album_name

        timestamps: List[str] = []

        while True:
            response = self.session.post(
                f"{self.base_url}/api/search/metadata",
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            page_assets, next_page = self._parse_search_response(response.json())

            for asset in page_assets:
                updated_at = self._extract_updated_at(asset)
                if updated_at:
                    timestamps.append(updated_at)

            if next_page is None:
                break
            payload["page"] = next_page

        return timestamps

    def _parse_search_response(self, data: Any) -> tuple[List[Dict[str, Any]], Optional[int]]:
        current = data
        while isinstance(current, dict) and "data" in current:
            current = current["data"]

        if isinstance(current, dict):
            assets_obj = current.get("assets", {})
            if isinstance(assets_obj, dict):
                items = assets_obj.get("items", [])
                next_page = assets_obj.get("nextPage")
                if isinstance(items, list):
                    parsed_next = int(next_page) if next_page else None
                    return items, parsed_next

        return [], None

    def _normalize_asset(
        self,
        asset: Dict[str, Any],
        include_albums: bool,
        include_people: bool,
    ) -> Dict[str, Any]:
        exif = asset.get("exifInfo") or {}
        original_path = asset.get("originalPath") or ""
        file_name = asset.get("originalFileName") or ""

        normalized: Dict[str, Any] = {
            "immich_asset_id": asset.get("id"),
            "immich_path": original_path,
            "immich_name": file_name,
            "immich_ext": self._extract_extension(file_name),
            "immich_date": exif.get("dateTimeOriginal") or asset.get("fileCreatedAt"),
            "immich_time": exif.get("timeZone") or "",
            "immich_offset": exif.get("offsetTimeOriginal") or "",
            "immich_timezone": exif.get("timeZone") or "",
            "immich_description": asset.get("description") or "",
            "immich_tags": self._extract_tag_names(asset.get("tags", [])),
            "immich_albums": [],
            "immich_people": [],
            "raw": asset,
        }

        if include_albums:
            normalized["immich_albums"] = self._extract_album_names(asset.get("albums", []))
        if include_people:
            normalized["immich_people"] = self._extract_people_names(asset.get("people", []))

        return normalized

    @staticmethod
    def _extract_extension(filename: str) -> str:
        if "." not in filename:
            return ""
        return filename.rsplit(".", 1)[1].lower()

    @staticmethod
    def _extract_tag_names(tags: Any) -> List[str]:
        names: List[str] = []
        if not isinstance(tags, list):
            return names

        for tag in tags:
            if isinstance(tag, str):
                names.append(tag)
                continue
            if isinstance(tag, dict) and tag.get("name"):
                names.append(str(tag["name"]))

        return names

    @staticmethod
    def _extract_album_names(albums: Any) -> List[str]:
        names: List[str] = []
        if not isinstance(albums, list):
            return names

        for album in albums:
            if isinstance(album, str):
                names.append(album)
                continue
            if isinstance(album, dict):
                value = album.get("albumName") or album.get("name") or album.get("id")
                if value:
                    names.append(str(value))

        return names

    @staticmethod
    def _extract_people_names(people: Any) -> List[str]:
        names: List[str] = []
        if not isinstance(people, list):
            return names

        for person in people:
            if isinstance(person, str):
                names.append(person)
                continue
            if isinstance(person, dict):
                value = person.get("name") or person.get("id")
                if value:
                    names.append(str(value))

        return names

    @staticmethod
    def _extract_updated_at(asset: Dict[str, Any]) -> str:
        return (
            asset.get("updatedAt")
            or asset.get("fileModifiedAt")
            or asset.get("fileCreatedAt")
            or ""
        )
