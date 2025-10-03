"""
Tests for the centralized temporary file management system.
"""

import pytest
import tempfile
import time
from pathlib import Path
from common.temp import (
    TempManager,
    get_debug_temp_dir,
    get_cache_temp_dir,
    temp_working_dir,
    pytest_temp_dirs,
)


class TestTempManager:
    """Test cases for the TempManager class."""

    def test_create_persistent_dir(self, tmp_path, monkeypatch):
        """Test creating persistent temporary directories."""
        # Change to temp directory to avoid affecting real project
        monkeypatch.chdir(tmp_path)

        # Test basic creation
        temp_dir = TempManager.create_persistent_dir("test")
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert temp_dir.parent.name == ".tmp"
        assert "test_" in temp_dir.name

    def test_create_persistent_dir_with_category(self, tmp_path, monkeypatch):
        """Test creating persistent directories with categories."""
        monkeypatch.chdir(tmp_path)

        temp_dir = TempManager.create_persistent_dir("test", "debug")
        assert temp_dir.exists()
        assert temp_dir.parent.name == "debug"
        assert temp_dir.parent.parent.name == ".tmp"

    def test_auto_cleanup_dir(self):
        """Test auto-cleanup temporary directory context manager."""
        temp_path = None

        with TempManager.auto_cleanup_dir("test") as temp_dir:
            temp_path = temp_dir
            assert temp_path.exists()
            assert temp_path.is_dir()
            assert "test_" in temp_path.name

            # Create a file to verify cleanup
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            assert test_file.exists()

        # Directory should be cleaned up
        assert not temp_path.exists()

    def test_create_persistent_file(self, tmp_path, monkeypatch):
        """Test creating persistent temporary files."""
        monkeypatch.chdir(tmp_path)

        temp_file = TempManager.create_persistent_file("config", ".json")
        assert temp_file.exists()
        assert temp_file.is_file()
        assert temp_file.suffix == ".json"
        assert "config_" in temp_file.name

    def test_create_persistent_file_with_category(self, tmp_path, monkeypatch):
        """Test creating persistent files with categories."""
        monkeypatch.chdir(tmp_path)

        temp_file = TempManager.create_persistent_file("data", ".csv", "cache")
        assert temp_file.exists()
        assert temp_file.parent.parent.name == "cache"

    def test_auto_cleanup_file(self):
        """Test auto-cleanup temporary file context manager."""
        temp_path = None

        with TempManager.auto_cleanup_file("test", ".txt") as temp_file:
            temp_path = temp_file
            assert temp_path.exists()
            assert temp_path.suffix == ".txt"
            assert "test_" in temp_path.name

            # Write content to verify cleanup
            temp_path.write_text("test content")
            assert temp_path.read_text() == "test content"

        # File should be cleaned up
        assert not temp_path.exists()

    def test_clean_persistent_temps(self, tmp_path, monkeypatch):
        """Test cleaning persistent temporary items."""
        monkeypatch.chdir(tmp_path)

        # Create some temporary items
        temp_dir1 = TempManager.create_persistent_dir("test1")
        temp_dir2 = TempManager.create_persistent_dir("test2", "debug")
        temp_file = TempManager.create_persistent_file("config", ".json")

        # Verify they exist
        assert temp_dir1.exists()
        assert temp_dir2.exists()
        assert temp_file.exists()

        # Clean them
        cleaned_count = TempManager.clean_persistent_temps()
        assert cleaned_count >= 3  # Should clean at least the files we created

        # Verify cleanup (directories might still exist if empty)
        assert not temp_file.exists()

    def test_clean_persistent_temps_with_age(self, tmp_path, monkeypatch):
        """Test cleaning with age restriction."""
        monkeypatch.chdir(tmp_path)

        # Create a temporary file
        temp_file = TempManager.create_persistent_file("old", ".txt")
        assert temp_file.exists()

        # Try to clean with 1 hour age limit (should not clean recent file)
        cleaned_count = TempManager.clean_persistent_temps(max_age_hours=1)
        assert temp_file.exists()  # Should still exist

        # Clean without age limit
        cleaned_count = TempManager.clean_persistent_temps()
        assert not temp_file.exists()  # Should be cleaned

    def test_list_persistent_temps(self, tmp_path, monkeypatch):
        """Test listing persistent temporary items."""
        monkeypatch.chdir(tmp_path)

        # Initially should be empty
        items = TempManager.list_persistent_temps()
        initial_count = len(items)

        # Create some items
        temp_dir = TempManager.create_persistent_dir("test")
        temp_file = TempManager.create_persistent_file("data", ".json")

        # Should now have more items
        items = TempManager.list_persistent_temps()
        assert len(items) >= initial_count + 2


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_debug_temp_dir(self, tmp_path, monkeypatch):
        """Test debug temp directory creation."""
        monkeypatch.chdir(tmp_path)

        debug_dir = get_debug_temp_dir("test_debug")
        assert debug_dir.exists()
        assert debug_dir.parent.name == "debug"
        assert "test_debug_" in debug_dir.name

    def test_get_cache_temp_dir(self, tmp_path, monkeypatch):
        """Test cache temp directory creation."""
        monkeypatch.chdir(tmp_path)

        cache_dir = get_cache_temp_dir("test_cache")
        assert cache_dir.exists()
        assert cache_dir.parent.name == "cache"
        assert "test_cache_" in cache_dir.name

    def test_temp_working_dir(self):
        """Test temporary working directory context manager."""
        temp_path = None

        with temp_working_dir("work") as work_dir:
            temp_path = work_dir
            assert temp_path.exists()
            assert temp_path.is_dir()

            # Create some files
            (work_dir / "file1.txt").write_text("content1")
            (work_dir / "file2.txt").write_text("content2")

        # Should be cleaned up
        assert not temp_path.exists()

    def test_pytest_temp_dirs(self):
        """Test pytest temp dirs helper."""
        with pytest_temp_dirs(3, ["source", "target", "work"]) as dirs:
            source, target, work = dirs

            assert len(dirs) == 3
            assert all(d.exists() and d.is_dir() for d in dirs)
            assert source.name == "source"
            assert target.name == "target"
            assert work.name == "work"

            # All should be in the same parent directory
            assert source.parent == target.parent == work.parent

    def test_pytest_temp_dirs_default_names(self):
        """Test pytest temp dirs with default names."""
        with pytest_temp_dirs(2) as dirs:
            source, target = dirs
            assert source.name == "source"
            assert target.name == "target"


if __name__ == "__main__":
    pytest.main([__file__])
