#!/usr/bin/env python3
"""
Basic tests for the find_dups script to ensure migration worked correctly.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the migrated find_dups script
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestFindDupsScript(unittest.TestCase):
    """Test the find_dups script functionality."""

    def setUp(self):
        """Set up test directories."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.temp_dir / "source"
        self.target_dir = self.temp_dir / "target"

        # Create test directory structure
        self.source_dir.mkdir()
        self.target_dir.mkdir()

        # Add some test files
        (self.source_dir / "image1.jpg").touch()
        (self.source_dir / "image2.jpg").touch()
        (self.target_dir / "image1.jpg").touch()  # duplicate
        (self.target_dir / "image3.jpg").touch()  # unique to target

    def tearDown(self):
        """Clean up test directories."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_duplicate_finder_can_be_imported(self):
        """Test that DuplicateFinder can be imported."""
        from exif.duplicate_finder import DuplicateFinder

        self.assertTrue(DuplicateFinder)

    def test_duplicate_finder_initialization(self):
        """Test DuplicateFinder can be initialized."""
        import logging
        from exif.duplicate_finder import DuplicateFinder

        logger = logging.getLogger("test")

        finder = DuplicateFinder(
            source_dir=self.source_dir, target_dir=self.target_dir, logger=logger
        )

        self.assertEqual(finder.source_dir, self.source_dir)
        self.assertEqual(finder.target_dir, self.target_dir)
        self.assertEqual(finder.logger, logger)


if __name__ == "__main__":
    unittest.main()
