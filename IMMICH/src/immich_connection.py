"""Immich API connection and data extraction."""

import logging
import requests
from typing import List, Optional, Dict, Any


class ImmichConnection:
    """Handles connection and data extraction from Immich API."""
    
    def __init__(self, url: str, api_key: str, logger: Optional[logging.Logger] = None):
        """
        Initialize Immich API connection.
        
        Args:
            url: Base URL of Immich server
            api_key: API key for authentication
            logger: Optional logger instance
        """
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
    
    def validate_connection(self) -> bool:
        """
        Test connection to Immich server.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/server/ping")
            return resp.status_code == 200
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Connection validation failed: {e}")
            return False
    
    def search_assets(
        self, 
        updated_before: Optional[str] = None,
        updated_after: Optional[str] = None,
        album_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for assets with optional filters, handles pagination.
        
        Args:
            updated_before: ISO 8601 date/time - only assets updated before this time
            updated_after: ISO 8601 date/time - only assets updated after this time
            album_id: Only assets from this album
            
        Returns:
            List of asset dictionaries
        """
        # If album_id is specified, use album endpoint instead of search
        if album_id:
            return self._get_album_assets(album_id)
        
        # Use search endpoint with filters
        search_payload: Dict[str, Any] = {"withExif": True}
        
        if updated_after:
            search_payload["updatedAfter"] = updated_after
        
        if updated_before:
            search_payload["updatedBefore"] = updated_before
        
        assets = []
        page = 1
        
        try:
            while True:
                search_payload["page"] = page
                resp = self.session.post(
                    f"{self.base_url}/api/search/metadata", 
                    json=search_payload
                )
                resp.raise_for_status()
                
                data = resp.json()
                
                # Handle nested response structure
                while isinstance(data, dict) and "data" in data:
                    data = data["data"]
                
                # Extract assets from various response formats
                page_assets = self._extract_assets_from_response(data)
                
                if not page_assets:
                    break
                
                assets.extend(page_assets)
                
                if len(assets) % 1000 == 0:
                    self.logger.info(f"Fetched {len(assets)} assets so far...")
                
                # Check for next page
                next_page = self._get_next_page(data)
                if next_page is None:
                    break
                
                page = next_page
            
            self.logger.info(f"Total assets fetched: {len(assets)}")
            return assets
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error searching assets: {e}")
            raise
    
    def _get_album_assets(self, album_id: str) -> List[Dict[str, Any]]:
        """
        Get all assets from a specific album.
        
        Args:
            album_id: Album ID
            
        Returns:
            List of asset dictionaries
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/albums/{album_id}")
            resp.raise_for_status()
            album_data = resp.json()
            assets = album_data.get("assets", [])
            
            # Enrich each asset with album information
            for asset in assets:
                if "albums" not in asset:
                    asset["albums"] = []
                if album_id not in asset["albums"]:
                    asset["albums"].append(album_id)
            
            self.logger.info(f"Fetched {len(assets)} assets from album {album_id}")
            return assets
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching album assets: {e}")
            raise
    
    def _extract_assets_from_response(self, data: Any) -> List[Dict[str, Any]]:
        """
        Extract assets list from various API response formats.
        
        Args:
            data: Response data from API
            
        Returns:
            List of assets or empty list
        """
        # Format 1: {"assets": {"items": [...]}}
        if isinstance(data, dict) and "assets" in data:
            assets_obj = data["assets"]
            if isinstance(assets_obj, dict) and "items" in assets_obj:
                return assets_obj["items"] if isinstance(assets_obj["items"], list) else []
            elif isinstance(assets_obj, list):
                return assets_obj
        
        # Format 2: Direct list
        if isinstance(data, list):
            return data
        
        return []
    
    def _get_next_page(self, data: Any) -> Optional[int]:
        """
        Extract next page number from API response.
        
        Args:
            data: Response data from API
            
        Returns:
            Next page number or None if no more pages
        """
        if isinstance(data, dict):
            # Check assets object first
            if "assets" in data and isinstance(data["assets"], dict):
                if data["assets"].get("nextPage"):
                    return int(data["assets"]["nextPage"])
            
            # Check top level
            if data.get("nextPage"):
                return int(data["nextPage"])
        
        return None
    
    def get_asset_details(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific asset.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            Asset details dictionary or None if not found
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/assets/{asset_id}")
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching asset details for {asset_id}: {e}")
            return None
    
    def get_album_info(self, album_id: str) -> Optional[Dict[str, Any]]:
        """
        Get album information.
        
        Args:
            album_id: Album ID
            
        Returns:
            Album information dictionary or None if not found
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/albums/{album_id}")
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching album info for {album_id}: {e}")
            return None
    
    def delete_assets(self, asset_ids: List[str], force: bool = False) -> bool:
        """
        Delete assets from Immich.
        
        Args:
            asset_ids: List of asset IDs to delete
            force: If True, permanently delete (bypass trash). If False, move to trash.
            
        Returns:
            True if deletion successful, False otherwise
        """
        if not asset_ids:
            return True
        
        try:
            payload = {
                "ids": asset_ids,
                "force": force
            }
            resp = self.session.delete(
                f"{self.base_url}/api/assets",
                json=payload
            )
            resp.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error deleting assets: {e}")
            return False
    
    def get_libraries(self) -> List[Dict[str, Any]]:
        """
        Get all libraries from Immich.
        
        Returns:
            List of library dictionaries with id, name, type, etc.
        """
        try:
            resp = self.session.get(f"{self.base_url}/api/libraries")
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching libraries: {e}")
            return []
    
    def scan_library(self, library_id: str) -> bool:
        """
        Trigger library scan to re-import assets.
        
        Args:
            library_id: Library ID to scan
            
        Returns:
            True if scan triggered successfully, False otherwise
        """
        try:
            resp = self.session.post(
                f"{self.base_url}/api/libraries/{library_id}/scan"
            )
            # 204 No Content is the expected success response
            return resp.status_code == 204
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error triggering library scan: {e}")
            return False
