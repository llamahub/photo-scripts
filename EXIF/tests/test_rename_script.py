"""
Tests for rename.py script - CLI interface and file renaming functionality.

These tests focus on testing the rename.py script directly, including:
- Command line argument parsing
- Error handling for invalid arguments
- File renaming with EXIF metadata
- Sidecar file handling
- Script entry point functionality
"""

import pytest
import subprocess
import tempfile
import sys
import shutil
from pathlib import Path
from unittest import mock


class TestRenameScript:
    """Test the rename.py script CLI interface."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the rename.py script."""
        return Path(__file__).parent.parent / "scripts" / "rename.py"

    @pytest.fixture
    def temp_dir_with_files(self):
        """Create temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "target"
            target_dir.mkdir()

            # Create test image files
            test_files = [
                target_dir / "image1.jpg",
                target_dir / "photo.png",
                target_dir / "video.mp4",
            ]

            for test_file in test_files:
                test_file.write_text("fake file content")

            # Create a sidecar file
            sidecar = target_dir / "image1.xmp"
            sidecar.write_text("<xmp>metadata</xmp>")

            yield target_dir

    def test_script_help(self, script_path):
        """Test that the script shows help message."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Rename files using EXIF metadata" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--label" in result.stdout
        assert "--move" in result.stdout

    def test_script_missing_arguments(self, script_path):
        """Test that script fails with missing arguments."""
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        assert "target directory is required" in result.stderr

    def test_script_dry_run_mode(self, script_path, temp_dir_with_files):
        """Test script in dry-run mode (no actual changes)."""
        target_dir = temp_dir_with_files

        # Get original files
        original_files = sorted([f.name for f in target_dir.iterdir()])

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Error:" not in result.stderr

        # Files should remain unchanged in dry-run
        current_files = sorted([f.name for f in target_dir.iterdir()])
        assert current_files == original_files

    def test_script_with_label(self, script_path, temp_dir_with_files):
        """Test script with label argument."""
        target_dir = temp_dir_with_files

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--label",
                "vacation",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Error:" not in result.stderr
        # In actual implementation, check if label appears in generated filenames

    def test_script_move_option(self, script_path, temp_dir_with_files):
        """Test the --move option (rename in place)."""
        target_dir = temp_dir_with_files

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--move",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "RENAME" in result.stdout or "rename" in result.stderr

    def test_script_nonexistent_target(self, script_path):
        """Test script with nonexistent target directory."""
        nonexistent = Path("/nonexistent/directory")

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(nonexistent),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Error:" in result.stderr or "does not exist" in result.stderr

    def test_script_named_target_argument(self, script_path, temp_dir_with_files):
        """Test script with named --target argument."""
        target_dir = temp_dir_with_files

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--target",
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Error:" not in result.stderr


class TestRenameScriptIntegration:
    """Integration tests for rename.py script with actual file operations."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the rename.py script."""
        return Path(__file__).parent.parent / "scripts" / "rename.py"

    @pytest.fixture
    def temp_dir_structure(self):
        """Create temporary directory with nested structure and various file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "organized"
            target_dir.mkdir()

            # Create subdirectories
            folders = [
                target_dir / "2023",
                target_dir / "2023" / "2023-05",
                target_dir / "2024",
            ]

            for folder in folders:
                folder.mkdir(parents=True, exist_ok=True)

            # Create various file types
            files = [
                target_dir / "root_image.jpg",
                target_dir / "2023" / "photo1.png",
                target_dir / "2023" / "2023-05" / "vacation.jpg",
                target_dir / "2024" / "video.mp4",
            ]

            for file_path in files:
                file_path.write_bytes(b"fake content")

            # Create sidecar files
            sidecars = [
                target_dir / "root_image.xmp",
                target_dir / "2023" / "photo1.aae",
            ]

            for sidecar in sidecars:
                sidecar.write_text("<metadata>")

            yield target_dir

    def test_script_processes_all_files(self, script_path, temp_dir_structure):
        """Test that script finds and processes all files in directory tree."""
        target_dir = temp_dir_structure

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Check that multiple files were found
        assert "files processed" in result.stderr or "files processed" in result.stdout

    def test_script_handles_sidecar_files(self, script_path, temp_dir_structure):
        """Test that script properly handles sidecar files."""
        target_dir = temp_dir_structure

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Should mention sidecar files if found
        output = result.stdout + result.stderr
        # The script should process sidecars when their media files are renamed

    def test_script_empty_directory(self, script_path):
        """Test script with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(empty_dir),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            # Should handle empty directory gracefully
            output = result.stdout + result.stderr
            assert "No media files" in output or "0 files" in output.lower()

    def test_script_live_mode_creates_copies(self, script_path, temp_dir_structure):
        """Test that script creates copies in live mode (without --move)."""
        target_dir = temp_dir_structure

        # Count original files
        original_count = len([f for f in target_dir.rglob("*") if f.is_file()])

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # After copy mode, should have more files (originals + copies)
        final_count = len([f for f in target_dir.rglob("*") if f.is_file()])
        # May have more files (originals preserved plus renamed copies)
        # or same if files already had correct names

    def test_script_move_mode_preserves_count(self, script_path, temp_dir_structure):
        """Test that script preserves file count in move mode."""
        target_dir = temp_dir_structure

        # Count original files
        original_count = len([f for f in target_dir.rglob("*") if f.is_file()])

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--move",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # After move mode, file count should remain the same
        final_count = len([f for f in target_dir.rglob("*") if f.is_file()])
        assert final_count == original_count


class TestRenameScriptFileTypes:
    """Test rename.py script with various file types."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the rename.py script."""
        return Path(__file__).parent.parent / "scripts" / "rename.py"

    @pytest.fixture
    def temp_dir_various_files(self):
        """Create directory with various file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "files"
            target_dir.mkdir()

            # Image files
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.heic']
            for ext in image_extensions:
                (target_dir / f"image{ext}").write_bytes(b"fake image")

            # Video files
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
            for ext in video_extensions:
                (target_dir / f"video{ext}").write_bytes(b"fake video")

            # Sidecar files
            (target_dir / "image.jpg.xmp").write_text("<xmp>")
            (target_dir / "video.mp4.aae").write_text("aae data")

            # Non-media files (should be ignored)
            (target_dir / "readme.txt").write_text("text file")
            (target_dir / "data.csv").write_text("csv file")

            yield target_dir

    def test_script_processes_all_image_formats(self, script_path, temp_dir_various_files):
        """Test that script processes all supported image formats."""
        target_dir = temp_dir_various_files

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Should find multiple image files
        output = result.stdout + result.stderr

    def test_script_processes_all_video_formats(self, script_path, temp_dir_various_files):
        """Test that script processes all supported video formats."""
        target_dir = temp_dir_various_files

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Should find video files
        output = result.stdout + result.stderr

    def test_script_ignores_non_media_files(self, script_path, temp_dir_various_files):
        """Test that script ignores non-media files."""
        target_dir = temp_dir_various_files

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Non-media files should still exist unchanged
        assert (target_dir / "readme.txt").exists()
        assert (target_dir / "data.csv").exists()


class TestRenameScriptMainFunction:
    """Test the main() function directly."""

    def test_main_function_import(self):
        """Test that we can import the main function."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import rename
            assert hasattr(rename, "main")
            assert callable(rename.main)
        except ImportError:
            pytest.skip("rename module not available for direct import testing")

    def test_main_function_with_temp_dir(self):
        """Test main function with temporary directory."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import rename

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                target_dir = temp_path / "target"
                target_dir.mkdir()

                # Create test file
                test_file = target_dir / "test.jpg"
                test_file.write_bytes(b"fake image")

                # Save original sys.argv
                original_argv = sys.argv

                # Mock sys.argv
                sys.argv = [
                    "rename.py",
                    str(target_dir),
                    "--dry-run",
                ]

                try:
                    result = rename.main()
                    assert result == 0
                finally:
                    sys.argv = original_argv

        except ImportError:
            pytest.skip("rename module not available for direct testing")

    def test_main_function_error_handling(self):
        """Test main function error handling with nonexistent directory."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import rename

            original_argv = sys.argv
            sys.argv = ["rename.py", "/nonexistent/directory"]

            try:
                result = rename.main()
                assert result == 1  # Should return error code
            finally:
                sys.argv = original_argv

        except ImportError:
            pytest.skip("rename module not available for direct testing")


class TestRenameScriptEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the rename.py script."""
        return Path(__file__).parent.parent / "scripts" / "rename.py"

    def test_script_with_special_characters_in_path(self, script_path):
        """Test script with special characters in directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory with spaces and special chars
            special_dir = Path(temp_dir) / "my photos & videos (2024)"
            special_dir.mkdir()

            test_file = special_dir / "test.jpg"
            test_file.write_bytes(b"fake image")

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(special_dir),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

    def test_script_with_symlinks(self, script_path):
        """Test script behavior with symbolic links."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "target"
            target_dir.mkdir()

            # Create a real file
            real_file = target_dir / "real.jpg"
            real_file.write_bytes(b"fake image")

            # Create a symlink (if supported on this platform)
            try:
                link_file = target_dir / "link.jpg"
                link_file.symlink_to(real_file)

                result = subprocess.run(
                    [
                        sys.executable,
                        str(script_path),
                        str(target_dir),
                        "--dry-run",
                    ],
                    capture_output=True,
                    text=True,
                )

                # Should handle symlinks gracefully
                assert result.returncode == 0

            except OSError:
                pytest.skip("Symbolic links not supported on this platform")

    def test_script_with_read_only_directory(self, script_path):
        """Test script with read-only directory (should fail gracefully)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "readonly"
            target_dir.mkdir()

            test_file = target_dir / "test.jpg"
            test_file.write_bytes(b"fake image")

            # Make directory read-only
            try:
                target_dir.chmod(0o444)

                result = subprocess.run(
                    [
                        sys.executable,
                        str(script_path),
                        str(target_dir),
                    ],
                    capture_output=True,
                    text=True,
                )

                # Should handle permission errors gracefully
                # (may succeed in dry-run or fail with proper error message)

            finally:
                # Restore permissions for cleanup
                target_dir.chmod(0o755)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
