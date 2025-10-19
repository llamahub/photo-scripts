#!/usr/bin/env python3
"""
Basic tests for the diff script to ensure migration worked correctly.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import the diff script
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
import diff


class TestDiffScript(unittest.TestCase):
    """Test the diff script functionality."""
    
    def setUp(self):
        """Set up test directories."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = self.temp_dir / 'source'
        self.target_dir = self.temp_dir / 'target'
        
        # Create test directory structure
        self.source_dir.mkdir()
        self.target_dir.mkdir()
        
        # Add some common and unique directories
        (self.source_dir / 'common').mkdir()
        (self.target_dir / 'common').mkdir()
        (self.source_dir / 'unique_source').mkdir()
        (self.target_dir / 'unique_target').mkdir()
        
        # Add some files
        (self.source_dir / 'file1.txt').touch()
        (self.target_dir / 'file2.txt').touch()
    
    def tearDown(self):
        """Clean up test directories."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_directory_comparator_initialization(self):
        """Test DirectoryComparator can be initialized."""
        import logging
        logger = logging.getLogger('test')
        
        comparator = diff.DirectoryComparator(
            self.source_dir, self.target_dir, logger)
        
        self.assertEqual(comparator.source, self.source_dir)
        self.assertEqual(comparator.target, self.target_dir)
        self.assertEqual(comparator.logger, logger)
    
    def test_directory_comparison(self):
        """Test directory comparison functionality."""
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('test')
        
        comparator = diff.DirectoryComparator(
            self.source_dir, self.target_dir, logger)
        
        # Perform comparison
        report = comparator.perform_comparison()
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertIn('DIRECTORY STRUCTURE COMPARISON REPORT', report)
        self.assertIn('source', report)
        self.assertIn('target', report)
        
        # Check statistics
        self.assertEqual(comparator.stats['source_directories'], 2)
        self.assertEqual(comparator.stats['target_directories'], 2)
        self.assertEqual(comparator.stats['source_files'], 1)
        self.assertEqual(comparator.stats['target_files'], 1)
        
        # Clean up temp files
        comparator.cleanup_temp_files()


if __name__ == '__main__':
    unittest.main()