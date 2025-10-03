#!/usr/bin/env python3
"""
Unit tests for the sample.py image sampling script.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add the scripts directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from sample import ImageSampler


class TestImageSampler:
    """Test cases for the ImageSampler class."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary source and target directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / 'source'
            target = temp_path / 'target'
            source.mkdir()
            target.mkdir()
            yield source, target
    
    @pytest.fixture
    def sample_structure(self, temp_dirs):
        """Create a sample directory structure with images and sidecars."""
        source, target = temp_dirs
        
        # Create directory structure
        folders = [
            source / 'folder1',
            source / 'folder1' / 'subfolder1',
            source / 'folder2',
            source / 'folder3' / 'deep'
        ]
        
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Create image files
        images = [
            source / 'root_image1.jpg',
            source / 'root_image2.png',
            source / 'folder1' / 'image1.jpg',
            source / 'folder1' / 'image2.tiff',
            source / 'folder1' / 'subfolder1' / 'deep_image.jpeg',
            source / 'folder2' / 'image3.bmp',
            source / 'folder2' / 'image4.heic',
            source / 'folder3' / 'deep' / 'very_deep.jpg',
            source / 'not_image.txt',  # Non-image file
        ]
        
        for img in images:
            img.touch()
        
        # Create sidecar files
        sidecars = [
            source / 'root_image1.xmp',
            source / 'folder1' / 'image1.yml',
            source / 'folder2' / 'image3.yaml',
            source / 'folder2' / 'image4(1).json',  # Takeout style
        ]
        
        for sidecar in sidecars:
            sidecar.touch()
        
        return source, target
    
    def test_init(self, temp_dirs):
        """Test ImageSampler initialization."""
        source, target = temp_dirs
        sampler = ImageSampler(source, target, max_files=5, debug=True)
        
        assert sampler.source == source.resolve()
        assert sampler.target == target.resolve()
        assert sampler.max_files == 5
        assert sampler.debug is True
        assert sampler.log_dir.exists()
    
    def test_is_image_file(self, temp_dirs):
        """Test image file detection."""
        source, target = temp_dirs
        sampler = ImageSampler(source, target)
        
        # Test various extensions
        assert sampler.is_image_file(Path('test.jpg')) is True
        assert sampler.is_image_file(Path('test.JPEG')) is True
        assert sampler.is_image_file(Path('test.png')) is True
        assert sampler.is_image_file(Path('test.tiff')) is True
        assert sampler.is_image_file(Path('test.heic')) is True
        assert sampler.is_image_file(Path('test.txt')) is False
        assert sampler.is_image_file(Path('test.pdf')) is False
    
    def test_find_images(self, sample_structure):
        """Test finding images in directory structure."""
        source, target = sample_structure
        sampler = ImageSampler(source, target)
        
        # Find all images with depth 2
        images = sampler.find_images(source, 2)
        image_names = [img.name for img in images]
        
        # Should find all images up to depth 2
        expected = ['root_image1.jpg', 'root_image2.png', 'image1.jpg', 
                   'image2.tiff', 'deep_image.jpeg', 'image3.bmp', 'image4.heic', 'very_deep.jpg']
        assert len(images) == len(expected)
        for name in expected:
            assert name in image_names
        
        # Should not find non-image files
        assert 'not_image.txt' not in image_names
    
    def test_find_sidecars(self, sample_structure):
        """Test finding sidecar files."""
        source, target = sample_structure
        sampler = ImageSampler(source, target)
        
        # Test image with XMP sidecar
        image1 = source / 'root_image1.jpg'
        sidecars1 = sampler.find_sidecars(image1)
        assert len(sidecars1) == 1
        assert sidecars1[0].name == 'root_image1.xmp'
        
        # Test image with YML sidecar
        image2 = source / 'folder1' / 'image1.jpg'
        sidecars2 = sampler.find_sidecars(image2)
        assert len(sidecars2) == 1
        assert sidecars2[0].name == 'image1.yml'
        
        # Test image with JSON sidecar (Google Takeout style)
        image3 = source / 'folder2' / 'image4.heic'
        sidecars3 = sampler.find_sidecars(image3)
        assert len(sidecars3) == 1
        assert sidecars3[0].name == 'image4(1).json'
        
        # Test image with no sidecars
        image4 = source / 'root_image2.png'
        sidecars4 = sampler.find_sidecars(image4)
        assert len(sidecars4) == 0
    
    def test_select_files(self, sample_structure):
        """Test file selection algorithm."""
        source, target = sample_structure
        sampler = ImageSampler(source, target, max_files=4, max_folders=2, 
                              max_per_folder=1)
        
        # Mock random.shuffle to make test deterministic
        with patch('sample.random.shuffle') as mock_shuffle:
            mock_shuffle.side_effect = lambda x: x  # Don't shuffle
            selected = sampler.select_files()
        
        assert len(selected) <= 4
        assert all(sampler.is_image_file(f) for f in selected)
    
    @patch('sample.shutil.copy2')
    def test_copy_file_with_metadata(self, mock_copy, sample_structure):
        """Test copying files with sidecars."""
        source, target = sample_structure
        sampler = ImageSampler(source, target)
        
        # Test copying image with sidecar
        image_file = source / 'root_image1.jpg'
        sampler.copy_file_with_metadata(image_file)
        
        # Should have called copy2 twice (image + sidecar)
        assert mock_copy.call_count == 2
        
        # Check that target directory structure is created
        expected_target = target / 'root_image1.jpg'
        assert expected_target.parent.exists()
    
    def test_run_invalid_source(self, temp_dirs):
        """Test run method with invalid source directory."""
        source, target = temp_dirs
        invalid_source = source / 'nonexistent'
        
        sampler = ImageSampler(invalid_source, target)
        
        with pytest.raises(FileNotFoundError):
            sampler.run()
    
    def test_logging(self, temp_dirs):
        """Test logging functionality."""
        source, target = temp_dirs
        sampler = ImageSampler(source, target, debug=True)
        
        test_message = "Test log message"
        sampler.log(test_message)
        
        assert sampler.log_file.exists()
        log_content = sampler.log_file.read_text()
        assert test_message in log_content


class TestMainFunction:
    """Test cases for the main function and argument parsing."""
    
    def test_main_missing_source(self):
        """Test main function with missing source argument."""
        from sample import main
        
        # Mock sys.argv to simulate no arguments
        with patch('sys.argv', ['sample.py']):
            with patch('sample.argparse.ArgumentParser.error') as mock_error:
                main()
                mock_error.assert_called_once()
    
    @patch('sample.ImageSampler')
    def test_main_with_positional_args(self, mock_sampler_class):
        """Test main function with positional arguments."""
        from sample import main
        
        mock_sampler = MagicMock()
        mock_sampler_class.return_value = mock_sampler
        
        test_args = ['sample.py', '/source', '/target']
        with patch('sys.argv', test_args):
            result = main()
        
        assert result == 0
        mock_sampler_class.assert_called_once()
        mock_sampler.run.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])
