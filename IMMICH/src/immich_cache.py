"""Immich metadata cache management."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class ImmichCache:
    """Manages CRUD operations on Immich metadata cache."""
    
    def __init__(self, cache_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize cache manager.
        
        Args:
            cache_path: Path to cache JSON file
            logger: Optional logger instance
        """
        self.cache_path = Path(cache_path)
        self.logger = logger or logging.getLogger(__name__)
        
        # Cache structure
        self.metadata: Dict[str, Any] = {
            "created": None,
            "last_updated": None,
            "target_path": None,
            "total_assets": 0
        }
        self.assets: Dict[str, Dict[str, Any]] = {}
        
        # Indices (built on-the-fly, not persisted)
        self.indices: Dict[str, Any] = {
            "by_filename": {},
            "by_path": {},
            "by_album": {},
            "by_tag": {}
        }
    
    def load(self) -> bool:
        """
        Load cache from JSON file and rebuild indices.
        
        Returns:
            True if loaded successfully, False if file doesn't exist or error
        """
        if not self.cache_path.exists():
            self.logger.info(f"Cache file not found: {self.cache_path}")
            return False
        
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get("metadata", self.metadata)
            self.assets = data.get("assets", {})
            
            # Rebuild indices from loaded data
            self.rebuild_indices()
            
            self.logger.info(
                f"Loaded cache with {len(self.assets)} assets from {self.cache_path}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading cache: {e}")
            return False
    
    def save(self) -> bool:
        """
        Save cache to JSON file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Update metadata
            self.metadata["last_updated"] = datetime.now().isoformat() + "Z"
            self.metadata["total_assets"] = len(self.assets)
            
            # Create cache directory if it doesn't exist
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data (no indices in saved file)
            data = {
                "metadata": self.metadata,
                "assets": self.assets
            }
            
            # Write to file
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved cache with {len(self.assets)} assets to {self.cache_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving cache: {e}")
            return False
    
    def clear(self):
        """Clear all cache data."""
        self.metadata = {
            "created": datetime.now().isoformat() + "Z",
            "last_updated": None,
            "target_path": None,
            "total_assets": 0
        }
        self.assets = {}
        self.indices = {
            "by_filename": {},
            "by_path": {},
            "by_album": {},
            "by_tag": {}
        }
        self.logger.info("Cache cleared")
    
    def add_asset(
        self, 
        asset_data: Dict[str, Any], 
        file_path: Optional[str] = None,
        match_confidence: str = "none",
        match_method: str = "none"
    ):
        """
        Add or update an asset in cache.
        
        Args:
            asset_data: Full asset data from Immich
            file_path: Matched file path (if found)
            match_confidence: "exact", "fuzzy", "none"
            match_method: How file was matched
        """
        asset_id = asset_data.get("id")
        if not asset_id:
            self.logger.warning("Cannot add asset without ID")
            return
        
        # Check if we should update (if asset already exists)
        if asset_id in self.assets:
            existing = self.assets[asset_id]
            existing_updated_at = existing.get("immich_data", {}).get("updatedAt", "")
            new_updated_at = asset_data.get("updatedAt", "")
            
            # Only update if Immich data is newer
            if new_updated_at <= existing_updated_at:
                self.logger.debug(
                    f"Skipping asset {asset_id}: existing data is newer or same"
                )
                return
        
        # Build asset entry
        asset_entry = {
            "immich_data": asset_data,
            "file_mapping": {
                "matched_path": file_path or "",
                "match_confidence": match_confidence,
                "matched_at": datetime.now().isoformat() + "Z",
                "match_method": match_method
            }
        }
        
        self.assets[asset_id] = asset_entry
        
        # Update indices
        self._update_indices_for_asset(asset_id, asset_entry)
        
        self.logger.debug(f"Added/updated asset {asset_id}")
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get asset by ID.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            Asset entry or None
        """
        return self.assets.get(asset_id)
    
    def find_by_filename(self, filename: str) -> List[Dict[str, Any]]:
        """
        Find assets by filename.
        
        Args:
            filename: Original filename to search for
            
        Returns:
            List of matching assets
        """
        asset_ids = self.indices["by_filename"].get(filename, [])
        return [self.assets[aid] for aid in asset_ids if aid in self.assets]
    
    def find_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Find asset by matched file path.
        
        Args:
            path: File path to search for
            
        Returns:
            Asset entry or None
        """
        asset_id = self.indices["by_path"].get(path)
        return self.assets.get(asset_id) if asset_id else None
    
    def find_by_album(self, album_id: str) -> List[Dict[str, Any]]:
        """
        Find all assets in an album.
        
        Args:
            album_id: Album ID
            
        Returns:
            List of matching assets
        """
        asset_ids = self.indices["by_album"].get(album_id, [])
        return [self.assets[aid] for aid in asset_ids if aid in self.assets]
    
    def find_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Find all assets with a tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of matching assets
        """
        asset_ids = self.indices["by_tag"].get(tag, [])
        return [self.assets[aid] for aid in asset_ids if aid in self.assets]
    
    def rebuild_indices(self):
        """Rebuild all search indices from assets."""
        self.indices = {
            "by_filename": {},
            "by_path": {},
            "by_album": {},
            "by_tag": {}
        }
        
        for asset_id, asset_entry in self.assets.items():
            self._update_indices_for_asset(asset_id, asset_entry)
        
        self.logger.debug("Rebuilt indices")
    
    def _update_indices_for_asset(self, asset_id: str, asset_entry: Dict[str, Any]):
        """
        Update indices for a single asset.
        
        Args:
            asset_id: Asset ID
            asset_entry: Asset entry with immich_data and file_mapping
        """
        immich_data = asset_entry.get("immich_data", {})
        file_mapping = asset_entry.get("file_mapping", {})
        
        # Index by filename
        filename = immich_data.get("originalFileName", "")
        if filename:
            if filename not in self.indices["by_filename"]:
                self.indices["by_filename"][filename] = []
            if asset_id not in self.indices["by_filename"][filename]:
                self.indices["by_filename"][filename].append(asset_id)
        
        # Index by path
        matched_path = file_mapping.get("matched_path", "")
        if matched_path:
            self.indices["by_path"][matched_path] = asset_id
        
        # Index by album
        albums = immich_data.get("albums", [])
        for album_id in albums:
            if album_id not in self.indices["by_album"]:
                self.indices["by_album"][album_id] = []
            if asset_id not in self.indices["by_album"][album_id]:
                self.indices["by_album"][album_id].append(asset_id)
        
        # Index by tag
        tags = immich_data.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                # Handle both string tags and dict tags
                tag_name = tag if isinstance(tag, str) else tag.get("name", "")
                if tag_name:
                    if tag_name not in self.indices["by_tag"]:
                        self.indices["by_tag"][tag_name] = []
                    if asset_id not in self.indices["by_tag"][tag_name]:
                        self.indices["by_tag"][tag_name].append(asset_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Return cache statistics.
        
        Returns:
            Dictionary with statistics
        """
        matched = sum(
            1 for a in self.assets.values() 
            if a.get("file_mapping", {}).get("match_confidence") != "none"
        )
        
        return {
            "total_assets": len(self.assets),
            "matched_files": matched,
            "unmatched_files": len(self.assets) - matched,
            "unique_filenames": len(self.indices["by_filename"]),
            "albums": len(self.indices["by_album"]),
            "tags": len(self.indices["by_tag"]),
            "created": self.metadata.get("created"),
            "last_updated": self.metadata.get("last_updated"),
            "target_path": self.metadata.get("target_path")
        }
