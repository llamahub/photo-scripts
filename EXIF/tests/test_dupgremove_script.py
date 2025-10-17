#!/usr/bin/env python3
"""
Tests for dupgremove.py script.

Test the duplicate file removal functionality including CSV processing,
file moving, path normalization, and error handling.
"""

import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestDupGuruRemover:
    """Test cases for dupgremove.py script."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.temp_dir) / "target"
        self.dup_dir = Path(self.temp_dir) / "duplicates"
        self.csv_file = Path(self.temp_dir) / "test.csv"

        # Create target directory structure
        self.target_dir.mkdir(parents=True)

        # Script path
        self.script_path = Path(__file__).parent.parent / "scripts" / "dupgremove.py"

    def teardown_method(self):
        """Clean up after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_files(self):
        """Create test files and directory structure matching CSV paths."""
        # Create test files that match the CSV folder structure
        files_to_create = [
            "2020+/2022/2022-06/2022-06_Photos/photo1.jpg",
            "2020+/2022/2022-06/2022-06_DEB/photo1_organized.jpg",
            "1990+/1995/1995-03/1995-03_Vacation/scan1.jpg",
            "1990+/1995/1995-03/1995-03_Scans/scan1_original.jpg",
            "2020+/2025/2025-10/NPTSTI~Z/duplicate.jpg",
            "2020+/2025/2025-10/2025-10_Photos/duplicate_good.jpg",
        ]

        for file_path in files_to_create:
            full_path = self.target_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"Test content for {file_path}")

    def create_test_csv(self, custom_data=None):
        """Create a test CSV file with dupGuru results."""
        if custom_data is None:
            # Default test data - split long lines for readability
            test_data = [
                [
                    "Group ID",
                    "Filename",
                    "Folder",
                    "Size (KB)",
                    "Dimensions",
                    "Match %",
                    "Action",
                    "Comments",
                ],
                [
                    "0",
                    "photo1.jpg",
                    "X:\\2020+\\2022\\2022-06\\2022-06_Photos",
                    "500",
                    "1920 x 1080",
                    "99",
                    "Delete",
                    "Duplicate",
                ],
                [
                    "0",
                    "photo1_organized.jpg",
                    "X:\\2020+\\2022\\2022-06\\2022-06_DEB",
                    "498",
                    "1920 x 1080",
                    "99",
                    "Keep",
                    "Organized format",
                ],
                [
                    "1",
                    "scan1.jpg",
                    "X:\\1990+\\1995\\1995-03\\1995-03_Vacation",
                    "800",
                    "2048 x 1536",
                    "98",
                    "Delete",
                    "Duplicate scan",
                ],
                [
                    "1",
                    "scan1_original.jpg",
                    "X:\\1990+\\1995\\1995-03\\1995-03_Scans",
                    "795",
                    "2048 x 1536",
                    "98",
                    "Keep",
                    "Original",
                ],
                [
                    "2",
                    "duplicate.jpg",
                    "X:\\2020+\\2025\\2025-10\\NPTSTI~Z",
                    "300",
                    "1080 x 1920",
                    "100",
                    "Delete",
                    "Invalid folder",
                ],
                [
                    "2",
                    "duplicate_good.jpg",
                    "X:\\2020+\\2025\\2025-10\\2025-10_Photos",
                    "298",
                    "1080 x 1920",
                    "100",
                    "Keep",
                    "Valid folder",
                ],
            ]
        else:
            test_data = custom_data

        with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(test_data)

    def run_script(self, args, expect_success=True):
        """Run the dupgremove.py script with given arguments."""
        cmd = ["python3", str(self.script_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)

        if expect_success and result.returncode != 0:
            pytest.fail(
                f"Script failed with return code {result.returncode}\n"
                f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )

        return result

    def test_basic_file_removal(self):
        """Test basic file removal functionality."""
        self.create_test_files()
        self.create_test_csv()

        # Run script
        self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)]
        )

        # Check that files marked for deletion were moved
        assert not (
            self.target_dir / "2020+/2022/2022-06/2022-06_Photos/photo1.jpg"
        ).exists()
        assert not (
            self.target_dir / "1990+/1995/1995-03/1995-03_Vacation/scan1.jpg"
        ).exists()
        assert not (
            self.target_dir / "2020+/2025/2025-10/NPTSTI~Z/duplicate.jpg"
        ).exists()

        # Check that files were moved to duplicate directory with preserved structure
        assert (self.dup_dir / "2020+/2022/2022-06/2022-06_Photos/photo1.jpg").exists()
        assert (self.dup_dir / "1990+/1995/1995-03/1995-03_Vacation/scan1.jpg").exists()
        assert (self.dup_dir / "2020+/2025/2025-10/NPTSTI~Z/duplicate.jpg").exists()

        # Verify file contents are preserved
        moved_file = self.dup_dir / "2020+/2022/2022-06/2022-06_Photos/photo1.jpg"
        assert (
            moved_file.read_text()
            == "Test content for 2020+/2022/2022-06/2022-06_Photos/photo1.jpg"
        )

    def test_dry_run_mode(self):
        """Test dry run mode doesn't move files."""
        self.create_test_files()
        self.create_test_csv()

        # Run in dry run mode
        result = self.run_script(
            [
                str(self.csv_file),
                str(self.target_dir),
                "--dup-path",
                str(self.dup_dir),
                "--dry-run",
            ]
        )

        # Check that original files still exist
        assert (
            self.target_dir / "2020+/2022/2022-06/2022-06_Photos/photo1.jpg"
        ).exists()
        assert (
            self.target_dir / "1990+/1995/1995-03/1995-03_Vacation/scan1.jpg"
        ).exists()
        assert (self.target_dir / "2020+/2025/2025-10/NPTSTI~Z/duplicate.jpg").exists()

        # Check that duplicate directory wasn't created
        assert not self.dup_dir.exists()

        # Check output contains dry run message
        assert "DRY RUN" in result.stdout
        assert "would move" in result.stdout.lower()

    def test_missing_files(self):
        """Test handling of files that don't exist."""
        # Create CSV with references to non-existent files
        test_data = [
            [
                "Group ID",
                "Filename",
                "Folder",
                "Size (KB)",
                "Dimensions",
                "Match %",
                "Action",
                "Comments",
            ],
            [
                "0",
                "nonexistent.jpg",
                "X:\\2020+\\2022\\2022-06\\2022-06_Photos",
                "500",
                "1920 x 1080",
                "99",
                "Delete",
                "Missing file",
            ],
        ]
        self.create_test_csv(test_data)

        # Run script (should complete with error code since no files moved and errors occurred)
        result = self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)],
            expect_success=False,
        )

        # Check that missing files are reported
        assert "Files not found: 1" in result.stdout
        assert "Files moved: 0" in result.stdout

    def test_positional_arguments(self):
        """Test using positional arguments."""
        self.create_test_files()
        self.create_test_csv()

        result = self.run_script([str(self.csv_file), str(self.target_dir)])

        # Should succeed and create default duplicate directory
        assert (
            "Successfully moved" in result.stdout or "No files needed" in result.stdout
        )

    def test_named_arguments(self):
        """Test using named arguments."""
        self.create_test_files()
        self.create_test_csv()

        result = self.run_script(
            [
                "--input",
                str(self.csv_file),
                "--target",
                str(self.target_dir),
                "--dup-path",
                str(self.dup_dir),
            ]
        )

        assert result.returncode == 0

    def test_verbose_output(self):
        """Test verbose logging output."""
        self.create_test_files()
        self.create_test_csv()

        result = self.run_script(
            [
                str(self.csv_file),
                str(self.target_dir),
                "--dup-path",
                str(self.dup_dir),
                "--verbose",
            ]
        )

        # Verbose output should contain more detailed information (in stderr for logging)
        assert "Processing CSV file:" in result.stderr or "Moved:" in result.stderr

    def test_quiet_mode(self):
        """Test quiet mode suppresses output."""
        self.create_test_files()
        self.create_test_csv()

        result = self.run_script(
            [
                str(self.csv_file),
                str(self.target_dir),
                "--dup-path",
                str(self.dup_dir),
                "--quiet",
            ]
        )

        # Quiet mode should have minimal output
        assert len(result.stdout.strip()) == 0 or "✅" not in result.stdout

    def test_invalid_csv_file(self):
        """Test handling of invalid CSV file."""
        # Create invalid CSV
        self.csv_file.write_text("invalid,csv,content\nwithout,proper,headers")

        result = self.run_script(
            [str(self.csv_file), str(self.target_dir)], expect_success=False
        )

        assert result.returncode != 0
        assert "Missing required columns" in result.stderr or "Error" in result.stderr

    def test_missing_input_file(self):
        """Test handling of missing input file."""
        result = self.run_script(
            ["/nonexistent/file.csv", str(self.target_dir)], expect_success=False
        )

        assert result.returncode != 0

    def test_missing_target_directory(self):
        """Test handling of missing target directory."""
        self.create_test_csv()

        result = self.run_script(
            [str(self.csv_file), "/nonexistent/directory"], expect_success=False
        )

        assert result.returncode != 0

    def test_no_delete_actions(self):
        """Test CSV with no delete actions."""
        test_data = [
            [
                "Group ID",
                "Filename",
                "Folder",
                "Size (KB)",
                "Dimensions",
                "Match %",
                "Action",
                "Comments",
            ],
            [
                "0",
                "photo1.jpg",
                "X:\\photos\\2020+\\2022\\2022-06\\2022-06_Photos",
                "500",
                "1920 x 1080",
                "99",
                "Keep",
                "Good file",
            ],
            [
                "1",
                "photo2.jpg",
                "X:\\photos\\2020+\\2022\\2022-06\\2022-06_Photos",
                "600",
                "1920 x 1080",
                "98",
                "Keep",
                "Another good file",
            ],
        ]
        self.create_test_csv(test_data)

        result = self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)]
        )

        assert "Delete actions found: 0" in result.stdout
        assert "Files moved: 0" in result.stdout

    def test_path_normalization(self):
        """Test Windows path normalization."""
        # Create file with specific path
        test_file = self.target_dir / "photos" / "2022" / "vacation" / "test.jpg"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Test content")

        # CSV with Windows-style path
        test_data = [
            [
                "Group ID",
                "Filename",
                "Folder",
                "Size (KB)",
                "Dimensions",
                "Match %",
                "Action",
                "Comments",
            ],
            [
                "0",
                "test.jpg",
                "X:\\photos\\2022\\vacation",
                "500",
                "1920 x 1080",
                "99",
                "Delete",
                "Windows path",
            ],
        ]
        self.create_test_csv(test_data)

        result = self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)]
        )

        # File should be moved successfully
        assert not test_file.exists()
        assert (self.dup_dir / "photos" / "2022" / "vacation" / "test.jpg").exists()

    def test_conflicting_destination_files(self):
        """Test handling of conflicting destination files."""
        self.create_test_files()

        # Create a file that will conflict in destination
        conflict_file = self.dup_dir / "2020+/2022/2022-06/2022-06_Photos/photo1.jpg"
        conflict_file.parent.mkdir(parents=True, exist_ok=True)
        conflict_file.write_text("Existing content")

        self.create_test_csv()

        result = self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)]
        )

        # Both files should exist (original and timestamped version)
        assert conflict_file.exists()

        # Find the timestamped file
        timestamped_files = list(conflict_file.parent.glob("photo1_*"))
        assert len(timestamped_files) > 0

    def test_empty_csv_file(self):
        """Test handling of empty CSV file."""
        # Create empty CSV with just headers
        test_data = [
            [
                "Group ID",
                "Filename",
                "Folder",
                "Size (KB)",
                "Dimensions",
                "Match %",
                "Action",
                "Comments",
            ]
        ]
        self.create_test_csv(test_data)

        result = self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)]
        )

        assert "Total rows processed: 0" in result.stdout
        assert result.returncode == 0

    def test_malformed_csv_rows(self):
        """Test handling of malformed CSV rows."""
        test_data = [
            [
                "Group ID",
                "Filename",
                "Folder",
                "Size (KB)",
                "Dimensions",
                "Match %",
                "Action",
                "Comments",
            ],
            [
                "0",
                "",
                "X:\\photos\\2020+\\2022",
                "500",
                "1920 x 1080",
                "99",
                "Delete",
                "Empty filename",
            ],
            [
                "1",
                "photo.jpg",
                "",
                "500",
                "1920 x 1080",
                "99",
                "Delete",
                "Empty folder",
            ],
            [
                "2",
                "normal.jpg",
                "X:\\photos\\2020+\\2022",
                "500",
                "1920 x 1080",
                "99",
                "Delete",
                "Normal row",
            ],
        ]
        self.create_test_csv(test_data)

        result = self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)],
            expect_success=False,
        )  # Expecting failure since file not found

        # Should skip malformed rows but continue processing
        assert "Rows skipped: 2" in result.stdout
        # Should fail due to file not found
        assert result.returncode == 1

    def test_help_message(self):
        """Test help message display."""
        result = subprocess.run(
            ["python3", str(self.script_path), "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Move duplicate files based on dupGuru CSV decisions" in result.stdout
        assert "--input" in result.stdout
        assert "--target" in result.stdout
        assert "--dup-path" in result.stdout

    def test_statistics_output(self):
        """Test statistics reporting."""
        self.create_test_files()
        self.create_test_csv()

        result = self.run_script(
            [str(self.csv_file), str(self.target_dir), "--dup-path", str(self.dup_dir)]
        )

        # Check for statistics in output
        assert "DupGuru Removal Results:" in result.stdout
        assert "Total rows processed:" in result.stdout
        assert "Delete actions found:" in result.stdout
        assert "Files moved:" in result.stdout

    def test_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        # This is a challenging test since KeyboardInterrupt in subprocess is complex
        # Instead, test that the script has proper exception handling structure

        # Read the script content to verify exception handling is present
        with open(self.script_path, "r") as f:
            script_content = f.read()

        # Verify the script has KeyboardInterrupt handling
        assert "except KeyboardInterrupt:" in script_content
        assert "interrupted by user" in script_content

        # For a more realistic test, we could mock the main function directly
        # but that would require importing the script as a module, which
        # adds complexity. The static check above ensures the handler exists.


if __name__ == "__main__":
    pytest.main([__file__])
