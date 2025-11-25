"""Pytest configuration and fixtures."""
import json
import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_vpd_data():
    """Sample VPD data structure for testing."""
    return {
        "projinfo": {
            "projectfile": "/path/to/project.vpd",
            "savetime": {
                "year": 2024,
                "month": 11,
                "day": 25,
                "hour": 10,
                "minute": 30,
                "second": 0
            }
        },
        "imagelist": {
            "scapegoat": [
                {
                    "uuid": "ABC123DEF456",
                    "path": "/path/to/image1.jpg",
                    "title": "Image 1",
                    "width": 1920,
                    "height": 1080,
                    "duration": 5000
                },
                {
                    "uuid": "DEF456GHI789",
                    "path": "/path/to/image2.png",
                    "title": "Image 2",
                    "width": 1920,
                    "height": 1080,
                    "duration": 5000
                }
            ],
            "subitems": [
                {
                    "type": "link",
                    "uuid": "abc-123-def-456",
                    "resid": "ABC123DEF456"
                },
                {
                    "type": "link",
                    "uuid": "def-456-ghi-789",
                    "resid": "DEF456GHI789"
                }
            ]
        },
        "audiolist": {
            "scapegoat": [
                {
                    "uuid": "AUDIO123456",
                    "path": "/path/to/audio.mp3",
                    "title": "Audio Track",
                    "duration": 180000
                }
            ],
            "subitems": [
                {
                    "type": "link",
                    "uuid": "audio-123-456",
                    "resid": "AUDIO123456"
                }
            ]
        },
        "videolist": {
            "scapegoat": [],
            "subitems": []
        },
        "timeline": {
            "subitems": [
                {
                    "title": "Video Track",
                    "subitems": [
                        {
                            "type": "ImageFileBlock",
                            "resid": "abc-123-def-456",
                            "tstart": 0,
                            "duration": 5000
                        },
                        {
                            "type": "ImageFileBlock",
                            "resid": "def-456-ghi-789",
                            "tstart": 5000,
                            "duration": 5000
                        }
                    ]
                },
                {
                    "title": "Audio Track",
                    "subitems": [
                        {
                            "type": "MediaFileBlock",
                            "resid": "audio-123-456",
                            "tstart": 0,
                            "duration": 180000
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def sample_vpd_file(temp_dir, sample_vpd_data):
    """Create a sample VPD file for testing."""
    vpd_file = temp_dir / "test.vpd"
    with open(vpd_file, 'w') as f:
        json.dump(sample_vpd_data, f, indent=4)
    return vpd_file


@pytest.fixture
def sample_media_files(temp_dir):
    """Create sample media files for testing."""
    media_dir = temp_dir / "media"
    media_dir.mkdir()
    
    # Create test files
    files = {
        'image1': media_dir / "image1.jpg",
        'image2': media_dir / "image2.png",
        'audio': media_dir / "audio.mp3"
    }
    
    for file in files.values():
        file.write_text("test content")
    
    return files
