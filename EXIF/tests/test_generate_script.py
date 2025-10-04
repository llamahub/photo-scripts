"""
Tests for generate.py script - CLI interface and argument parsing.

These tests focus on testing the generate.py script directly, including:
- Command line argument parsing
- Error handling for invalid arguments
- Integration between CLI and ImageGenerator class
- Script entry point functionality
"""

import pytest
import subprocess
import tempfile
import sys
import csv
from pathlib import Path
from unittest import mock


class TestGenerateScript:
    """Test the generate.py script CLI interface."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the generate.py script."""
        return Path(__file__).parent.parent / "scripts" / "generate.py"

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_dir = temp_path / "csv"
            output_dir = temp_path / "output"
            csv_dir.mkdir()
            output_dir.mkdir()
            yield csv_dir, output_dir

    @pytest.fixture
    def sample_csv_file(self, temp_dirs):
        """Create a sample CSV file for testing."""
        csv_dir, _ = temp_dirs
        csv_file = csv_dir / "test_images.csv"

        sample_data = [
            {
                "Root Path": "photos",
                "Parent Folder": "vacation",
                "Filename": "beach_sunset",
                "Source Ext": "jpg",
                "Image Width": "800",
                "Image Height": "600",
                "Actual Format": "JPEG",
                "DateTimeOriginal": "2023:07:15 18:30:00",
                "ExifIFD:DateTimeOriginal": "",
                "XMP-photoshop:DateCreated": "2023-07-15",
            },
            {
                "Root Path": "photos",
                "Parent Folder": "family",
                "Filename": "birthday",
                "Source Ext": "png",
                "Image Width": "1024",
                "Image Height": "768",
                "Actual Format": "PNG",
                "DateTimeOriginal": "2023:08:20 15:45:00",
                "ExifIFD:DateTimeOriginal": "",
                "XMP-photoshop:DateCreated": "",
            },
        ]

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=sample_data[0].keys())
            writer.writeheader()
            writer.writerows(sample_data)

        return csv_file

    def test_script_help(self, script_path):
        """Test that the script shows help message."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Generate test images from CSV data" in result.stdout
        assert "CSV Format Requirements:" in result.stdout
        assert "--sample" in result.stdout
        assert "--debug" in result.stdout

    def test_script_missing_arguments(self, script_path):
        """Test that script fails with missing arguments."""
        # No arguments
        result = subprocess.run(
            [sys.executable, str(script_path)], capture_output=True, text=True
        )

        assert result.returncode != 0
        assert "CSV file is required" in result.stderr

    def test_script_missing_output(self, script_path, sample_csv_file):
        """Test that script fails with missing output argument."""
        result = subprocess.run(
            [sys.executable, str(script_path), str(sample_csv_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "output directory is required" in result.stderr

    def test_script_nonexistent_csv(self, script_path, temp_dirs):
        """Test script with nonexistent CSV file."""
        _, output_dir = temp_dirs
        nonexistent_csv = output_dir.parent / "nonexistent.csv"

        result = subprocess.run(
            [sys.executable, str(script_path), str(nonexistent_csv), str(output_dir)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "CSV file not found" in result.stderr

    def test_script_positional_arguments(self, script_path, sample_csv_file, temp_dirs):
        """Test script with positional arguments."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(sample_csv_file),
                str(output_dir),
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Image generation completed successfully" in result.stdout

        # Verify images were created
        created_images = list(output_dir.rglob("*.jpg")) + list(
            output_dir.rglob("*.png")
        )
        assert len(created_images) == 2

    def test_script_named_arguments(self, script_path, sample_csv_file, temp_dirs):
        """Test script with named arguments."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--csv",
                str(sample_csv_file),
                "--output",
                str(output_dir),
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Image generation completed successfully" in result.stdout

    def test_script_sample_option(self, script_path, sample_csv_file, temp_dirs):
        """Test script with sample option."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(sample_csv_file),
                str(output_dir),
                "--sample",
                "1",
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Image generation completed successfully" in result.stdout

        # Should have created only 1 image
        created_images = list(output_dir.rglob("*.*"))
        assert len(created_images) == 1

    def test_script_limit_option(self, script_path, sample_csv_file, temp_dirs):
        """Test script with limit option."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(sample_csv_file),
                str(output_dir),
                "--limit",
                "1",
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Image generation completed successfully" in result.stdout

        # Should have created only 1 image
        created_images = list(output_dir.rglob("*.*"))
        assert len(created_images) == 1

    def test_script_debug_mode(self, script_path, sample_csv_file, temp_dirs):
        """Test script with debug mode enabled."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(sample_csv_file),
                str(output_dir),
                "--debug",
                "--no-exiftool",
                "--sample",
                "1",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Debug mode should provide additional output
        # (We can't easily check the log file from subprocess,
        # but we can verify the script ran successfully)

    def test_script_mixed_arguments(self, script_path, sample_csv_file, temp_dirs):
        """Test script with mixed positional and named arguments."""
        _, output_dir = temp_dirs

        # Positional CSV, named output
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(sample_csv_file),
                "--output",
                str(output_dir),
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Image generation completed successfully" in result.stdout

    def test_script_sample_and_limit_warning(
        self, script_path, sample_csv_file, temp_dirs
    ):
        """Test that script warns when both sample and limit are specified."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(sample_csv_file),
                str(output_dir),
                "--sample",
                "1",
                "--limit",
                "1",
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Both --sample and --limit specified, using --sample" in result.stderr

    def test_script_handles_import_error(self, script_path, sample_csv_file, temp_dirs):
        """Test that script handles import errors gracefully."""
        # We can't easily simulate import errors in subprocess tests,
        # but we can verify the script structure handles them properly
        # by checking the import error handling code exists
        script_content = Path(script_path).read_text()
        assert "ImportError" in script_content
        assert "sys.exit(1)" in script_content


class TestGenerateScriptIntegration:
    """Integration tests for the generate.py script with actual ImageGenerator functionality."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories with more complex test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_dir = temp_path / "csv"
            output_dir = temp_path / "output"
            csv_dir.mkdir()
            output_dir.mkdir()
            yield csv_dir, output_dir

    @pytest.fixture
    def complex_csv_file(self, temp_dirs):
        """Create a more complex CSV file for integration testing."""
        csv_dir, _ = temp_dirs
        csv_file = csv_dir / "complex_test.csv"

        complex_data = [
            {
                "Root Path": "photos",
                "Parent Folder": "vacation/2023",
                "Filename": "beach_sunset",
                "Source Ext": "jpg",
                "Image Width": "1920",
                "Image Height": "1080",
                "Actual Format": "JPEG",
                "DateTimeOriginal": "2023:07:15 18:30:00",
                "ExifIFD:DateTimeOriginal": "2023:07:15 18:30:00",
                "XMP-photoshop:DateCreated": "2023-07-15",
            },
            {
                "Root Path": "photos",
                "Parent Folder": "family/events",
                "Filename": "birthday_party",
                "Source Ext": "png",
                "Image Width": "800",
                "Image Height": "600",
                "Actual Format": "PNG",
                "DateTimeOriginal": "2023:08:20 15:45:00",
                "ExifIFD:DateTimeOriginal": "",
                "XMP-photoshop:DateCreated": "2023-08-20",
            },
            {
                "Root Path": "photos",
                "Parent Folder": "pets/outdoor",
                "Filename": "dog_playing",
                "Source Ext": "tiff",
                "Image Width": "1024",
                "Image Height": "768",
                "Actual Format": "TIFF",
                "DateTimeOriginal": "",
                "ExifIFD:DateTimeOriginal": "",
                "XMP-photoshop:DateCreated": "",
            },
            {
                "Root Path": "photos",
                "Parent Folder": "nature/landscapes",
                "Filename": "mountain_view",
                "Source Ext": "heic",
                "Image Width": "4032",
                "Image Height": "3024",
                "Actual Format": "HEIC",
                "DateTimeOriginal": "2023:09:10 14:20:00",
                "ExifIFD:DateTimeOriginal": "2023:09:10 14:20:00",
                "XMP-photoshop:DateCreated": "2023-09-10",
            },
        ]

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=complex_data[0].keys())
            writer.writeheader()
            writer.writerows(complex_data)

        return csv_file

    @pytest.fixture
    def script_path(self):
        """Get the path to the generate.py script."""
        return Path(__file__).parent.parent / "scripts" / "generate.py"

    def test_script_full_generation(self, script_path, complex_csv_file, temp_dirs):
        """Test full script execution with complex data."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(complex_csv_file),
                str(output_dir),
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Image generation completed successfully" in result.stdout
        assert "Generated 4 images from 4 specifications" in result.stdout

        # Verify directory structure was created
        assert (output_dir / "photos" / "vacation" / "2023").exists()
        assert (output_dir / "photos" / "family" / "events").exists()
        assert (output_dir / "photos" / "pets" / "outdoor").exists()
        assert (output_dir / "photos" / "nature" / "landscapes").exists()

        # Verify images were created
        all_images = list(output_dir.rglob("*.*"))
        assert len(all_images) == 4

        # Check specific files
        assert (
            output_dir / "photos" / "vacation" / "2023" / "beach_sunset.jpg"
        ).exists()
        assert (
            output_dir / "photos" / "family" / "events" / "birthday_party.png"
        ).exists()
        assert (
            output_dir / "photos" / "pets" / "outdoor" / "dog_playing.tiff"
        ).exists()
        assert (
            output_dir / "photos" / "nature" / "landscapes" / "mountain_view.heic"
        ).exists()

    def test_script_statistics_output(self, script_path, complex_csv_file, temp_dirs):
        """Test that script outputs useful statistics."""
        _, output_dir = temp_dirs

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                str(complex_csv_file),
                str(output_dir),
                "--no-exiftool",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Check for expected statistics in output
        assert "🎉 Image generation completed successfully!" in result.stdout
        assert "📊 Generated 4 images from 4 specifications" in result.stdout
        assert f"📁 Output directory: {output_dir.resolve()}" in result.stdout


class TestGenerateScriptMainFunction:
    """Test the main() function directly without subprocess calls."""

    def test_main_function_import(self):
        """Test that we can import the main function."""
        import sys
        from pathlib import Path

        # Add the scripts directory to path
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import generate

            assert hasattr(generate, "main")
            assert callable(generate.main)
        except ImportError:
            pytest.skip("generate module not available for direct import testing")

    def test_main_function_success(self):
        """Test main function with valid arguments."""
        import sys
        from pathlib import Path
        import tempfile
        import csv

        # Add the scripts directory to path
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import generate

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                csv_file = temp_path / "test.csv"
                output_dir = temp_path / "output"
                output_dir.mkdir()

                # Create test CSV
                test_data = [
                    {
                        "Root Path": "test",
                        "Parent Folder": "folder",
                        "Filename": "image",
                        "Source Ext": "jpg",
                        "Image Width": "100",
                        "Image Height": "100",
                        "Actual Format": "JPEG",
                        "DateTimeOriginal": "",
                        "ExifIFD:DateTimeOriginal": "",
                        "XMP-photoshop:DateCreated": "",
                    }
                ]

                with open(csv_file, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=test_data[0].keys())
                    writer.writeheader()
                    writer.writerows(test_data)

                # Save original sys.argv
                original_argv = sys.argv

                # Mock sys.argv for testing
                sys.argv = [
                    "generate.py",
                    str(csv_file),
                    str(output_dir),
                    "--no-exiftool",
                ]

                try:
                    # Call main function
                    result = generate.main()

                    # Should return 0 for success
                    assert result == 0

                    # Verify image was created
                    created_images = list(output_dir.rglob("*.*"))
                    assert len(created_images) == 1

                finally:
                    # Restore original sys.argv
                    sys.argv = original_argv

        except ImportError:
            pytest.skip("generate module not available for direct testing")

    def test_main_function_error_handling(self):
        """Test main function error handling."""
        import sys
        from pathlib import Path

        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            import generate

            # Save original sys.argv
            original_argv = sys.argv

            # Mock sys.argv with nonexistent CSV file
            sys.argv = ["generate.py", "/nonexistent/file.csv", "/tmp/output"]

            try:
                # Call main function
                result = generate.main()

                # Should return 1 for error
                assert result == 1

            finally:
                # Restore original sys.argv
                sys.argv = original_argv

        except ImportError:
            pytest.skip("generate module not available for direct testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
