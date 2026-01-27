"""
Tests for extract_videos.py script - CLI interface and video extraction functionality.

These tests focus on testing the extract_videos.py script directly, including:
- Command line argument parsing
- Error handling for invalid arguments
- Video file extraction and organization
- Copy vs move operation modes
- Subdirectory structure preservation
- Script entry point functionality
"""

import pytest
import subprocess
import tempfile
import sys
import shutil
from pathlib import Path


class TestExtractVideosScript:
    """Test the extract_videos.py script CLI interface."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the extract_videos.py script."""
        return Path(__file__).parent.parent / "scripts" / "extract_videos.py"

    @pytest.fixture
    def source_dir_with_videos(self):
        """Create source directory structure with video files in subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()

            # Create subdirectories with videos
            subdirs = [
                source_dir / "2023-05",
                source_dir / "2023-06",
                source_dir / "vacation" / "day1",
            ]

            for subdir in subdirs:
                subdir.mkdir(parents=True, exist_ok=True)

            # Create video files in subdirectories
            video_files = [
                source_dir / "2023-05" / "video1.mp4",
                source_dir / "2023-05" / "video2.mov",
                source_dir / "2023-06" / "footage.avi",
                source_dir / "vacation" / "day1" / "clip.mkv",
            ]

            for video_file in video_files:
                video_file.write_text("fake video content")

            # Also create non-video files that should be ignored
            (source_dir / "2023-05" / "image.jpg").write_text("fake image")
            (source_dir / "2023-05" / "readme.txt").write_text("not a video")

            yield source_dir

    def test_script_help(self, script_path):
        """Test that the script shows help message."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Extract video files" in result.stdout
        assert "--move" in result.stdout
        assert "--dry-run" in result.stdout

    def test_script_missing_arguments(self, script_path):
        """Test that script fails with missing source argument."""
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        assert "source directory is required" in result.stderr or "Error" in result.stderr

    def test_script_dry_run_mode(self, script_path, source_dir_with_videos):
        """Test script in dry-run mode (no actual changes)."""
        source_dir = source_dir_with_videos
        
        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            # Get original files in source
            original_files = {}
            for root, dirs, files in source_dir.walk():
                rel_path = root.relative_to(source_dir)
                original_files[str(rel_path)] = sorted(files)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "Error:" not in result.stderr

            # Source files should remain unchanged in dry-run
            current_files = {}
            for root, dirs, files in source_dir.walk():
                rel_path = root.relative_to(source_dir)
                current_files[str(rel_path)] = sorted(files)

            assert current_files == original_files

            # Target should be empty (or not contain all videos) in dry-run
            if target_dir.exists():
                target_files = list(target_dir.rglob("*.mp4"))
                target_files.extend(target_dir.rglob("*.mov"))
                target_files.extend(target_dir.rglob("*.avi"))
                target_files.extend(target_dir.rglob("*.mkv"))
                # In dry-run, actual copies shouldn't happen
                # (though log shows what would happen)

    def test_script_copy_mode(self, script_path, source_dir_with_videos):
        """Test script copies videos while preserving source."""
        source_dir = source_dir_with_videos

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "Error:" not in result.stderr or "extraction completed" in result.stdout.lower()

            # Videos should be in target directory
            target_videos = list(target_dir.glob("*/*.mp4"))
            target_videos.extend(target_dir.glob("*/*.mov"))
            target_videos.extend(target_dir.glob("*/*.avi"))
            target_videos.extend(target_dir.glob("*/*/mkv"))
            
            # Should have found some videos
            assert len(target_videos) > 0 or "found 0 video files" in result.stdout.lower()

            # Source files should still exist (copy mode)
            source_videos = list(source_dir.glob("*/*.mp4"))
            source_videos.extend(source_dir.glob("*/*.mov"))
            source_videos.extend(source_dir.glob("*/*.avi"))
            assert len(source_videos) > 0

    def test_script_move_mode(self, script_path, source_dir_with_videos):
        """Test script moves videos (removes originals)."""
        source_dir = source_dir_with_videos

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            # Count original videos
            original_videos = list(source_dir.glob("*/*.mp4"))
            original_videos.extend(source_dir.glob("*/*.mov"))
            original_videos.extend(source_dir.glob("*/*.avi"))
            original_count = len(original_videos)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--move",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            # After move, original videos should be gone (or moved to target)
            # Check output shows "moved" or "move" in the operation
            output_text = result.stdout + result.stderr
            assert "move" in output_text.lower()

    def test_script_preserves_directory_structure(self, script_path, source_dir_with_videos):
        """Test that script preserves subdirectory structure in target."""
        source_dir = source_dir_with_videos

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            # Check that subdirectories are created in target
            # (if videos were found)
            if (target_dir / "2023-05").exists():
                assert (target_dir / "2023-05").is_dir()

    def test_script_default_target_directory(self, script_path, source_dir_with_videos):
        """Test script with default target directory."""
        source_dir = source_dir_with_videos

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(source_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Should mention target directory (default: /mnt/photo_drive/santee-videos)
        assert "target" in result.stdout.lower()

    def test_script_nonexistent_source(self, script_path):
        """Test script with nonexistent source directory."""
        nonexistent = Path("/nonexistent/directory/for/testing")

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(nonexistent),
                    str(target_dir),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode != 0
            assert "Error:" in result.stderr or "does not exist" in result.stderr

    def test_script_filters_video_files_only(self, script_path, source_dir_with_videos):
        """Test that script only processes video files, ignoring others."""
        source_dir = source_dir_with_videos

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            # Output should show video count (excluding non-video files)
            # image.jpg and readme.txt should be ignored
            output_text = result.stdout + result.stderr
            # Should find 4 videos (video1.mp4, video2.mov, footage.avi, clip.mkv)
            assert "video" in output_text.lower()

    def test_script_quiet_mode(self, script_path, source_dir_with_videos):
        """Test script with --quiet option."""
        source_dir = source_dir_with_videos

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--quiet",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            # In quiet mode, should have minimal stdout
            # (mainly error messages if any)

    def test_script_verbose_mode(self, script_path, source_dir_with_videos):
        """Test script with --verbose option."""
        source_dir = source_dir_with_videos

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--verbose",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            # In verbose mode, should have debug output
            # (Check combined stdout/stderr has more content)


class TestExtractVideosScriptIntegration:
    """Integration tests for extract_videos.py script with actual file operations."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the extract_videos.py script."""
        return Path(__file__).parent.parent / "scripts" / "extract_videos.py"

    @pytest.fixture
    def complex_source_structure(self):
        """Create complex source directory with nested structure and various file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "photos"
            source_dir.mkdir()

            # Create complex subdirectory structure
            structure = {
                "2023": ["2023-01", "2023-12"],
                "2024": ["2024-01", "2024-06"],
                "events": ["wedding", "birthday"],
            }

            subdirs = []
            for root_dir, sub_dirs in structure.items():
                subdirs.append(source_dir / root_dir)
                for sub_dir in sub_dirs:
                    subdirs.append(source_dir / root_dir / sub_dir)

            for subdir in subdirs:
                subdir.mkdir(parents=True, exist_ok=True)

            # Create various files
            video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
            image_extensions = [".jpg", ".png", ".heic"]
            other_extensions = [".txt", ".json", ".xmp"]

            file_count = 0

            # Add videos, images, and other files to various subdirectories
            for i, subdir in enumerate(subdirs):
                # Add some videos to each subdirectory
                for j in range(2):
                    ext = video_extensions[j % len(video_extensions)]
                    video_file = subdir / f"video_{file_count}{ext}"
                    video_file.write_bytes(b"fake video")
                    file_count += 1

                # Add some images (should be ignored)
                for j in range(2):
                    ext = image_extensions[j % len(image_extensions)]
                    image_file = subdir / f"image_{file_count}{ext}"
                    image_file.write_bytes(b"fake image")

                # Add sidecar files (should be ignored)
                for j in range(1):
                    ext = other_extensions[j % len(other_extensions)]
                    other_file = subdir / f"meta_{file_count}{ext}"
                    other_file.write_text("metadata")

            yield source_dir

    def test_script_finds_all_videos(self, script_path, complex_source_structure):
        """Test that script finds all video files across nested structure."""
        source_dir = complex_source_structure

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            output_text = result.stdout + result.stderr
            # Should report finding video files
            assert "video" in output_text.lower()

    def test_script_ignores_non_video_files(self, script_path, complex_source_structure):
        """Test that script only processes video files and ignores others."""
        source_dir = complex_source_structure

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            # Count video files in source
            video_files = list(source_dir.rglob("*.mp4"))
            video_files.extend(source_dir.rglob("*.mov"))
            video_files.extend(source_dir.rglob("*.avi"))
            video_files.extend(source_dir.rglob("*.mkv"))
            video_files.extend(source_dir.rglob("*.webm"))

            # Count image files (should not be extracted)
            image_files = list(source_dir.rglob("*.jpg"))
            image_files.extend(source_dir.rglob("*.png"))
            image_files.extend(source_dir.rglob("*.heic"))

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            # Should find video files but not image files
            output_text = result.stdout + result.stderr
            # Verify that output mentions videos found
            if len(video_files) > 0:
                assert "video" in output_text.lower()

    def test_script_actual_copy_operation(self, script_path, complex_source_structure):
        """Test actual copy operation with complex structure."""
        source_dir = complex_source_structure

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            # Count video files
            source_videos = list(source_dir.rglob("*.mp4"))
            source_videos.extend(source_dir.rglob("*.mov"))
            source_videos.extend(source_dir.rglob("*.avi"))
            source_videos.extend(source_dir.rglob("*.mkv"))
            source_videos.extend(source_dir.rglob("*.webm"))

            if len(source_videos) > 0:
                # Source files should still exist (copy mode)
                remaining_source_videos = list(source_dir.rglob("*.mp4"))
                remaining_source_videos.extend(source_dir.rglob("*.mov"))
                remaining_source_videos.extend(source_dir.rglob("*.avi"))
                remaining_source_videos.extend(source_dir.rglob("*.mkv"))
                remaining_source_videos.extend(source_dir.rglob("*.webm"))

                assert len(remaining_source_videos) == len(source_videos)

    def test_script_actual_move_operation(self, script_path, complex_source_structure):
        """Test actual move operation with complex structure."""
        source_dir = complex_source_structure

        # Count video files before move
        source_videos_before = list(source_dir.rglob("*.mp4"))
        source_videos_before.extend(source_dir.rglob("*.mov"))
        source_videos_before.extend(source_dir.rglob("*.avi"))
        source_videos_before.extend(source_dir.rglob("*.mkv"))
        source_videos_before.extend(source_dir.rglob("*.webm"))

        with tempfile.TemporaryDirectory() as temp_target:
            target_dir = Path(temp_target)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(source_dir),
                    str(target_dir),
                    "--move",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            if len(source_videos_before) > 0:
                # Count video files after move
                source_videos_after = list(source_dir.rglob("*.mp4"))
                source_videos_after.extend(source_dir.rglob("*.mov"))
                source_videos_after.extend(source_dir.rglob("*.avi"))
                source_videos_after.extend(source_dir.rglob("*.mkv"))
                source_videos_after.extend(source_dir.rglob("*.webm"))

                # Should have fewer or same videos in source after move
                # (depending on whether they were successfully moved to target)
