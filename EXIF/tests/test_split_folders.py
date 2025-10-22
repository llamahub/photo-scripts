#!/usr/bin/env python3
"""
Tests for split_folders.py script.
"""

import unittest
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.split_folders import FolderSplitter


class MockLogger:
    """Mock logger for testing."""
    def info(self, msg): pass
    def debug(self, msg): pass
    def error(self, msg): pass


class TestSplitFolders(unittest.TestCase):
    """Test cases for FolderSplitter functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.mock_logger = MockLogger()
    
    def test_init(self):
        """Test FolderSplitter initialization."""
        splitter = FolderSplitter(
            source_dir=self.test_dir,
            threshold=50,
            max_per_folder=50,
            dry_run=True
        )
        
        self.assertEqual(splitter.source_dir, self.test_dir)
        self.assertEqual(splitter.threshold, 50)
        self.assertEqual(splitter.max_per_folder, 50)
        self.assertTrue(splitter.dry_run)
        self.assertIsInstance(splitter.stats, dict)
        self.assertIsInstance(splitter.image_extensions, set)
    
    def test_is_image_file(self):
        """Test image file detection."""
        splitter = FolderSplitter(self.test_dir, dry_run=True)
        
        # Test valid image extensions
        self.assertTrue(splitter.is_image_file(Path("test.jpg")))
        self.assertTrue(splitter.is_image_file(Path("test.JPG")))
        self.assertTrue(splitter.is_image_file(Path("test.png")))
        self.assertTrue(splitter.is_image_file(Path("test.heic")))
        
        # Test invalid extensions
        self.assertFalse(splitter.is_image_file(Path("test.txt")))
        self.assertFalse(splitter.is_image_file(Path("test.mp4")))
        self.assertFalse(splitter.is_image_file(Path("test.doc")))
    
    def test_empty_directory(self):
        """Test behavior with empty directory."""
        splitter = FolderSplitter(self.test_dir, dry_run=True, logger=self.mock_logger)
        
        # Run on empty directory
        splitter.run()
        
        stats = splitter.get_stats()
        self.assertEqual(stats['folders_scanned'], 1)  # Source directory itself is scanned
        self.assertEqual(stats['folders_split'], 0)
        self.assertEqual(stats['subfolders_created'], 0)
        self.assertEqual(stats['images_processed'], 0)
    
    def test_small_folders_not_split(self):
        """Test that folders with fewer than threshold images are not split."""
        # Create a small folder with few images
        small_folder = self.test_dir / "small_folder"
        small_folder.mkdir()
        
        # Create some dummy image files (names only, no actual image content)
        for i in range(10):
            (small_folder / f"image_{i:03d}.jpg").touch()
        
        splitter = FolderSplitter(self.test_dir, threshold=50, dry_run=True, logger=self.mock_logger)
        splitter.run()
        
        stats = splitter.get_stats()
        self.assertEqual(stats['folders_scanned'], 2)  # Source directory + small_folder
        self.assertEqual(stats['folders_split'], 0)  # Should not be split
        self.assertEqual(stats['subfolders_created'], 0)
    
    def test_get_stats(self):
        """Test statistics collection."""
        splitter = FolderSplitter(self.test_dir, dry_run=True)
        
        initial_stats = splitter.get_stats()
        expected_keys = [
            'folders_scanned', 'folders_split', 'subfolders_created', 
            'images_processed', 'errors'
        ]
        
        for key in expected_keys:
            self.assertIn(key, initial_stats)
            self.assertEqual(initial_stats[key], 0)
    
    def test_nonexistent_directory(self):
        """Test error handling for nonexistent directory."""
        nonexistent_dir = self.test_dir / "does_not_exist"
        splitter = FolderSplitter(nonexistent_dir, dry_run=True)
        
        with self.assertRaises(ValueError) as context:
            splitter.run()
        
        self.assertIn("does not exist", str(context.exception))
    
    def test_custom_threshold(self):
        """Test custom threshold setting."""
        splitter = FolderSplitter(self.test_dir, threshold=25, max_per_folder=10, dry_run=True)
        
        self.assertEqual(splitter.threshold, 25)
        self.assertEqual(splitter.max_per_folder, 10)


if __name__ == '__main__':
    unittest.main()