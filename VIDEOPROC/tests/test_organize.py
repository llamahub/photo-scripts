"""Tests for organize script."""
import json
import pytest
import logging
from pathlib import Path
from scripts.organize import VPDOrganizer, MediaResource, TimelineBlock


class TestVPDOrganizer:
    """Test VPDOrganizer class."""
    
    def test_normalize_uuid_with_hyphens(self):
        """Test UUID normalization removes hyphens and uppercases."""
        logger = logging.getLogger(__name__)
        organizer = VPDOrganizer(
            vpd_path="/tmp/test.vpd",
            target_dir="/tmp/target",
            dry_run=True,
            logger=logger
        )
        
        uuid_with_hyphens = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        normalized = organizer.normalize_uuid(uuid_with_hyphens)
        
        assert normalized == "A1B2C3D4E5F67890ABCDEF1234567890"
        assert "-" not in normalized
        assert normalized.isupper()
    
    def test_normalize_uuid_already_normalized(self):
        """Test UUID normalization on already normalized UUID."""
        logger = logging.getLogger(__name__)
        organizer = VPDOrganizer(
            vpd_path="/tmp/test.vpd",
            target_dir="/tmp/target",
            dry_run=True,
            logger=logger
        )
        
        uuid_normalized = "A1B2C3D4E5F67890ABCDEF1234567890"
        result = organizer.normalize_uuid(uuid_normalized)
        
        assert result == uuid_normalized
    
    def test_load_vpd(self, sample_vpd_file, temp_dir):
        """Test loading VPD file."""
        logger = logging.getLogger(__name__)
        organizer = VPDOrganizer(
            vpd_path=str(sample_vpd_file),
            target_dir=str(temp_dir / "target"),
            dry_run=True,
            logger=logger
        )
        
        data = organizer.load_vpd()
        
        assert data is not None
        assert "projinfo" in data
        assert "imagelist" in data
        assert "timeline" in data
    
    def test_extract_resources(self, sample_vpd_file, temp_dir):
        """Test extracting resources from VPD."""
        logger = logging.getLogger(__name__)
        organizer = VPDOrganizer(
            vpd_path=str(sample_vpd_file),
            target_dir=str(temp_dir / "target"),
            dry_run=True,
            logger=logger
        )
        
        organizer.load_vpd()
        resources = organizer.extract_resources()
        
        # conftest creates 2 images only (audio is in timeline but not in imagelist)
        assert len(resources) == 2  # 2 images
        assert all(r.resource_type == 'image' for r in resources.values())
    
    def test_extract_timeline_blocks(self, sample_vpd_file, temp_dir):
        """Test extracting timeline blocks."""
        logger = logging.getLogger(__name__)
        organizer = VPDOrganizer(
            vpd_path=str(sample_vpd_file),
            target_dir=str(temp_dir / "target"),
            dry_run=True,
            logger=logger
        )
        
        organizer.load_vpd()
        organizer.extract_resources()
        blocks = organizer.extract_timeline_blocks()
        
        # Sample VPD has 3 timeline blocks (2 image blocks + 1 audio block)
        assert len(blocks) == 3
        assert any(b.tstart == 0 for b in blocks)
        assert any(b.tstart == 5000 for b in blocks)
    
    def test_link_timeline_to_resources(self, sample_vpd_file, temp_dir):
        """Test linking timeline blocks to resources."""
        logger = logging.getLogger(__name__)
        organizer = VPDOrganizer(
            vpd_path=str(sample_vpd_file),
            target_dir=str(temp_dir / "target"),
            dry_run=True,
            logger=logger
        )
        
        organizer.load_vpd()
        organizer.extract_resources()
        organizer.extract_timeline_blocks()
        organizer.link_timeline_to_resources()
        
        # Check that resources were linked
        used_resources = [r for r in organizer.resources.values() if r.timeline_uses]
        assert len(used_resources) > 0
    
    def test_assign_sequence_numbers(self, sample_vpd_file, temp_dir):
        """Test sequence number assignment."""
        logger = logging.getLogger(__name__)
        organizer = VPDOrganizer(
            vpd_path=str(sample_vpd_file),
            target_dir=str(temp_dir / "target"),
            dry_run=True,
            logger=logger
        )
        
        organizer.load_vpd()
        organizer.extract_resources()
        organizer.extract_timeline_blocks()
        organizer.link_timeline_to_resources()
        organizer.assign_sequence_numbers()
        
        # Check that used resources have sequence numbers
        used_resources = [r for r in organizer.resources.values() if r.timeline_uses]
        assert len(used_resources) > 0
        assert all(r.sequence_number is not None for r in used_resources)
        
        # Check sequence numbers are in order
        sequences = sorted([r.sequence_number for r in used_resources])
        assert sequences == list(range(1, len(used_resources) + 1))
    
    def test_clean_filename_removes_sequence_pattern(self):
        """Test that existing sequence patterns are removed from filenames."""
        import re
        
        # Test the regex pattern used in organize script
        pattern = r'^\d{4}_[^_]+_Track_'
        
        test_cases = [
            ("0001_Video_Track_image.jpg", "image.jpg"),
            ("0021_Audio_Track_sound.mp3", "sound.mp3"),
            ("1234_My_Track_file.png", "file.png"),
            ("image.jpg", "image.jpg"),  # No pattern to remove
        ]
        
        for input_name, expected in test_cases:
            result = re.sub(pattern, '', input_name)
            assert result == expected, f"Expected {expected}, got {result} for {input_name}"


class TestMediaResource:
    """Test MediaResource class."""
    
    def test_media_resource_creation(self):
        """Test MediaResource initialization."""
        resource = MediaResource(
            uuid="ABC123",
            path="/path/to/file.jpg",
            title="Test Image",
            resource_type="image",
            duration=5000
        )
        
        assert resource.uuid == "ABC123"
        assert resource.path == "/path/to/file.jpg"
        assert resource.title == "Test Image"
        assert resource.resource_type == "image"
        assert resource.sequence_number is None
        assert resource.timeline_uses == []


class TestTimelineBlock:
    """Test TimelineBlock class."""
    
    def test_timeline_block_creation(self):
        """Test TimelineBlock initialization."""
        block = TimelineBlock(
            resid="ABC123",
            tstart=1000,
            block_type="ImageFileBlock",
            track_name="Video Track",
            block_data={}
        )
        
        assert block.resid == "ABC123"
        assert block.track_name == "Video Track"
        assert block.tstart == 1000
        assert block.block_type == "ImageFileBlock"


def test_imports():
    """Test that all necessary modules can be imported."""
    from scripts import organize
    from scripts import repair
    
    assert hasattr(organize, 'VPDOrganizer')
    assert hasattr(repair, 'VPDRepair')
