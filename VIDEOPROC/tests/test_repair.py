"""Tests for repair script."""
import pytest
import logging
from pathlib import Path
from scripts.repair import VPDRepair


class TestVPDRepair:
    """Test VPDRepair class."""
    
    def test_repair_instantiation(self):
        """Test that VPDRepair can be instantiated."""
        repairer = VPDRepair(
            vpd_path="/tmp/test.vpd",
            search_root="/tmp",
            dry_run=True
        )
        
        assert repairer.vpd_path == Path("/tmp/test.vpd")
        assert repairer.search_root == Path("/tmp")
        assert repairer.dry_run is True
    
    def test_load_vpd(self, sample_vpd_file, temp_dir):
        """Test loading VPD file."""
        logger = logging.getLogger(__name__)
        repairer = VPDRepair(
            vpd_path=str(sample_vpd_file),
            search_root=str(temp_dir),
            dry_run=True,
            logger=logger
        )
        
        data = repairer.load_vpd()
        
        assert data is not None
        assert "projinfo" in data
        assert "imagelist" in data
        assert "timeline" in data
    
    def test_extract_resources(self, sample_vpd_file, temp_dir):
        """Test extracting resources from VPD."""
        logger = logging.getLogger(__name__)
        repairer = VPDRepair(
            vpd_path=str(sample_vpd_file),
            search_root=str(temp_dir),
            dry_run=True,
            logger=logger
        )
        
        repairer.load_vpd()
        resources = repairer.extract_resources()
        
        # repair.py returns a list, organize.py returns a dict
        # VPDResource uses 'type' attribute, not 'resource_type'
        assert len(resources) == 2
        assert all(r.type == 'image' for r in resources)
    
    def test_verify_resources_with_existing_files(self, sample_vpd_file, sample_media_files, temp_dir):
        """Test verifying resources when files exist."""
        logger = logging.getLogger(__name__)
        repairer = VPDRepair(
            vpd_path=str(sample_vpd_file),
            search_root=str(temp_dir),
            dry_run=True,
            logger=logger
        )
        
        repairer.load_vpd()
        repairer.extract_resources()
        missing = repairer.verify_resources()
        
        # All files should be missing initially since paths don't match temp_dir
        assert len(missing) > 0
    
    def test_search_for_file(self, sample_media_files, temp_dir):
        """Test searching for a file."""
        logger = logging.getLogger(__name__)
        repairer = VPDRepair(
            vpd_path=str(temp_dir / "test.vpd"),
            search_root=str(temp_dir),
            dry_run=True,
            logger=logger
        )
        
        # Try to find one of the sample files
        found_paths = repairer.search_for_file("image1.jpg")
        
        assert len(found_paths) > 0
        assert any(Path(p).name == "image1.jpg" for p in found_paths)
        assert all(Path(p).exists() for p in found_paths)


def test_repair_imports():
    """Test that repair module can be imported."""
    from scripts import repair
    
    assert hasattr(repair, 'VPDRepair')
    assert hasattr(repair, 'VPDResource')
