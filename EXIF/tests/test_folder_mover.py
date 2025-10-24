"""
Tests for FolderMover class - Move files between folders based on CSV instructions.

Tests the core functionality of moving files from source to target folders
based on CSV instructions with proper validation and safety features.
"""

import tempfile
import csv
from pathlib import Path
import pytest

# Try to import the FolderMover class
try:
    import sys

    # Add project src directory to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from exif.folder_mover import FolderMover

    HAS_FOLDER_MOVER = True
except ImportError:
    HAS_FOLDER_MOVER = False


# Skip all tests if FolderMover is not available
pytestmark = pytest.mark.skipif(
    not HAS_FOLDER_MOVER, reason="FolderMover class not available for testing"
)


class TestFolderMover:
    """Test the FolderMover class directly."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test structure
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            csv_file = temp_path / "test.csv"

            source_dir.mkdir()
            target_dir.mkdir()

            # Create test files
            test_file1 = source_dir / "file1.txt"
            test_file2 = source_dir / "subdir" / "file2.txt"
            test_file2.parent.mkdir()

            test_file1.write_text("test content 1")
            test_file2.write_text("test content 2")

            yield source_dir, target_dir, csv_file

    def test_init(self, temp_dirs):
        """Test FolderMover initialization."""
        source_dir, target_dir, csv_file = temp_dirs

        mover = FolderMover(
            input_csv=str(csv_file), overwrite=True, dry_run=True, verbose=True
        )

        assert mover.input_csv == csv_file
        assert mover.overwrite is True
        assert mover.dry_run is True
        assert mover.verbose is True
        assert mover.stats == {
            "rows_processed": 0,
            "folders_moved": 0,
            "files_moved": 0,
            "errors": 0,
            "skipped": 0,
        }

    def test_validate_csv_file_missing(self, temp_dirs):
        """Test CSV validation with missing file."""
        source_dir, target_dir, csv_file = temp_dirs

        mover = FolderMover(input_csv=str(csv_file))
        result = mover.validate_csv_file()

        assert result is False

    def test_validate_csv_file_valid(self, temp_dirs):
        """Test CSV validation with valid file."""
        source_dir, target_dir, csv_file = temp_dirs

        # Create valid CSV
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Folder", "New Folder", "Target Folder"])
            writer.writerow([str(source_dir), "", str(target_dir)])

        mover = FolderMover(input_csv=str(csv_file))
        result = mover.validate_csv_file()

        assert result is True

    def test_validate_csv_file_missing_columns(self, temp_dirs):
        """Test CSV validation with missing required columns."""
        source_dir, target_dir, csv_file = temp_dirs

        # Create CSV with missing columns
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Folder", "New Folder"])  # Missing Target Folder
            writer.writerow([str(source_dir), ""])

        mover = FolderMover(input_csv=str(csv_file))
        result = mover.validate_csv_file()

        assert result is False

    def test_read_move_instructions_valid(self, temp_dirs):
        """Test reading valid move instructions."""
        source_dir, target_dir, csv_file = temp_dirs

        # Create valid CSV
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Folder", "New Folder", "Target Folder"])
            writer.writerow([str(source_dir), "", str(target_dir)])

        mover = FolderMover(input_csv=str(csv_file))
        instructions = mover.read_move_instructions()

        assert len(instructions) == 1
        assert instructions[0]["source_folder"] == str(source_dir)
        assert instructions[0]["target_folder"] == str(target_dir)
        assert mover.stats["rows_processed"] == 1

    def test_read_move_instructions_skip_empty_target(self, temp_dirs):
        """Test skipping rows with empty target folder."""
        source_dir, target_dir, csv_file = temp_dirs

        # Create CSV with empty target
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Folder", "New Folder", "Target Folder"])
            writer.writerow([str(source_dir), "", ""])  # Empty target

        mover = FolderMover(input_csv=str(csv_file))
        instructions = mover.read_move_instructions()

        assert len(instructions) == 0
        assert mover.stats["skipped"] == 1

    def test_validate_target_path_existing_dir(self, temp_dirs):
        """Test target path validation with existing directory."""
        source_dir, target_dir, csv_file = temp_dirs

        mover = FolderMover(input_csv=str(csv_file))
        result = mover.validate_target_path(target_dir, 1)

        assert result is True

    def test_validate_target_path_missing_parent_no_overwrite(self, temp_dirs):
        """Test target path validation with missing parent, no overwrite."""
        source_dir, target_dir, csv_file = temp_dirs

        nonexistent_target = target_dir / "missing_parent" / "target"

        mover = FolderMover(input_csv=str(csv_file), overwrite=False)
        result = mover.validate_target_path(nonexistent_target, 1)

        assert result is False

    def test_validate_target_path_missing_parent_with_overwrite(self, temp_dirs):
        """Test target path validation with missing parent, with overwrite."""
        source_dir, target_dir, csv_file = temp_dirs

        nonexistent_target = target_dir / "missing_parent" / "target"

        mover = FolderMover(input_csv=str(csv_file), overwrite=True)
        result = mover.validate_target_path(nonexistent_target, 1)

        assert result is True

    def test_move_folder_contents_dry_run(self, temp_dirs):
        """Test moving folder contents in dry run mode."""
        source_dir, target_dir, csv_file = temp_dirs

        mover = FolderMover(input_csv=str(csv_file), dry_run=True)
        files_moved, errors = mover.move_folder_contents(source_dir, target_dir, 1)

        assert files_moved == 2  # 2 test files
        assert errors == 0

        # Files should still exist in source (dry run)
        assert (source_dir / "file1.txt").exists()
        assert (source_dir / "subdir" / "file2.txt").exists()

    def test_move_folder_contents_dry_run_missing_parent_no_overwrite(self, temp_dirs):
        """Test dry run mode when parent directory doesn't exist and overwrite is False."""
        source_dir, target_dir, csv_file = temp_dirs

        # Create a target path with missing parent
        missing_parent_target = target_dir / "missing_parent" / "target"

        mover = FolderMover(input_csv=str(csv_file), dry_run=True, overwrite=False)
        files_moved, errors = mover.move_folder_contents(
            source_dir, missing_parent_target, 1
        )

        assert files_moved == 0  # No files should be "moved" due to error
        assert errors == 1  # Should have 1 error for missing parent

    def test_move_folder_contents_dry_run_missing_parent_with_overwrite(
        self, temp_dirs
    ):
        """Test dry run mode when parent directory doesn't exist but overwrite is True."""
        source_dir, target_dir, csv_file = temp_dirs

        # Create a target path with missing parent
        missing_parent_target = target_dir / "missing_parent" / "target"

        mover = FolderMover(input_csv=str(csv_file), dry_run=True, overwrite=True)
        files_moved, errors = mover.move_folder_contents(
            source_dir, missing_parent_target, 1
        )

        assert files_moved == 2  # Should report 2 files would be moved
        assert errors == 0  # No errors with overwrite=True

    def test_move_folder_contents_real_move(self, temp_dirs):
        """Test actually moving folder contents."""
        source_dir, target_dir, csv_file = temp_dirs

        mover = FolderMover(input_csv=str(csv_file), dry_run=False)
        files_moved, errors = mover.move_folder_contents(source_dir, target_dir, 1)

        assert files_moved == 2
        assert errors == 0

        # Files should be moved to target
        assert (target_dir / "file1.txt").exists()
        assert (target_dir / "subdir" / "file2.txt").exists()

        # Source files should be gone
        assert not (source_dir / "file1.txt").exists()
        assert not (source_dir / "subdir" / "file2.txt").exists()

    def test_process_moves_complete_workflow(self, temp_dirs):
        """Test the complete move workflow."""
        source_dir, target_dir, csv_file = temp_dirs

        # Create valid CSV
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Folder", "New Folder", "Target Folder"])
            writer.writerow([str(source_dir), "", str(target_dir / "moved")])

        mover = FolderMover(input_csv=str(csv_file), dry_run=True)
        stats = mover.process_moves()

        assert stats["rows_processed"] == 1
        assert stats["folders_moved"] == 1
        assert stats["files_moved"] == 2
        assert stats["errors"] == 0
        assert stats["skipped"] == 0

    def test_get_stats(self, temp_dirs):
        """Test getting statistics."""
        source_dir, target_dir, csv_file = temp_dirs

        mover = FolderMover(input_csv=str(csv_file))
        mover.stats["processed"] = 5

        stats = mover.get_stats()

        # Should return a copy
        assert stats is not mover.stats
        assert "processed" in stats

        # Modifying returned stats shouldn't affect original
        stats["test"] = "value"
        assert "test" not in mover.stats
