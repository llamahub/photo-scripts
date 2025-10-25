import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "COMMON" / "src" / "common")
)
from temp import TempManager
import immich_extract


class TestImmichAPI(unittest.TestCase):
    @patch("immich_extract.requests.Session")
    def test_get_album_assets(self, mock_session):
        api = immich_extract.ImmichAPI("http://test", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"assets": [1, 2, 3]}
        mock_resp.raise_for_status = MagicMock()
        api.session.get.return_value = mock_resp
        assets = api.get_album_assets("albumid")
        self.assertEqual(assets, [1, 2, 3])
        api.session.get.assert_called_once()

    @patch("immich_extract.requests.Session")
    def test_get_asset_details(self, mock_session):
        api = immich_extract.ImmichAPI("http://test", "key")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "assetid"}
        api.session.get.return_value = mock_resp
        details = api.get_asset_details("assetid")
        self.assertEqual(details, {"id": "assetid"})

    @patch("immich_extract.requests.Session")
    def test_list_albums(self, mock_session):
        api = immich_extract.ImmichAPI("http://test", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "1"}]
        mock_resp.raise_for_status = MagicMock()
        api.session.get.return_value = mock_resp
        albums = api.list_albums()
        self.assertEqual(albums, [{"id": "1"}])


class TestExifToolManager(unittest.TestCase):
    @patch("immich_extract.subprocess.run")
    def test_check_exiftool_success(self, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(immich_extract.ExifToolManager.check_exiftool())

    @patch("immich_extract.subprocess.run", side_effect=Exception)
    def test_check_exiftool_fail(self, mock_run):
        self.assertFalse(immich_extract.ExifToolManager.check_exiftool())

    @patch("immich_extract.os.path.exists", return_value=False)
    def test_update_exif_file_not_found(self, mock_exists):
        result = immich_extract.ExifToolManager.update_exif(
            "nofile.jpg", "desc", ["tag"], dry_run=True
        )
        self.assertEqual(result, "error")

    @patch("immich_extract.subprocess.run")
    @patch("immich_extract.os.path.exists", return_value=True)
    def test_update_exif_dry_run(self, mock_exists, mock_run):
        result = immich_extract.ExifToolManager.update_exif(
            "file.jpg", "desc", ["tag"], dry_run=True
        )
        self.assertEqual(result, "updated")


class TestFindImageFile(unittest.TestCase):
    def test_find_image_file_found(self):
        with TempManager.auto_cleanup_dir("immich_test") as temp_dir:
            with patch("immich_extract.Path.rglob") as mock_rglob:
                mock_file = MagicMock()
                mock_file.is_file.return_value = True
                mock_rglob.return_value = [mock_file]
                result = immich_extract.find_image_file("test.jpg", [str(temp_dir)])
                self.assertTrue(result)

    def test_find_image_file_not_found(self):
        with TempManager.auto_cleanup_dir("immich_test") as temp_dir:
            with patch("immich_extract.Path.rglob", return_value=[]):
                result = immich_extract.find_image_file("test.jpg", [str(temp_dir)])
                self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
