"""Tests for immich_cache module."""

import pytest
import json
import tempfile
from pathlib import Path
from immich_cache import ImmichCache


@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
    yield cache_path
    # Cleanup
    Path(cache_path).unlink(missing_ok=True)


@pytest.fixture
def sample_asset():
    """Create a sample asset for testing."""
    return {
        "id": "asset123",
        "originalFileName": "test.jpg",
        "description": "Test photo",
        "tags": ["vacation", "beach"],
        "dateTimeOriginal": "2025-06-15T18:30:00Z",
        "updatedAt": "2025-10-25T10:00:00Z",
        "albums": ["album1", "album2"]
    }


class TestImmichCache:
    """Tests for ImmichCache class."""
    
    def test_init(self, temp_cache_file):
        """Test initialization."""
        cache = ImmichCache(temp_cache_file)
        
        assert cache.cache_path == Path(temp_cache_file)
        assert cache.metadata["total_assets"] == 0
        assert len(cache.assets) == 0
        assert len(cache.indices) == 4
    
    def test_add_asset(self, temp_cache_file, sample_asset):
        """Test adding an asset."""
        cache = ImmichCache(temp_cache_file)
        
        cache.add_asset(sample_asset, "/path/to/test.jpg", "exact", "unique_filename")
        
        assert "asset123" in cache.assets
        assert cache.assets["asset123"]["immich_data"]["originalFileName"] == "test.jpg"
        assert cache.assets["asset123"]["file_mapping"]["matched_path"] == "/path/to/test.jpg"
        assert cache.assets["asset123"]["file_mapping"]["match_confidence"] == "exact"
    
    def test_add_asset_no_id(self, temp_cache_file):
        """Test adding asset without ID."""
        cache = ImmichCache(temp_cache_file)
        
        cache.add_asset({})
        
        assert len(cache.assets) == 0
    
    def test_add_asset_updates_newer(self, temp_cache_file, sample_asset):
        """Test that newer asset updates existing one."""
        cache = ImmichCache(temp_cache_file)
        
        # Add original
        cache.add_asset(sample_asset)
        
        # Update with newer version
        newer_asset = sample_asset.copy()
        newer_asset["updatedAt"] = "2025-10-26T10:00:00Z"
        newer_asset["description"] = "Updated description"
        
        cache.add_asset(newer_asset)
        
        assert cache.assets["asset123"]["immich_data"]["description"] == "Updated description"
    
    def test_add_asset_skips_older(self, temp_cache_file, sample_asset):
        """Test that older asset doesn't update existing one."""
        cache = ImmichCache(temp_cache_file)
        
        # Add original
        cache.add_asset(sample_asset)
        original_desc = sample_asset["description"]
        
        # Try to update with older version
        older_asset = sample_asset.copy()
        older_asset["updatedAt"] = "2025-10-24T10:00:00Z"
        older_asset["description"] = "Older description"
        
        cache.add_asset(older_asset)
        
        # Should not have updated
        assert cache.assets["asset123"]["immich_data"]["description"] == original_desc
    
    def test_get_asset(self, temp_cache_file, sample_asset):
        """Test getting an asset by ID."""
        cache = ImmichCache(temp_cache_file)
        cache.add_asset(sample_asset)
        
        asset = cache.get_asset("asset123")
        
        assert asset is not None
        assert asset["immich_data"]["originalFileName"] == "test.jpg"
    
    def test_get_asset_not_found(self, temp_cache_file):
        """Test getting non-existent asset."""
        cache = ImmichCache(temp_cache_file)
        
        asset = cache.get_asset("nonexistent")
        
        assert asset is None
    
    def test_find_by_filename(self, temp_cache_file, sample_asset):
        """Test finding assets by filename."""
        cache = ImmichCache(temp_cache_file)
        cache.add_asset(sample_asset)
        
        assets = cache.find_by_filename("test.jpg")
        
        assert len(assets) == 1
        assert assets[0]["immich_data"]["id"] == "asset123"
    
    def test_find_by_filename_multiple(self, temp_cache_file):
        """Test finding multiple assets with same filename."""
        cache = ImmichCache(temp_cache_file)
        
        cache.add_asset({
            "id": "asset1",
            "originalFileName": "photo.jpg",
            "updatedAt": "2025-10-25T10:00:00Z"
        })
        cache.add_asset({
            "id": "asset2",
            "originalFileName": "photo.jpg",
            "updatedAt": "2025-10-25T10:00:00Z"
        })
        
        assets = cache.find_by_filename("photo.jpg")
        
        assert len(assets) == 2
    
    def test_find_by_path(self, temp_cache_file, sample_asset):
        """Test finding asset by file path."""
        cache = ImmichCache(temp_cache_file)
        cache.add_asset(sample_asset, "/path/to/test.jpg")
        
        asset = cache.find_by_path("/path/to/test.jpg")
        
        assert asset is not None
        assert asset["immich_data"]["id"] == "asset123"
    
    def test_find_by_album(self, temp_cache_file, sample_asset):
        """Test finding assets by album."""
        cache = ImmichCache(temp_cache_file)
        cache.add_asset(sample_asset)
        
        assets = cache.find_by_album("album1")
        
        assert len(assets) == 1
        assert assets[0]["immich_data"]["id"] == "asset123"
    
    def test_find_by_tag(self, temp_cache_file, sample_asset):
        """Test finding assets by tag."""
        cache = ImmichCache(temp_cache_file)
        cache.add_asset(sample_asset)
        
        assets = cache.find_by_tag("vacation")
        
        assert len(assets) == 1
        assert assets[0]["immich_data"]["id"] == "asset123"
    
    def test_find_by_tag_dict_format(self, temp_cache_file):
        """Test finding assets with dict-format tags."""
        cache = ImmichCache(temp_cache_file)
        
        asset = {
            "id": "asset1",
            "originalFileName": "test.jpg",
            "tags": [{"name": "vacation"}, {"name": "beach"}],
            "updatedAt": "2025-10-25T10:00:00Z"
        }
        cache.add_asset(asset)
        
        assets = cache.find_by_tag("vacation")
        
        assert len(assets) == 1
    
    def test_save_and_load(self, temp_cache_file, sample_asset):
        """Test saving and loading cache."""
        # Create and save cache
        cache1 = ImmichCache(temp_cache_file)
        cache1.metadata["target_path"] = "/test/path"
        cache1.add_asset(sample_asset, "/path/to/test.jpg")
        cache1.save()
        
        # Load cache
        cache2 = ImmichCache(temp_cache_file)
        result = cache2.load()
        
        assert result is True
        assert len(cache2.assets) == 1
        assert "asset123" in cache2.assets
        assert cache2.metadata["target_path"] == "/test/path"
    
    def test_load_nonexistent(self, temp_cache_file):
        """Test loading non-existent cache file."""
        Path(temp_cache_file).unlink(missing_ok=True)
        cache = ImmichCache(temp_cache_file)
        
        result = cache.load()
        
        assert result is False
    
    def test_clear(self, temp_cache_file, sample_asset):
        """Test clearing cache."""
        cache = ImmichCache(temp_cache_file)
        cache.add_asset(sample_asset)
        
        cache.clear()
        
        assert len(cache.assets) == 0
        assert cache.metadata["total_assets"] == 0
        assert len(cache.indices["by_filename"]) == 0
    
    def test_rebuild_indices(self, temp_cache_file, sample_asset):
        """Test rebuilding indices."""
        cache = ImmichCache(temp_cache_file)
        cache.add_asset(sample_asset, "/path/to/test.jpg")
        
        # Clear indices
        cache.indices = {
            "by_filename": {},
            "by_path": {},
            "by_album": {},
            "by_tag": {}
        }
        
        # Rebuild
        cache.rebuild_indices()
        
        assert "test.jpg" in cache.indices["by_filename"]
        assert "/path/to/test.jpg" in cache.indices["by_path"]
        assert "album1" in cache.indices["by_album"]
        assert "vacation" in cache.indices["by_tag"]
    
    def test_get_stats(self, temp_cache_file, sample_asset):
        """Test getting cache statistics."""
        cache = ImmichCache(temp_cache_file)
        cache.metadata["target_path"] = "/test"
        
        # Add matched asset
        cache.add_asset(sample_asset, "/path/to/test.jpg", "exact")
        
        # Add unmatched asset
        unmatched = {
            "id": "asset456",
            "originalFileName": "missing.jpg",
            "updatedAt": "2025-10-25T10:00:00Z",
            "tags": ["other"],
            "albums": ["album3"]
        }
        cache.add_asset(unmatched, None, "none")
        
        stats = cache.get_stats()
        
        assert stats["total_assets"] == 2
        assert stats["matched_files"] == 1
        assert stats["unmatched_files"] == 1
        assert stats["unique_filenames"] == 2
        assert stats["albums"] == 3  # album1, album2, album3
        assert stats["tags"] == 3  # vacation, beach, other
        assert stats["target_path"] == "/test"
    
    def test_save_creates_directory(self, temp_cache_file):
        """Test that save creates parent directory if needed."""
        # Use a cache path in non-existent directory
        cache_dir = Path(temp_cache_file).parent / "subdir"
        cache_path = cache_dir / "cache.json"
        
        cache = ImmichCache(str(cache_path))
        cache.add_asset({
            "id": "asset1",
            "originalFileName": "test.jpg",
            "updatedAt": "2025-10-25T10:00:00Z"
        })
        
        result = cache.save()
        
        assert result is True
        assert cache_path.exists()
        
        # Cleanup
        cache_path.unlink()
        cache_dir.rmdir()
