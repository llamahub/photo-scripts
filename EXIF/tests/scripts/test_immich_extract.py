import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "COMMON" / "src"))
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
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


if __name__ == "__main__":
    unittest.main()
