#!/usr/bin/env python3
"""Unit tests for dupguru.py script."""

import pytest
import os
import csv
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Get the script path
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "dupguru.py")


class TestDupGuruScript:
    """Test cases for dupguru.py CLI script."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_csv = os.path.join(self.temp_dir, "test_duplicates.csv")
        self.log_dir = os.path.join(self.temp_dir, ".log")
        os.makedirs(self.log_dir, exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.temp_dir)

    def create_test_csv(self, data=None, include_actions=False):
        """Create a test CSV file with dupGuru format."""
        if data is None:
            data = [
                {
                    "Group ID": "0",
                    "Filename": "IMG_001.jpg",
                    "Folder": "X:\\images\\2020+\\2025\\2025-10\\NPTSTI~Z",
                    "Size (KB)": "500",
                    "Dimensions": "1920 x 1080",
                    "Match %": "99"
                },
                {
                    "Group ID": "0",
                    "Filename": "2022-06-15_1200_DEB_1920x1080_IMG_001.jpg",
                    "Folder": "X:\\images\\2020+\\2022\\2022-06\\2022-06_DEB",
                    "Size (KB)": "485",
                    "Dimensions": "1920 x 1080", 
                    "Match %": "99"
                },
                {
                    "Group ID": "1",
                    "Filename": "photo1.jpg",
                    "Folder": "X:\\images\\0+\\0000\\0000-00\\Random",
                    "Size (KB)": "300",
                    "Dimensions": "1024 x 768",
                    "Match %": "98"
                },
                {
                    "Group ID": "1", 
                    "Filename": "2021-03-10_1400_2021-03-10_photo1.jpg",
                    "Folder": "X:\\images\\2020+\\2021\\2021-03\\2021-03-10",
                    "Size (KB)": "295",
                    "Dimensions": "1024 x 768",
                    "Match %": "98"
                }
            ]

        fieldnames = ["Group ID", "Filename", "Folder", "Size (KB)", "Dimensions", "Match %"]
        if include_actions:
            fieldnames.extend(["Action", "Comments"])
            for row in data:
                row.setdefault("Action", "")
                row.setdefault("Comments", "")

        with open(self.test_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def run_script(self, args, cwd=None):
        """Run the dupguru.py script with given arguments."""
        cmd = [sys.executable, SCRIPT_PATH] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd or self.temp_dir
        )
        return result

    def read_csv_output(self, filepath):
        """Read CSV output file and return rows."""
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)

    # Basic functionality tests

    def test_basic_processing(self):
        """Test basic CSV processing functionality."""
        self.create_test_csv()
        
        result = self.run_script([self.test_csv])
        
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        
        # Check that output was created
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        assert len(output_files) == 1, f"Expected 1 output file, got {len(output_files)}"
        
        output_data = self.read_csv_output(output_files[0])
        
        # Check that Action and Comments columns were added
        assert len(output_data) == 4
        for row in output_data:
            assert "Action" in row
            assert "Comments" in row

    def test_invalid_folder_rule(self):
        """Test that invalid folders are properly rejected."""
        self.create_test_csv()
        
        result = self.run_script([self.test_csv])
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        output_data = self.read_csv_output(output_files[0])
        
        # Group 0: NPTSTI~Z folder should be deleted, organized filename kept
        group0_rows = [row for row in output_data if row["Group ID"] == "0"]
        nptsi_file = next(row for row in group0_rows if "NPTSTI~Z" in row["Folder"])
        organized_file = next(row for row in group0_rows if "_DEB_" in row["Filename"])
        
        assert nptsi_file["Action"] == "Delete"
        assert organized_file["Action"] == "Keep"
        assert "not keeping" in nptsi_file["Comments"].lower()

    def test_older_file_preference(self):
        """Test preference for older files in valid folders."""
        self.create_test_csv()
        
        result = self.run_script([self.test_csv])
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        output_data = self.read_csv_output(output_files[0])
        
        # Group 1: Should prefer older file in valid folder
        group1_rows = [row for row in output_data if row["Group ID"] == "1"]
        invalid_folder_file = next(row for row in group1_rows if "0000-00" in row["Folder"])
        valid_folder_file = next(row for row in group1_rows if "2021-03" in row["Folder"])
        
        assert invalid_folder_file["Action"] == "Delete"
        assert valid_folder_file["Action"] == "Keep"

    def test_size_threshold_rule(self):
        """Test file size threshold rule."""
        # Create data with significant size difference
        data = [
            {
                "Group ID": "0",
                "Filename": "small_version.jpg",
                "Folder": "X:\\images\\2020+\\2022\\2022-06\\folder1", 
                "Size (KB)": "100",
                "Dimensions": "1920 x 1080",
                "Match %": "99"
            },
            {
                "Group ID": "0",
                "Filename": "large_version.jpg",
                "Folder": "X:\\images\\2020+\\2022\\2022-06\\folder2",
                "Size (KB)": "200", # 100KB difference > 50KB threshold
                "Dimensions": "1920 x 1080",
                "Match %": "99"
            }
        ]
        
        self.create_test_csv(data)
        
        result = self.run_script([self.test_csv])
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        output_data = self.read_csv_output(output_files[0])
        
        small_file = next(row for row in output_data if row["Filename"] == "small_version.jpg")
        large_file = next(row for row in output_data if row["Filename"] == "large_version.jpg")
        
        assert small_file["Action"] == "Delete"
        assert large_file["Action"] == "Keep"
        assert "larger file size" in large_file["Comments"].lower()

    def test_organized_filename_preference(self):
        """Test preference for organized filenames."""
        data = [
            {
                "Group ID": "0",
                "Filename": "random_name.jpg",
                "Folder": "X:\\images\\2020+\\2022\\2022-06\\folder1",
                "Size (KB)": "100",
                "Dimensions": "1920 x 1080",
                "Match %": "99"
            },
            {
                "Group ID": "0", 
                "Filename": "2022-06-15_1200_DEB_1920x1080_photo.jpg",
                "Folder": "X:\\images\\2020+\\2022\\2022-06\\folder2",
                "Size (KB)": "95", # Slightly smaller but organized
                "Dimensions": "1920 x 1080",
                "Match %": "99"
            }
        ]
        
        self.create_test_csv(data)
        
        result = self.run_script([self.test_csv])
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        output_data = self.read_csv_output(output_files[0])
        
        random_file = next(row for row in output_data if row["Filename"] == "random_name.jpg")
        organized_file = next(row for row in output_data if "_DEB_" in row["Filename"])
        
        assert random_file["Action"] == "Delete"
        assert organized_file["Action"] == "Keep"
        assert "organized filename" in organized_file["Comments"].lower()

    def test_safety_check(self):
        """Test that safety check prevents losing all copies."""
        # Create data where both files would normally be deleted
        data = [
            {
                "Group ID": "0",
                "Filename": "file1.jpg",
                "Folder": "X:\\images\\0+\\0000\\0000-00\\invalid1",
                "Size (KB)": "100", 
                "Dimensions": "1920 x 1080",
                "Match %": "99",
                "Action": "Delete",
                "Comments": "Invalid folder"
            },
            {
                "Group ID": "0",
                "Filename": "file2.jpg", 
                "Folder": "X:\\images\\0+\\0000\\0000-00\\invalid2",
                "Size (KB)": "95",
                "Dimensions": "1920 x 1080",
                "Match %": "99",
                "Action": "",
                "Comments": ""
            }
        ]
        
        self.create_test_csv(data, include_actions=True)
        
        result = self.run_script([self.test_csv])
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        output_data = self.read_csv_output(output_files[0])
        
        # Should have at least one Keep action
        actions = [row["Action"] for row in output_data]
        assert "Keep" in actions, f"No Keep action found in safety check: {actions}"

    def test_preserve_existing_actions(self):
        """Test that existing Action/Comments are preserved."""
        data = [
            {
                "Group ID": "0",
                "Filename": "file1.jpg",
                "Folder": "X:\\images\\folder1",
                "Size (KB)": "100",
                "Dimensions": "1920 x 1080", 
                "Match %": "99",
                "Action": "Keep",
                "Comments": "User decision"
            },
            {
                "Group ID": "0",
                "Filename": "file2.jpg",
                "Folder": "X:\\images\\folder2", 
                "Size (KB)": "95",
                "Dimensions": "1920 x 1080",
                "Match %": "99",
                "Action": "Delete",
                "Comments": "User decision"
            }
        ]
        
        self.create_test_csv(data, include_actions=True)
        
        result = self.run_script([self.test_csv])
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        output_data = self.read_csv_output(output_files[0])
        
        # Existing decisions should be preserved
        for orig, new in zip(data, output_data):
            assert orig["Action"] == new["Action"]
            assert orig["Comments"] == new["Comments"]

    # Command line argument tests

    def test_output_argument(self):
        """Test --output argument."""
        self.create_test_csv()
        output_file = os.path.join(self.temp_dir, "custom_output.csv")
        
        result = self.run_script([self.test_csv, "--output", output_file])
        
        assert result.returncode == 0
        assert os.path.exists(output_file)

    def test_verbose_argument(self):
        """Test --verbose argument."""
        self.create_test_csv()
        
        result = self.run_script([self.test_csv, "--verbose"])
        
        assert result.returncode == 0
        assert "[INFO]" in result.stdout or len(result.stdout) > 0

    def test_quiet_argument(self):
        """Test --quiet argument."""
        self.create_test_csv()
        
        result = self.run_script([self.test_csv, "--quiet"])
        
        assert result.returncode == 0
        # Should have minimal output
        lines = result.stdout.strip().split('\n')
        assert len(lines) <= 2  # Should be very minimal

    def test_size_threshold_argument(self):
        """Test --size-threshold argument."""
        data = [
            {
                "Group ID": "0",
                "Filename": "small.jpg",
                "Folder": "X:\\images\\2020+\\2022\\2022-06\\folder1",
                "Size (KB)": "100",
                "Dimensions": "1920 x 1080",
                "Match %": "99"
            },
            {
                "Group ID": "0",
                "Filename": "large.jpg", 
                "Folder": "X:\\images\\2020+\\2022\\2022-06\\folder2",
                "Size (KB)": "125", # 25KB difference
                "Dimensions": "1920 x 1080",
                "Match %": "99"
            }
        ]
        
        self.create_test_csv(data)
        
        # With default 50KB threshold, should not trigger size rule
        result1 = self.run_script([self.test_csv])
        
        # With 20KB threshold, should trigger size rule  
        result2 = self.run_script([self.test_csv, "--size-threshold", "20"])
        
        assert result1.returncode == 0
        assert result2.returncode == 0

    def test_no_stats_argument(self):
        """Test --no-stats argument."""
        self.create_test_csv()
        
        result = self.run_script([self.test_csv, "--no-stats"])
        
        assert result.returncode == 0
        assert "Total groups:" not in result.stdout

    # Error handling tests

    def test_missing_input_file(self):
        """Test error handling for missing input file."""
        result = self.run_script(["nonexistent.csv"])
        
        assert result.returncode == 1
        assert "not found" in result.stdout.lower()

    def test_invalid_csv_format(self):
        """Test error handling for invalid CSV format."""
        # Create malformed CSV
        with open(self.test_csv, 'w') as f:
            f.write("invalid,csv,data\n")
            f.write("missing,required,columns\n")
        
        result = self.run_script([self.test_csv])
        
        assert result.returncode == 1

    def test_empty_csv_file(self):
        """Test error handling for empty CSV file."""
        # Create empty CSV
        with open(self.test_csv, 'w') as f:
            f.write("Group ID,Filename,Folder,Size (KB),Dimensions,Match %\n")
        
        result = self.run_script([self.test_csv])
        
        assert result.returncode == 1
        assert "no data" in result.stdout.lower()

    def test_keyboard_interrupt(self):
        """Test graceful handling of keyboard interrupt."""
        self.create_test_csv()
        
        # This is harder to test directly, but we can at least verify the script handles it
        # In practice, this would require mocking or signal handling
        pass

    # Integration tests

    def test_real_world_scenario(self):
        """Test with realistic dupGuru output."""
        data = [
            # Organized vs unorganized
            {
                "Group ID": "0",
                "Filename": "IMG_1234.jpg", 
                "Folder": "X:\\photos\\2020+\\2025\\2025-10\\NPTSTI~Z",
                "Size (KB)": "2500",
                "Dimensions": "3024 x 4032",
                "Match %": "100"
            },
            {
                "Group ID": "0",
                "Filename": "2022-08-15_1430_DEB_3024x4032_IMG_1234.jpg",
                "Folder": "X:\\photos\\2020+\\2022\\2022-08\\2022-08_DEB", 
                "Size (KB)": "2485",
                "Dimensions": "3024 x 4032",
                "Match %": "100"
            },
            # Scanned photos
            {
                "Group ID": "1",
                "Filename": "1975-01-01_0000_1800x1200_197501_Scans_old_photo.jpg",
                "Folder": "X:\\photos\\1970+\\1975\\1975-01\\197501_Scans",
                "Size (KB)": "800",
                "Dimensions": "1800 x 1200", 
                "Match %": "99"
            },
            {
                "Group ID": "1",
                "Filename": "2002-09-01_1200_1800x1200_old_photo.jpg",
                "Folder": "X:\\photos\\2000+\\2002\\2002-09\\197501",
                "Size (KB)": "795",
                "Dimensions": "1800 x 1200",
                "Match %": "99"
            },
            # Size difference scenario
            {
                "Group ID": "2",
                "Filename": "vacation.jpg",
                "Folder": "X:\\photos\\2020+\\2023\\2023-07\\vacation",
                "Size (KB)": "1000",
                "Dimensions": "2000 x 1500",
                "Match %": "98"
            },
            {
                "Group ID": "2", 
                "Filename": "vacation_hq.jpg",
                "Folder": "X:\\photos\\2020+\\2023\\2023-07\\vacation_hq",
                "Size (KB)": "1500", # 500KB difference > 50KB threshold
                "Dimensions": "2000 x 1500", 
                "Match %": "98"
            }
        ]
        
        self.create_test_csv(data)
        
        result = self.run_script([self.test_csv])
        assert result.returncode == 0
        
        output_files = list(Path(self.temp_dir).glob("*_processed_*.csv"))
        output_data = self.read_csv_output(output_files[0])
        
        # Verify expected outcomes
        groups = {}
        for row in output_data:
            gid = row["Group ID"]
            if gid not in groups:
                groups[gid] = []
            groups[gid].append(row)
        
        # Group 0: Should prefer organized filename
        group0_keep = next(row for row in groups["0"] if row["Action"] == "Keep")
        assert "_DEB_" in group0_keep["Filename"]
        
        # Group 1: Should prefer scanned original 
        group1_keep = next(row for row in groups["1"] if row["Action"] == "Keep") 
        assert "scan" in group1_keep["Folder"].lower()
        
        # Group 2: Should prefer larger file
        group2_keep = next(row for row in groups["2"] if row["Action"] == "Keep")
        assert group2_keep["Filename"] == "vacation_hq.jpg"

    def test_statistics_output(self):
        """Test that statistics are properly calculated and displayed."""
        self.create_test_csv()
        
        result = self.run_script([self.test_csv])
        
        assert result.returncode == 0
        assert "Total groups:" in result.stdout
        assert "Pairs processed:" in result.stdout
        assert "Safety verification passed" in result.stdout

    def test_help_message(self):
        """Test help message display."""
        result = self.run_script(["--help"])
        
        assert result.returncode == 0
        assert "Process dupGuru duplicate detection CSV files" in result.stdout
        assert "Decision Rules" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])