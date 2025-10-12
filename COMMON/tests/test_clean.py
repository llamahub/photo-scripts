#!/usr/bin/env python3
"""
Tests for the clean.py script.

Tests both the DirectoryCleaner class and the CLI interface.
"""

import sys
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest import mock

# Add the COMMON src path for imports
common_src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(common_src_path))

# Import the script
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import clean


class TestDirectoryCleaner:
    """Test the DirectoryCleaner class business logic."""

    @pytest.fixture
    def temp_dir_structure(self):
        """Create a temporary directory structure for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files and directories
            # Apple files
            (temp_path / ".DS_Store").touch()
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / ".DS_Store").touch()
            (temp_path / "._AppleDouble").touch()
            (temp_path / "subdir" / "._hidden").touch()

            # Log files
            (temp_path / "app.log").touch()
            (temp_path / "debug.log").touch()
            (temp_path / "subdir" / "error.log").touch()

            # Empty directories
            (temp_path / "empty1").mkdir()
            (temp_path / "empty2").mkdir()
            (temp_path / "subdir" / "empty_nested").mkdir()

            # Non-empty directory with normal file
            (temp_path / "normal_dir").mkdir()
            (temp_path / "normal_dir" / "file.txt").touch()

            yield temp_path

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return mock.MagicMock()

    def test_init(self, temp_dir_structure, mock_logger):
        """Test DirectoryCleaner initialization."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)

        assert cleaner.target_path == temp_dir_structure
        assert cleaner.logger == mock_logger
        assert cleaner.stats["mac_files_removed"] == 0
        assert cleaner.stats["log_files_removed"] == 0
        assert cleaner.stats["empty_dirs_removed"] == 0
        assert cleaner.stats["errors"] == 0

    def test_clean_mac_files_dry_run(self, temp_dir_structure, mock_logger):
        """Test cleaning Mac files in dry run mode."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)

        # Verify files exist before cleaning
        assert (temp_dir_structure / ".DS_Store").exists()
        assert (temp_dir_structure / "subdir" / ".DS_Store").exists()
        assert (temp_dir_structure / "._AppleDouble").exists()
        assert (temp_dir_structure / "subdir" / "._hidden").exists()

        cleaner.clean_mac_files(dry_run=True)

        # Files should still exist after dry run
        assert (temp_dir_structure / ".DS_Store").exists()
        assert (temp_dir_structure / "subdir" / ".DS_Store").exists()
        assert (temp_dir_structure / "._AppleDouble").exists()
        assert (temp_dir_structure / "subdir" / "._hidden").exists()

        # Should have counted the files
        assert cleaner.stats["mac_files_removed"] == 4
        assert cleaner.stats["errors"] == 0

    def test_clean_mac_files_actual(self, temp_dir_structure, mock_logger):
        """Test actually cleaning Mac files."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)

        # Verify files exist before cleaning
        assert (temp_dir_structure / ".DS_Store").exists()
        assert (temp_dir_structure / "._AppleDouble").exists()

        cleaner.clean_mac_files(dry_run=False)

        # Files should be removed
        assert not (temp_dir_structure / ".DS_Store").exists()
        assert not (temp_dir_structure / "subdir" / ".DS_Store").exists()
        assert not (temp_dir_structure / "._AppleDouble").exists()
        assert not (temp_dir_structure / "subdir" / "._hidden").exists()

        assert cleaner.stats["mac_files_removed"] == 4
        assert cleaner.stats["errors"] == 0

    def test_clean_log_files_dry_run(self, temp_dir_structure, mock_logger):
        """Test cleaning log files in dry run mode."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)

        # Verify log files exist
        assert (temp_dir_structure / "app.log").exists()
        assert (temp_dir_structure / "debug.log").exists()
        assert (temp_dir_structure / "subdir" / "error.log").exists()

        cleaner.clean_log_files(dry_run=True)

        # Files should still exist after dry run
        assert (temp_dir_structure / "app.log").exists()
        assert (temp_dir_structure / "debug.log").exists()
        assert (temp_dir_structure / "subdir" / "error.log").exists()

        assert cleaner.stats["log_files_removed"] == 3
        assert cleaner.stats["errors"] == 0

    def test_clean_log_files_actual(self, temp_dir_structure, mock_logger):
        """Test actually cleaning log files."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)

        cleaner.clean_log_files(dry_run=False)

        # Log files should be removed
        assert not (temp_dir_structure / "app.log").exists()
        assert not (temp_dir_structure / "debug.log").exists()
        assert not (temp_dir_structure / "subdir" / "error.log").exists()

        assert cleaner.stats["log_files_removed"] == 3
        assert cleaner.stats["errors"] == 0

    def test_clean_empty_directories_dry_run(self, temp_dir_structure, mock_logger):
        """Test cleaning empty directories in dry run mode."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)

        # Verify empty directories exist
        assert (temp_dir_structure / "empty1").exists()
        assert (temp_dir_structure / "empty2").exists()
        assert (temp_dir_structure / "subdir" / "empty_nested").exists()

        cleaner.clean_empty_directories(dry_run=True)

        # Directories should still exist after dry run
        assert (temp_dir_structure / "empty1").exists()
        assert (temp_dir_structure / "empty2").exists()
        assert (temp_dir_structure / "subdir" / "empty_nested").exists()

        assert cleaner.stats["empty_dirs_removed"] == 3
        assert cleaner.stats["errors"] == 0

    def test_clean_empty_directories_actual(self, temp_dir_structure, mock_logger):
        """Test actually cleaning empty directories."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)

        # Verify normal directory with files is preserved
        assert (temp_dir_structure / "normal_dir").exists()
        assert (temp_dir_structure / "normal_dir" / "file.txt").exists()

        cleaner.clean_empty_directories(dry_run=False)

        # Empty directories should be removed
        assert not (temp_dir_structure / "empty1").exists()
        assert not (temp_dir_structure / "empty2").exists()
        assert not (temp_dir_structure / "subdir" / "empty_nested").exists()

        # Non-empty directory should remain
        assert (temp_dir_structure / "normal_dir").exists()
        assert (temp_dir_structure / "normal_dir" / "file.txt").exists()

        assert cleaner.stats["empty_dirs_removed"] == 3
        assert cleaner.stats["errors"] == 0

    def test_clean_empty_directories_nested(self, mock_logger):
        """Test cleaning nested empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested empty directories
            nested_path = temp_path / "level1" / "level2" / "level3"
            nested_path.mkdir(parents=True)

            cleaner = clean.DirectoryCleaner(temp_path, mock_logger)
            cleaner.clean_empty_directories(dry_run=False)

            # All nested empty directories should be removed
            assert not nested_path.exists()
            assert not (temp_path / "level1" / "level2").exists()
            assert not (temp_path / "level1").exists()

            # Should count all removed directories
            assert cleaner.stats["empty_dirs_removed"] == 3

    @mock.patch("pathlib.Path.unlink")
    def test_clean_mac_files_permission_error(
        self, mock_unlink, temp_dir_structure, mock_logger
    ):
        """Test handling permission errors when removing Mac files."""
        mock_unlink.side_effect = PermissionError("Permission denied")

        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)
        cleaner.clean_mac_files(dry_run=False)

        # Should log errors but continue
        assert cleaner.stats["errors"] > 0
        mock_logger.error.assert_called()

    def test_print_summary(self, temp_dir_structure, mock_logger):
        """Test printing cleaning summary."""
        cleaner = clean.DirectoryCleaner(temp_dir_structure, mock_logger)
        cleaner.stats["mac_files_removed"] = 5
        cleaner.stats["log_files_removed"] = 3
        cleaner.stats["empty_dirs_removed"] = 2
        cleaner.stats["errors"] = 1

        cleaner.print_summary()

        # Verify summary was logged
        mock_logger.info.assert_any_call("CLEANING SUMMARY")
        mock_logger.info.assert_any_call("Apple files removed: 5")
        mock_logger.info.assert_any_call("Log files removed: 3")
        mock_logger.info.assert_any_call("Empty directories removed: 2")
        mock_logger.warning.assert_any_call("Errors encountered: 1")


class TestCleanScript:
    """Test the clean.py script CLI interface."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the clean script."""
        return Path(__file__).parent.parent / "scripts" / "clean.py"

    @pytest.fixture
    def temp_test_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / ".DS_Store").touch()
            (temp_path / "test.log").touch()
            (temp_path / "empty_dir").mkdir()

            yield temp_path

    def test_script_help(self, script_path):
        """Test script help message."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Clean unwanted files and empty directories" in result.stdout
        assert "--mac" in result.stdout
        assert "--empty" in result.stdout
        assert "--log" in result.stdout
        assert "--dry-run" in result.stdout

    def test_script_missing_target(self, script_path):
        """Test script with missing target argument."""
        result = subprocess.run(
            [sys.executable, str(script_path)], capture_output=True, text=True
        )

        assert result.returncode != 0
        assert "required" in result.stderr.lower()

    def test_script_nonexistent_target(self, script_path):
        """Test script with nonexistent target directory."""
        result = subprocess.run(
            [sys.executable, str(script_path), "/nonexistent/path", "--mac"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "does not exist" in result.stderr

    def test_script_no_cleaning_options(self, script_path, temp_test_dir):
        """Test script with no cleaning options specified."""
        result = subprocess.run(
            [sys.executable, str(script_path), str(temp_test_dir)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "No cleaning options specified" in result.stderr

    def test_script_mac_cleaning_dry_run(self, script_path, temp_test_dir):
        """Test script with Mac file cleaning in dry run mode."""
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(temp_test_dir),
                "--mac",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "DRY RUN MODE" in result.stderr
        assert "Would remove" in result.stderr
        assert ".DS_Store" in result.stderr

        # File should still exist
        assert (temp_test_dir / ".DS_Store").exists()

    def test_script_log_cleaning_actual(self, script_path, temp_test_dir):
        """Test script with actual log file cleaning."""
        result = subprocess.run(
            [sys.executable, str(script_path), str(temp_test_dir), "--log"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Cleaning completed successfully" in result.stderr

        # Log file should be removed
        assert not (temp_test_dir / "test.log").exists()

    def test_script_empty_dirs_cleaning(self, script_path, temp_test_dir):
        """Test script with empty directory cleaning."""
        result = subprocess.run(
            [sys.executable, str(script_path), str(temp_test_dir), "--empty"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Cleaning completed successfully" in result.stderr

        # Empty directory should be removed
        assert not (temp_test_dir / "empty_dir").exists()

    def test_script_all_cleaning_options(self, script_path, temp_test_dir):
        """Test script with all cleaning options."""
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(temp_test_dir),
                "--mac",
                "--log",
                "--empty",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "DRY RUN MODE" in result.stderr
        assert "CLEANING SUMMARY" in result.stderr

    def test_script_debug_mode(self, script_path, temp_test_dir):
        """Test script with debug mode enabled."""
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(temp_test_dir),
                "--mac",
                "--debug",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Debug mode should produce more verbose output
        assert "DEBUG" in result.stderr or len(result.stderr) > 200

    def test_script_main_function_direct(self, temp_test_dir):
        """Test calling main function directly."""
        # Save original argv
        original_argv = sys.argv

        try:
            # Test successful execution
            sys.argv = ["clean.py", str(temp_test_dir), "--mac", "--dry-run"]
            result = clean.main()
            assert result == 0

            # Test missing options
            sys.argv = ["clean.py", str(temp_test_dir)]
            result = clean.main()
            assert result == 1

            # Test nonexistent path
            sys.argv = ["clean.py", "/nonexistent", "--mac"]
            result = clean.main()
            assert result == 1

        finally:
            sys.argv = original_argv

    @mock.patch("clean.DirectoryCleaner")
    def test_script_keyboard_interrupt(self, mock_cleaner_class, temp_test_dir):
        """Test script handling of keyboard interrupt."""
        mock_cleaner = mock.MagicMock()
        mock_cleaner_class.return_value = mock_cleaner
        mock_cleaner.clean_mac_files.side_effect = KeyboardInterrupt()

        original_argv = sys.argv
        try:
            sys.argv = ["clean.py", str(temp_test_dir), "--mac"]
            result = clean.main()
            assert result == 1
        finally:
            sys.argv = original_argv

    @mock.patch("clean.DirectoryCleaner")
    def test_script_unexpected_error(self, mock_cleaner_class, temp_test_dir):
        """Test script handling of unexpected errors."""
        mock_cleaner = mock.MagicMock()
        mock_cleaner_class.return_value = mock_cleaner
        mock_cleaner.clean_mac_files.side_effect = Exception("Unexpected error")

        original_argv = sys.argv
        try:
            sys.argv = ["clean.py", str(temp_test_dir), "--mac"]
            result = clean.main()
            assert result == 1
        finally:
            sys.argv = original_argv


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
