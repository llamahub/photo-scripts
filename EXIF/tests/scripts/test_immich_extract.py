import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "COMMON" / "src"))
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import logging
# Import logging setup to enable audit() method on Logger
import common.logging
from common.temp import TempManager
from exif.immich_extract_support import ImmichAPI, ExifToolManager, find_image_file
from exif.immich_extractor import ImmichExtractor


class TestImmichExtractor(unittest.TestCase):
    @patch("os.path.exists", return_value=True)
    @patch("exif.immich_extractor.ImmichAPI")
    @patch("exif.immich_extractor.ExifToolManager")
    @patch("exif.immich_extractor.find_image_file")
    @patch("exif.image_analyzer.ImageAnalyzer")
    @patch("builtins.open")
    @patch("json.dump")
    @patch("json.load")
    def test_run_minimal_album(
        self,
        mock_json_load,
        mock_json_dump,
        mock_open,
        mock_ImageAnalyzer,
        mock_find_image_file,
        mock_ExifToolManager,
        mock_ImmichAPI,
        mock_exists,
    ):
        # Setup mocks
        mock_api = mock_ImmichAPI.return_value
        mock_api.list_albums.return_value = []
        mock_api.get_album_assets.return_value = [
            {"id": "asset1", "originalFileName": "img1.jpg"}
        ]
        mock_api.get_asset_details.return_value = {
            "id": "asset1",
            "originalFileName": "img1.jpg",
            "tags": ["tag1"],
            "description": "desc",
        }
        # Mock session to prevent any real HTTP requests
        mock_api.session = MagicMock()
        mock_find_image_file.return_value = (
            __file__  # Use this test file as a dummy image
        )
        mock_ExifToolManager.update_exif.return_value = "updated"
        mock_ExifToolManager.check_exiftool.return_value = True
        mock_ImageAnalyzer.return_value.get_exif.return_value = {
            "Description": "desc",
            "Subject": ["tag1"],
            "DateTimeOriginal": "2020:01:01 12:00:00",
        }
        mock_json_load.return_value = {}

        # Create a temp dir for log/cache
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                import logging

                logger = logging.getLogger("test_immich_extractor")
                logger.setLevel(logging.DEBUG)
                ch = logging.StreamHandler()
                ch.setLevel(logging.DEBUG)
                logger.addHandler(ch)
                extractor = ImmichExtractor(
                    url="http://test",
                    api_key="key",
                    search_path=tmpdir,
                    album="albumid",
                    logger=logger,
                )
                extractor.search = False  # Ensure we do not enter the search loop
                extractor.run()
            finally:
                os.chdir(old_cwd)


class TestImmichAPI(unittest.TestCase):
    @patch("exif.immich_extract_support.requests.Session")
    def test_get_album_assets(self, mock_session):
        api = ImmichAPI("http://test", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"assets": [1, 2, 3]}
        mock_resp.raise_for_status = MagicMock()
        api.session.get.return_value = mock_resp
        assets = api.get_album_assets("albumid")
        self.assertEqual(assets, [1, 2, 3])
        api.session.get.assert_called_once()

    @patch("exif.immich_extract_support.requests.Session")
    def test_get_asset_details(self, mock_session):
        api = ImmichAPI("http://test", "key")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "assetid"}
        api.session.get.return_value = mock_resp
        details = api.get_asset_details("assetid")
        self.assertEqual(details, {"id": "assetid"})

    @patch("exif.immich_extract_support.requests.Session")
    def test_list_albums(self, mock_session):
        api = ImmichAPI("http://test", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "1"}]
        mock_resp.raise_for_status = MagicMock()
        api.session.get.return_value = mock_resp
        albums = api.list_albums()
        self.assertEqual(albums, [{"id": "1"}])


class TestExifToolManager(unittest.TestCase):

    @patch("exif.immich_extract_support.os.path.exists", return_value=True)
    def test_update_exif_heic_subject(self, mock_exists):
        # Simulate exiftool returning Subject for HEIC (tags match)
        with patch("exif.immich_extract_support.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(
                    stdout='[{"Description": "desc", "Subject": ["tag1", "tag2"], "DateTimeOriginal": "2020:01:01 12:00:00"}]',
                    returncode=0,
                ),
            ]
            result = ExifToolManager.update_exif(
                "file.HEIC",
                "desc",
                ["tag1", "tag2"],
                dry_run=False,
                date_exif="2020:01:01 12:00:00",
                skip_if_unchanged=True,
            )
            self.assertEqual(result, "skipped")
        # Simulate exiftool returning Subject for HEIC (tags differ, triggers update)
        with patch("exif.immich_extract_support.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(
                    stdout='[{"Description": "desc", "Subject": ["tag1"], "DateTimeOriginal": "2020:01:01 12:00:00"}]',
                    returncode=0,
                ),
                MagicMock(returncode=0),  # update call
            ]
            result = ExifToolManager.update_exif(
                "file.heic",
                "desc",
                ["tag1", "tag2"],
                dry_run=False,
                date_exif="2020:01:01 12:00:00",
                skip_if_unchanged=True,
            )
            self.assertEqual(result, "updated")

    @patch("exif.immich_extract_support.os.path.exists", return_value=True)
    def test_update_exif_jpeg_keywords(self, mock_exists):
        # Simulate exiftool returning Keywords for JPEG (tags match)
        with patch("exif.immich_extract_support.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(
                    stdout='[{"Description": "desc", "Keywords": ["tag1", "tag2"], "DateTimeOriginal": "2020:01:01 12:00:00"}]',
                    returncode=0,
                ),
            ]
            result = ExifToolManager.update_exif(
                "file.jpg",
                "desc",
                ["tag1", "tag2"],
                dry_run=False,
                date_exif="2020:01:01 12:00:00",
                skip_if_unchanged=True,
            )
            self.assertEqual(result, "skipped")
        # Simulate exiftool returning Keywords for JPEG (tags differ, triggers update)
        with patch("exif.immich_extract_support.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(
                    stdout='[{"Description": "desc", "Keywords": ["tag1"], "DateTimeOriginal": "2020:01:01 12:00:00"}]',
                    returncode=0,
                ),
                MagicMock(returncode=0),  # update call
            ]
            result = ExifToolManager.update_exif(
                "file.JPG",
                "desc",
                ["tag1", "tag2"],
                dry_run=False,
                date_exif="2020:01:01 12:00:00",
                skip_if_unchanged=True,
            )
            self.assertEqual(result, "updated")

    @patch("exif.immich_extract_support.subprocess.run")
    def test_check_exiftool_success(self, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(ExifToolManager.check_exiftool())

    @patch("exif.immich_extract_support.subprocess.run", side_effect=Exception)
    def test_check_exiftool_fail(self, mock_run):
        self.assertFalse(ExifToolManager.check_exiftool())

    @patch("exif.immich_extract_support.os.path.exists", return_value=False)
    def test_update_exif_file_not_found(self, mock_exists):
        result = ExifToolManager.update_exif(
            "nofile.jpg", "desc", ["tag"], dry_run=True
        )
        self.assertEqual(result, "error")

    @patch("exif.immich_extract_support.os.path.exists", return_value=True)
    def test_update_exif_dry_run(self, mock_exists):
        # Simulate exiftool returning Keywords for JPEG
        with patch("exif.immich_extract_support.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='[{"Description": "desc", "Keywords": ["tag"], "DateTimeOriginal": "2020:01:01 12:00:00"}]',
                returncode=0,
            )
            result = ExifToolManager.update_exif(
                "file.jpg", "desc", ["tag"], dry_run=True
            )
            self.assertEqual(result, "updated")


class TestFindImageFile(unittest.TestCase):
    def test_find_image_file_found(self):
        with TempManager.auto_cleanup_dir("immich_test") as temp_dir:
            with patch("exif.immich_extract_support.Path.rglob") as mock_rglob:
                mock_file = MagicMock()
                mock_file.is_file.return_value = True
                mock_rglob.return_value = [mock_file]
                result = find_image_file("test.jpg", str(temp_dir))
                self.assertTrue(result)

    def test_find_image_file_not_found(self):
        with TempManager.auto_cleanup_dir("immich_test") as temp_dir:
            with patch("exif.immich_extract_support.Path.rglob", return_value=[]):
                result = find_image_file("test.jpg", str(temp_dir))
                self.assertIsNone(result)


class TestDisableSidecars(unittest.TestCase):
    """Tests for the --disable-sidecars feature"""

    def test_disable_sidecar_files_xmp_only(self):
        """Test renaming .xmp sidecar files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image and sidecar
            image_path = os.path.join(tmpdir, "test.jpg")
            xmp_path = os.path.join(tmpdir, "test.jpg.xmp")
            
            # Create dummy files
            open(image_path, 'w').close()
            open(xmp_path, 'w').close()
            
            import logging
            logger = logging.getLogger("test_disable_sidecars")
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=False,
            )
            
            # Call the method with the image path in processed_files
            result = extractor._disable_sidecar_files({image_path})
            
            # Verify sidecar was renamed
            self.assertEqual(result, 1)
            self.assertFalse(os.path.exists(xmp_path))
            self.assertTrue(os.path.exists(f"{xmp_path}.bak"))

    def test_disable_sidecar_files_json_only(self):
        """Test renaming .supplemental-metadata.json sidecar files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image and sidecar
            image_path = os.path.join(tmpdir, "test.jpg")
            json_path = os.path.join(tmpdir, "test.jpg.supplemental-metadata.json")
            
            # Create dummy files
            open(image_path, 'w').close()
            open(json_path, 'w').close()
            
            import logging
            logger = logging.getLogger("test_disable_sidecars")
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=False,
            )
            
            # Call the method with the image path in processed_files
            result = extractor._disable_sidecar_files({image_path})
            
            # Verify sidecar was renamed
            self.assertEqual(result, 1)
            self.assertFalse(os.path.exists(json_path))
            self.assertTrue(os.path.exists(f"{json_path}.bak"))

    def test_disable_sidecar_files_both_types(self):
        """Test renaming both .xmp and .supplemental-metadata.json sidecars"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image and sidecars
            image_path = os.path.join(tmpdir, "test.jpg")
            xmp_path = os.path.join(tmpdir, "test.jpg.xmp")
            json_path = os.path.join(tmpdir, "test.jpg.supplemental-metadata.json")
            
            # Create dummy files
            open(image_path, 'w').close()
            open(xmp_path, 'w').close()
            open(json_path, 'w').close()
            
            import logging
            logger = logging.getLogger("test_disable_sidecars")
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=False,
            )
            
            # Call the method with the image path in processed_files
            result = extractor._disable_sidecar_files({image_path})
            
            # Verify both sidecars were renamed
            self.assertEqual(result, 2)
            self.assertFalse(os.path.exists(xmp_path))
            self.assertFalse(os.path.exists(json_path))
            self.assertTrue(os.path.exists(f"{xmp_path}.bak"))
            self.assertTrue(os.path.exists(f"{json_path}.bak"))

    def test_disable_sidecar_files_no_sidecars(self):
        """Test when no sidecar files exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image without sidecars
            image_path = os.path.join(tmpdir, "test.jpg")
            open(image_path, 'w').close()
            
            import logging
            logger = logging.getLogger("test_disable_sidecars")
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=False,
            )
            
            # Call the method with the image path in processed_files
            result = extractor._disable_sidecar_files({image_path})
            
            # Verify count is 0
            self.assertEqual(result, 0)

    def test_disable_sidecar_files_dry_run(self):
        """Test that dry-run mode doesn't actually rename files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image and sidecar
            image_path = os.path.join(tmpdir, "test.jpg")
            xmp_path = os.path.join(tmpdir, "test.jpg.xmp")
            json_path = os.path.join(tmpdir, "test.jpg.supplemental-metadata.json")
            
            # Create dummy files
            open(image_path, 'w').close()
            open(xmp_path, 'w').close()
            open(json_path, 'w').close()
            
            import logging
            logger = logging.getLogger("test_disable_sidecars")
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=True,  # Enable dry-run
            )
            
            # Call the method with the image path in processed_files
            result = extractor._disable_sidecar_files({image_path})
            
            # Verify count is still 2 (operation counted but not performed)
            self.assertEqual(result, 2)
            # Verify files were NOT actually renamed
            self.assertTrue(os.path.exists(xmp_path))
            self.assertTrue(os.path.exists(json_path))
            self.assertFalse(os.path.exists(f"{xmp_path}.bak"))
            self.assertFalse(os.path.exists(f"{json_path}.bak"))

    def test_disable_sidecar_files_multiple_images(self):
        """Test disabling sidecars for multiple images"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple images with sidecars
            images = []
            for i in range(3):
                image_path = os.path.join(tmpdir, f"test{i}.jpg")
                xmp_path = os.path.join(tmpdir, f"test{i}.jpg.xmp")
                open(image_path, 'w').close()
                open(xmp_path, 'w').close()
                images.append(image_path)
            
            import logging
            logger = logging.getLogger("test_disable_sidecars")
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=False,
            )
            
            # Call the method with all image paths
            result = extractor._disable_sidecar_files(set(images))
            
            # Verify all sidecars were renamed (3 files)
            self.assertEqual(result, 3)
            for i in range(3):
                xmp_path = os.path.join(tmpdir, f"test{i}.jpg.xmp")
                self.assertFalse(os.path.exists(xmp_path))
                self.assertTrue(os.path.exists(f"{xmp_path}.bak"))

    def test_disable_sidecar_files_preserves_data(self):
        """Test that renamed files preserve their content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image and sidecar with content
            image_path = os.path.join(tmpdir, "test.jpg")
            xmp_path = os.path.join(tmpdir, "test.jpg.xmp")
            xmp_content = "<rdf>test metadata</rdf>"
            
            open(image_path, 'w').close()
            with open(xmp_path, 'w') as f:
                f.write(xmp_content)
            
            import logging
            logger = logging.getLogger("test_disable_sidecars")
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=False,
            )
            
            # Call the method
            extractor._disable_sidecar_files({image_path})
            
            # Verify content was preserved
            with open(f"{xmp_path}.bak", 'r') as f:
                content = f.read()
            self.assertEqual(content, xmp_content)

    def test_disable_sidecar_files_empty_set(self):
        """Test with empty processed_files set - should disable ALL sidecars in search path"""
        import logging
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = logging.getLogger("test_disable_sidecars")
            
            # Create test sidecars
            img = os.path.join(tmpdir, "test.jpg")
            xmp = f"{img}.xmp"
            json_file = f"{img}.supplemental-metadata.json"
            
            open(img, 'w').close()
            open(xmp, 'w').close()
            open(json_file, 'w').close()
            
            extractor = ImmichExtractor(
                url="http://test",
                api_key="key",
                search_path=tmpdir,
                album="test",
                disable_sidecars=True,
                logger=logger,
                dry_run=False,
            )
            
            # Call the method with empty set - should still find and disable all sidecars
            result = extractor._disable_sidecar_files(set())
            
            # Verify all sidecars were disabled (now processes ALL sidecars in path)
            self.assertEqual(result, 2)
            self.assertFalse(os.path.exists(xmp))
            self.assertFalse(os.path.exists(json_file))
            self.assertTrue(os.path.exists(f"{xmp}.bak"))
            self.assertTrue(os.path.exists(f"{json_file}.bak"))


class TestTimestampOffsetEquivalence(unittest.TestCase):
    """Test that offset_equivalent logic works correctly in different scenarios."""
    
    @patch("os.path.exists", return_value=True)
    @patch("exif.immich_extractor.ImmichAPI")
    @patch("exif.immich_extractor.ExifToolManager")
    @patch("exif.immich_extractor.find_image_file")
    @patch("exif.image_analyzer.ImageAnalyzer")
    @patch("builtins.open")
    @patch("json.dump")
    @patch("json.load")
    def test_offset_equivalent_skip_all(
        self,
        mock_json_load,
        mock_json_dump,
        mock_open,
        mock_ImageAnalyzer,
        mock_find_image_file,
        mock_ExifToolManager,
        mock_ImmichAPI,
        mock_exists,
    ):
        """Test scenario 1: Timestamps are offset_equivalent AND tags/description match - should skip entirely."""
        mock_api = mock_ImmichAPI.return_value
        mock_api.list_albums.return_value = []
        mock_api.get_album_assets.return_value = [
            {"id": "asset1", "originalFileName": "img1.jpg"}
        ]
        mock_api.get_asset_details.return_value = {
            "id": "asset1",
            "originalFileName": "img1.jpg",
            "tags": ["tag1"],
            "description": "desc",
        }
        mock_api.session = MagicMock()
        mock_find_image_file.return_value = __file__
        mock_ExifToolManager.check_exiftool.return_value = True
        
        # Current EXIF: 12:00:00 in +05:00 timezone (which is 07:00:00 UTC)
        # Target: 07:00:00 in +00:00 timezone (which is also 07:00:00 UTC)
        # Same tags and description - should skip entirely
        analyzer_instance = mock_ImageAnalyzer.return_value
        analyzer_instance.get_exif.return_value = {
            "Description": "desc",
            "Subject": ["tag1"],
            "DateTimeOriginal": "2020:01:01 12:00:00",
            "OffsetTimeOriginal": "+05:00",
        }
        mock_json_load.return_value = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                # Create a fake image file
                test_image = Path(tmpdir) / "img1.jpg"
                test_image.write_text("fake image")
                mock_find_image_file.return_value = str(test_image)
                
                logger = logging.getLogger("test_offset_equivalent")
                logger.setLevel(logging.DEBUG)
                extractor = ImmichExtractor(
                    url="http://test",
                    api_key="key",
                    search_path=tmpdir,
                    album="albumid",
                    logger=logger,
                )
                extractor.search = False
                
                # Mock the API to return proper date for immich
                mock_api.get_asset_details.return_value = {
                    "id": "asset1",
                    "originalFileName": "img1.jpg",
                    "tags": ["tag1"],
                    "description": "desc",
                    "exifInfo": {
                        "dateTimeOriginal": "2020-01-01T07:00:00.000Z"  # UTC time
                    }
                }
                
                result = extractor.run()
                
                # Should NOT have called update_exif at all
                mock_ExifToolManager.update_exif.assert_not_called()
                
                # Check that status was offset_equivalent
                self.assertIn("offset_equivalent", result.get("audit_status_counts", {}))
            finally:
                os.chdir(old_cwd)

    @patch("os.path.exists", return_value=True)
    @patch("exif.immich_extractor.ImmichAPI")
    @patch("exif.immich_extractor.ExifToolManager")
    @patch("exif.immich_extractor.find_image_file")
    @patch("exif.image_analyzer.ImageAnalyzer")
    @patch("builtins.open")
    @patch("json.dump")
    @patch("json.load")
    def test_offset_equivalent_update_tags_only(
        self,
        mock_json_load,
        mock_json_dump,
        mock_open,
        mock_ImageAnalyzer,
        mock_find_image_file,
        mock_ExifToolManager,
        mock_ImmichAPI,
        mock_exists,
    ):
        """Test scenario 2: Timestamps are offset_equivalent BUT tags differ - should update tags only (date=None)."""
        mock_api = mock_ImmichAPI.return_value
        mock_api.list_albums.return_value = []
        mock_api.get_album_assets.return_value = [
            {"id": "asset1", "originalFileName": "img1.jpg"}
        ]
        mock_api.get_asset_details.return_value = {
            "id": "asset1",
            "originalFileName": "img1.jpg",
            "tags": ["tag2", "tag3"],  # Different tags
            "description": "desc",
        }
        mock_api.session = MagicMock()
        mock_find_image_file.return_value = __file__
        mock_ExifToolManager.check_exiftool.return_value = True
        mock_ExifToolManager.update_exif.return_value = "updated"
        
        # Same timestamp in different timezone, but different tags
        analyzer_instance = mock_ImageAnalyzer.return_value
        analyzer_instance.get_exif.return_value = {
            "Description": "desc",
            "Subject": ["tag1"],  # Different from target
            "DateTimeOriginal": "2020:01:01 12:00:00",
            "OffsetTimeOriginal": "+05:00",
        }
        mock_json_load.return_value = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                # Create a fake image file
                test_image = Path(tmpdir) / "img1.jpg"
                test_image.write_text("fake image")
                mock_find_image_file.return_value = str(test_image)
                
                logger = logging.getLogger("test_offset_equivalent_tags")
                logger.setLevel(logging.DEBUG)
                extractor = ImmichExtractor(
                    url="http://test",
                    api_key="key",
                    search_path=tmpdir,
                    album="albumid",
                    logger=logger,
                )
                extractor.search = False
                
                # Mock the API to return proper date for immich
                mock_api.get_asset_details.return_value = {
                    "id": "asset1",
                    "originalFileName": "img1.jpg",
                    "tags": ["tag2", "tag3"],  # Different tags
                    "description": "desc",
                    "exifInfo": {
                        "dateTimeOriginal": "2020-01-01T07:00:00.000Z"  # UTC time
                    }
                }
                
                result = extractor.run()
                
                # Should have called update_exif with date=None (don't update timestamp)
                mock_ExifToolManager.update_exif.assert_called()
                call_args = mock_ExifToolManager.update_exif.call_args
                # Check if date_exif is None (passed as keyword argument)
                self.assertIsNone(call_args.kwargs.get("date_exif"))  # date should be None
                self.assertIsNone(call_args.kwargs.get("date_exif_offset"))  # offset should be None
            finally:
                os.chdir(old_cwd)

    @patch("os.path.exists", return_value=True)
    @patch("exif.immich_extractor.ImmichAPI")
    @patch("exif.immich_extractor.ExifToolManager")
    @patch("exif.immich_extractor.find_image_file")
    @patch("exif.image_analyzer.ImageAnalyzer")
    @patch("builtins.open")
    @patch("json.dump")
    @patch("json.load")
    def test_timestamps_differ_update_all(
        self,
        mock_json_load,
        mock_json_dump,
        mock_open,
        mock_ImageAnalyzer,
        mock_find_image_file,
        mock_ExifToolManager,
        mock_ImmichAPI,
        mock_exists,
    ):
        """Test scenario 3: Timestamps differ - should update everything including timestamp."""
        mock_api = mock_ImmichAPI.return_value
        mock_api.list_albums.return_value = []
        mock_api.get_album_assets.return_value = [
            {"id": "asset1", "originalFileName": "img1.jpg"}
        ]
        mock_api.get_asset_details.return_value = {
            "id": "asset1",
            "originalFileName": "img1.jpg",
            "tags": ["tag1"],
            "description": "desc",
        }
        mock_api.session = MagicMock()
        mock_find_image_file.return_value = __file__
        mock_ExifToolManager.check_exiftool.return_value = True
        mock_ExifToolManager.update_exif.return_value = "updated"  # Force updated status
        
        # Different timestamp (not offset_equivalent)
        analyzer_instance = mock_ImageAnalyzer.return_value
        analyzer_instance.get_exif.return_value = {
            "Description": "old desc",  # Make description different
            "Subject": ["tag1"],
            "DateTimeOriginal": "2020:01:01 15:00:00",  # Different time
            "OffsetTimeOriginal": "+05:00",
        }
        mock_json_load.return_value = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                # Create a fake image file
                test_image = Path(tmpdir) / "img1.jpg"
                test_image.write_text("fake image")
                mock_find_image_file.return_value = str(test_image)
                
                logger = logging.getLogger("test_timestamps_differ")
                logger.setLevel(logging.DEBUG)
                extractor = ImmichExtractor(
                    url="http://test",
                    api_key="key",
                    search_path=tmpdir,
                    album="albumid",
                    logger=logger,
                )
                extractor.search = False
                
                # Mock the API to return different UTC time
                mock_api.get_asset_details.return_value = {
                    "id": "asset1",
                    "originalFileName": "img1.jpg",
                    "tags": ["tag1"],
                    "description": "desc",
                    "exifInfo": {
                        "dateTimeOriginal": "2020-01-01T07:00:00.000Z"  # Different UTC time
                    }
                }
                
                result = extractor.run()
                
                # Should have called update_exif with actual date (update timestamp)
                mock_ExifToolManager.update_exif.assert_called()
                call_args = mock_ExifToolManager.update_exif.call_args
                # date_exif is the 5th positional argument (index 4)
                date_exif_val = call_args.args[4] if len(call_args.args) > 4 else None
                self.assertIsNotNone(date_exif_val)  # date should NOT be None
                self.assertEqual(call_args.kwargs.get("date_exif_offset"), "+00:00")  # offset should be UTC
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
