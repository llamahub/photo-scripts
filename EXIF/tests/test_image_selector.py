#!/usr/bin/env python3
"""
Unit tests for ImageSelector class.

Tests the image selection and copying functionality including:
- File discovery and filtering
- Multi-stage sampling strategy
- Sidecar file handling
- Error handling and validation
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from exif.image_selector import ImageSelector


class TestImageSelector:
    """Test cases for ImageSelector class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary source and target directories."""
        source_dir = tempfile.mkdtemp()
        target_dir = tempfile.mkdtemp()

        yield Path(source_dir), Path(target_dir)

        # Cleanup
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(target_dir, ignore_errors=True)

    @pytest.fixture
    def sample_images(self, temp_dirs):
        """Create sample image structure."""
        source_dir, target_dir = temp_dirs

        # Create directory structure
        (source_dir / "subfolder1").mkdir()
        (source_dir / "subfolder2").mkdir()
        (source_dir / "deep" / "nested").mkdir(parents=True)

        # Create image files
        image_files = [
            source_dir / "root1.jpg",
            source_dir / "root2.png",
            source_dir / "subfolder1" / "sub1.jpg",
            source_dir / "subfolder1" / "sub2.tiff",
            source_dir / "subfolder2" / "sub3.heic",
            source_dir / "deep" / "nested" / "deep1.jpeg",
        ]

        for img_file in image_files:
            img_file.write_text("fake image content")

        # Create some non-image files
        (source_dir / "document.txt").write_text("not an image")
        (source_dir / "subfolder1" / "readme.md").write_text("readme")

        # Create sidecar files
        (source_dir / "root1.xmp").write_text("xmp metadata")
        (source_dir / "subfolder1" / "sub1.yml").write_text("yml metadata")
        (source_dir / "subfolder2" / "sub3_metadata.json").write_text("json metadata")

        return source_dir, target_dir, image_files

    def test_init_basic(self, temp_dirs):
        """Test basic initialization."""
        source_dir, target_dir = temp_dirs

        selector = ImageSelector(source_dir, target_dir)

        assert selector.source == source_dir.resolve()
        assert selector.target == target_dir.resolve()
        assert selector.max_files == 10
        assert selector.max_folders == 3
        assert selector.max_depth == 2
        assert selector.max_per_folder == 2
        assert selector.clean_target is False
        assert selector.debug is False
        assert isinstance(selector.folder_counts, dict)
        assert "total_images_found" in selector.stats

    def test_init_custom_params(self, temp_dirs):
        """Test initialization with custom parameters."""
        source_dir, target_dir = temp_dirs

        selector = ImageSelector(
            source=source_dir,
            target=target_dir,
            max_files=25,
            max_folders=5,
            max_depth=3,
            max_per_folder=4,
            clean_target=True,
            debug=True,
        )

        assert selector.max_files == 25
        assert selector.max_folders == 5
        assert selector.max_depth == 3
        assert selector.max_per_folder == 4
        assert selector.clean_target is True
        assert selector.debug is True

    def test_is_image_file(self, temp_dirs):
        """Test image file detection."""
        source_dir, target_dir = temp_dirs
        selector = ImageSelector(source_dir, target_dir)

        # Test supported formats
        assert selector.is_image_file(Path("test.jpg"))
        assert selector.is_image_file(Path("test.JPEG"))
        assert selector.is_image_file(Path("test.png"))
        assert selector.is_image_file(Path("test.bmp"))
        assert selector.is_image_file(Path("test.tif"))
        assert selector.is_image_file(Path("test.TIFF"))
        assert selector.is_image_file(Path("test.heic"))

        # Test unsupported formats
        assert not selector.is_image_file(Path("test.txt"))
        assert not selector.is_image_file(Path("test.pdf"))
        assert not selector.is_image_file(Path("test.doc"))
        assert not selector.is_image_file(Path("test"))

    def test_find_images(self, sample_images):
        """Test image file discovery."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir)

        # Find all images with max depth
        found_images = selector.find_images(source_dir, 3)

        # Should find all 6 image files
        assert len(found_images) == 6
        assert all(selector.is_image_file(img) for img in found_images)

        # Check that non-image files are excluded
        found_names = {img.name for img in found_images}
        assert "document.txt" not in found_names
        assert "readme.md" not in found_names

    def test_find_images_depth_limit(self, sample_images):
        """Test image discovery with depth limit."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir)

        # Find images with depth limit of 1
        found_images = selector.find_images(source_dir, 1)

        # Should exclude deep/nested/deep1.jpeg (depth 2)
        found_names = {img.name for img in found_images}
        assert "deep1.jpeg" not in found_names
        assert len(found_images) == 5  # All except deep1.jpeg

    def test_get_subfolders(self, sample_images):
        """Test subfolder discovery."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir)

        subfolders = selector.get_subfolders(source_dir, 2)

        # Should find subfolder1, subfolder2, and deep (but not deep/nested at depth 2)
        subfolder_names = {folder.name for folder in subfolders}
        expected_names = {"subfolder1", "subfolder2", "deep", "nested"}

        # All expected names should be present
        assert expected_names.issubset(subfolder_names)

    def test_find_sidecars(self, sample_images):
        """Test sidecar file discovery."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir)

        # Test standard sidecar (.xmp for root1.jpg)
        root1_jpg = source_dir / "root1.jpg"
        sidecars = selector.find_sidecars(root1_jpg)
        assert len(sidecars) == 1
        assert sidecars[0].name == "root1.xmp"

        # Test yml sidecar
        sub1_jpg = source_dir / "subfolder1" / "sub1.jpg"
        sidecars = selector.find_sidecars(sub1_jpg)
        assert len(sidecars) == 1
        assert sidecars[0].name == "sub1.yml"

        # Test JSON sidecar (Google Takeout style)
        sub3_heic = source_dir / "subfolder2" / "sub3.heic"
        sidecars = selector.find_sidecars(sub3_heic)
        assert len(sidecars) == 1
        assert sidecars[0].name == "sub3_metadata.json"

        # Test file with no sidecars
        root2_png = source_dir / "root2.png"
        sidecars = selector.find_sidecars(root2_png)
        assert len(sidecars) == 0

    @patch("shutil.copy2")
    def test_copy_file_with_metadata_success(self, mock_copy, sample_images):
        """Test successful file copying with sidecars."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir)

        # Copy root1.jpg (has .xmp sidecar)
        root1_jpg = source_dir / "root1.jpg"
        result = selector.copy_file_with_metadata(root1_jpg)

        assert result is True
        assert selector.stats["copied_files"] == 1
        assert selector.stats["copied_sidecars"] == 1
        assert selector.stats["errors"] == 0

        # Should call copy2 twice (image + sidecar)
        assert mock_copy.call_count == 2

    @patch("shutil.copy2")
    def test_copy_file_with_metadata_error(self, mock_copy, sample_images):
        """Test file copying error handling."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir, debug=True)

        # Make copy2 raise an exception
        mock_copy.side_effect = PermissionError("Permission denied")

        root1_jpg = source_dir / "root1.jpg"
        result = selector.copy_file_with_metadata(root1_jpg)

        assert result is False
        assert selector.stats["copied_files"] == 0
        assert selector.stats["errors"] == 1

    def test_select_files_basic(self, sample_images):
        """Test basic file selection."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir, max_files=3)

        selected = selector.select_files()

        assert len(selected) <= 3
        assert len(selected) <= selector.max_files
        assert all(selector.is_image_file(img) for img in selected)
        assert selector.stats["selected_files"] == len(selected)

    def test_select_files_respects_limits(self, sample_images):
        """Test that file selection respects various limits."""
        source_dir, target_dir, image_files = sample_images

        # Test max_files limit
        selector = ImageSelector(source_dir, target_dir, max_files=2)
        selected = selector.select_files()
        assert len(selected) <= 2

        # Test that selection doesn't exceed total available
        selector = ImageSelector(source_dir, target_dir, max_files=100)
        selected = selector.select_files()
        assert len(selected) <= len(image_files)

        # Test that selection algorithm works with reasonable parameters
        selector = ImageSelector(
            source_dir, target_dir, max_files=3, max_folders=2, max_per_folder=2
        )
        selected = selector.select_files()
        assert len(selected) <= 3
        assert len(selected) > 0  # Should find some files

    def test_get_statistics(self, temp_dirs):
        """Test statistics retrieval."""
        source_dir, target_dir = temp_dirs
        selector = ImageSelector(source_dir, target_dir)

        stats = selector.get_statistics()

        assert isinstance(stats, dict)
        assert "total_images_found" in stats
        assert "selected_files" in stats
        assert "copied_files" in stats
        assert "copied_sidecars" in stats
        assert "errors" in stats
        assert "folders_processed" in stats

    def test_run_nonexistent_source(self, temp_dirs):
        """Test run with nonexistent source directory."""
        source_dir, target_dir = temp_dirs
        nonexistent = source_dir / "nonexistent"

        selector = ImageSelector(nonexistent, target_dir)

        with pytest.raises(FileNotFoundError):
            selector.run()

    def test_run_source_not_directory(self, temp_dirs):
        """Test run with source that's not a directory."""
        source_dir, target_dir = temp_dirs

        # Create a file instead of directory
        file_path = source_dir / "not_a_dir.txt"
        file_path.write_text("not a directory")

        selector = ImageSelector(file_path, target_dir)

        with pytest.raises(NotADirectoryError):
            selector.run()

    @patch("shutil.rmtree")
    def test_run_clean_target(self, mock_rmtree, sample_images):
        """Test run with clean_target option."""
        source_dir, target_dir, image_files = sample_images

        # Create something in target directory
        target_dir.mkdir(exist_ok=True)
        (target_dir / "existing_file.txt").write_text("existing content")

        selector = ImageSelector(source_dir, target_dir, clean_target=True, max_files=1)

        stats = selector.run()

        # Should have called rmtree to clean target
        mock_rmtree.assert_called_once_with(target_dir)
        assert isinstance(stats, dict)

    def test_run_no_images_found(self, temp_dirs):
        """Test run when no images are found."""
        source_dir, target_dir = temp_dirs

        # Create source with no images
        (source_dir / "document.txt").write_text("not an image")

        selector = ImageSelector(source_dir, target_dir)

        stats = selector.run()

        assert stats["selected_files"] == 0
        assert stats["copied_files"] == 0

    def test_run_successful_workflow(self, sample_images):
        """Test complete successful run workflow."""
        source_dir, target_dir, image_files = sample_images

        selector = ImageSelector(source_dir, target_dir, max_files=2, debug=True)

        stats = selector.run()

        # Check statistics
        assert isinstance(stats, dict)
        assert stats["selected_files"] <= 2
        assert stats["copied_files"] <= 2
        assert stats["copied_files"] == stats["selected_files"]

        # Check that target directory was created
        assert target_dir.exists()
        assert target_dir.is_dir()

    @patch("sys.path")
    def test_logger_fallback(self, mock_path, temp_dirs):
        """Test logger fallback when COMMON module is not available."""
        source_dir, target_dir = temp_dirs

        # Mock sys.path to simulate COMMON not being available
        with patch.dict("sys.modules", {"common.logging": None}):
            with patch("exif.image_selector.ScriptLogging", None):
                selector = ImageSelector(source_dir, target_dir, debug=True)

                # Should use fallback logger
                assert selector.logger is not None
                assert hasattr(selector.logger, "info")
                assert hasattr(selector.logger, "debug")
                assert hasattr(selector.logger, "error")

    def test_permission_error_handling(self, sample_images):
        """Test handling of permission errors during file operations."""
        source_dir, target_dir, image_files = sample_images
        selector = ImageSelector(source_dir, target_dir)

        # Mock os.walk to raise PermissionError
        with patch("os.walk") as mock_walk:
            mock_walk.side_effect = PermissionError("Permission denied")

            # Should handle the error gracefully
            images = selector.find_images(source_dir, 2)
            assert images == []  # Should return empty list, not crash


if __name__ == "__main__":
    pytest.main([__file__])
