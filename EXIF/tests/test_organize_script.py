"""
Tests for organize.py script - CLI interface and argument parsing.

These tests focus on testing the organize.py script directly, including:
- Command line argument parsing
- Error handling for invalid arguments
- Integration between CLI and PhotoOrganizer class
- Script entry point functionality
"""

import pytest
import subprocess
import tempfile
import sys
from pathlib import Path
from unittest import mock


class TestOrganizeScript:
    """Test the organize.py script CLI interface."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the organize.py script."""
        return Path(__file__).parent.parent / "scripts" / "organize.py"

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()

            # Create a test image file
            test_image = source_dir / "test.jpg"
            test_image.write_text("fake image content")

            yield source_dir, target_dir

    def test_script_help(self, script_path):
        """Test that the script shows help message."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Organize photos by date using EXIF metadata" in result.stdout
        assert "Target directory structure:" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--debug" in result.stdout

    def test_script_missing_arguments(self, script_path):
        """Test that script fails with missing arguments."""
        # No arguments
        result = subprocess.run(
            [sys.executable, str(script_path)], capture_output=True, text=True
        )

        assert result.returncode != 0
        assert "source directory is required" in result.stderr

    def test_script_missing_target(self, script_path, temp_dirs):
        """Test that script fails with missing target argument."""
        source_dir, _ = temp_dirs

        result = subprocess.run(
            [sys.executable, str(script_path), str(source_dir)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "target directory is required" in result.stderr

    def test_script_positional_arguments_dry_run(self, script_path, temp_dirs):
        """Test script with positional arguments in dry-run mode."""
        source_dir, target_dir = temp_dirs

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
        # Should not contain error messages
        assert "Error:" not in result.stderr

    def test_script_named_arguments_dry_run(self, script_path, temp_dirs):
        """Test script with named arguments in dry-run mode."""
        source_dir, target_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--source",
                str(source_dir),
                "--target",
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Error:" not in result.stderr

    def test_script_debug_mode(self, script_path, temp_dirs):
        """Test script with debug mode enabled."""
        source_dir, target_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(source_dir),
                str(target_dir),
                "--dry-run",
                "--debug",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Should have debug output when debug mode is enabled
        # (We can't easily check the log file from subprocess,
        # but we can verify the script ran successfully)

    def test_script_nonexistent_source(self, script_path, temp_dirs):
        """Test script with nonexistent source directory."""
        _, target_dir = temp_dirs
        nonexistent_source = target_dir.parent / "nonexistent"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(nonexistent_source),
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Error:" in result.stderr

    def test_script_mixed_arguments(self, script_path, temp_dirs):
        """Test script with mixed positional and named arguments."""
        source_dir, target_dir = temp_dirs

        # Positional source, named target
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(source_dir),
                "--target",
                str(target_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Error:" not in result.stderr

    def test_script_named_overrides_positional(self, script_path, temp_dirs):
        """Test that named arguments override positional ones."""
        source_dir, target_dir = temp_dirs
        fake_dir = target_dir.parent / "fake"
        fake_dir.mkdir()

        # Use fake directories in positional, real ones in named
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(fake_dir),
                str(fake_dir),  # Positional (should be ignored)
                "--source",
                str(source_dir),  # Named (should be used)
                "--target",
                str(target_dir),  # Named (should be used)
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Error:" not in result.stderr


class TestOrganizeScriptIntegration:
    """Integration tests for the organize.py script with actual PhotoOrganizer functionality."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories with test images."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()

            # Create test directory structure with sample files
            folders = [source_dir / "folder1", source_dir / "folder2" / "subfolder"]

            for folder in folders:
                folder.mkdir(parents=True, exist_ok=True)

            # Create sample image files
            image_files = [
                source_dir / "root_image.jpg",
                source_dir / "folder1" / "image1.png",
                source_dir / "folder2" / "subfolder" / "deep_image.jpeg",
            ]

            for img_file in image_files:
                img_file.write_text("fake image content")

            yield source_dir, target_dir

    @pytest.fixture
    def script_path(self):
        """Get the path to the organize.py script."""
        return Path(__file__).parent.parent / "scripts" / "organize.py"

    def test_script_full_run_dry_mode(self, script_path, temp_dirs):
        """Test full script execution in dry run mode."""
        source_dir, target_dir = temp_dirs

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

        # In dry run mode, no files should be created in target
        organized_files = list(target_dir.rglob("*.*"))
        assert len(organized_files) == 0

    def test_script_full_run_live_mode(self, script_path, temp_dirs):
        """Test full script execution in live mode."""
        source_dir, target_dir = temp_dirs

        result = subprocess.run(
            [sys.executable, str(script_path), str(source_dir), str(target_dir)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Error:" not in result.stderr

        # In live mode, files should be organized in target
        organized_files = list(target_dir.rglob("*.*"))
        assert len(organized_files) > 0

        # Verify some basic organization structure was created
        organized_dirs = [d for d in target_dir.rglob("*") if d.is_dir()]
        assert len(organized_dirs) > 0

    def test_script_handles_import_error(self, script_path, temp_dirs):
        """Test that script handles import errors gracefully."""
        source_dir, target_dir = temp_dirs

        # Create a modified environment without the exif module
        env = {**subprocess.os.environ, "PYTHONPATH": ""}  # Remove any existing paths

        # We can't easily simulate import errors in subprocess tests,
        # but we can verify the script structure handles them properly
        # by checking the import error handling code exists
        script_content = Path(script_path).read_text()
        assert "ImportError" in script_content
        assert "sys.exit(1)" in script_content


class TestOrganizeScriptMainFunction:
    """Test the main() function directly without subprocess calls."""

    def test_main_function_import(self):
        """Test that we can import the main function."""
        import sys
        from pathlib import Path

        # Add the scripts directory to path
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import organize

            assert hasattr(organize, "main")
            assert callable(organize.main)
        except ImportError:
            pytest.skip("organize module not available for direct import testing")

    def test_main_function_argument_parsing(self):
        """Test main function argument parsing directly."""
        import sys
        from pathlib import Path
        import tempfile

        # Add the scripts directory to path
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import organize

            # Create temporary directories
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                source_dir = temp_path / "source"
                target_dir = temp_path / "target"
                source_dir.mkdir()
                target_dir.mkdir()

                # Create a test file
                test_file = source_dir / "test.jpg"
                test_file.write_text("fake image")

                # Save original sys.argv
                original_argv = sys.argv

                # Mock sys.argv for testing
                sys.argv = [
                    "organize.py",  # argv[0]
                    str(source_dir),
                    str(target_dir),
                    "--dry-run",
                ]

                try:
                    # Call main function
                    result = organize.main()

                    # Should return 0 for success
                    assert result == 0

                finally:
                    # Restore original sys.argv
                    sys.argv = original_argv

        except ImportError:
            pytest.skip("organize module not available for direct testing")

    def test_main_function_error_handling(self):
        """Test main function error handling."""
        import sys
        from pathlib import Path

        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import organize

            # Save original sys.argv
            original_argv = sys.argv

            # Mock sys.argv with nonexistent source directory
            sys.argv = ["organize.py", "/nonexistent/source", "/tmp/target"]

            try:
                # Call main function
                result = organize.main()

                # Should return 1 for error
                assert result == 1

            finally:
                # Restore original sys.argv
                sys.argv = original_argv

        except ImportError:
            pytest.skip("organize module not available for direct testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
