"""Tests for immich_connection module."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from immich_connection import ImmichConnection


@pytest.fixture
def mock_connection():
    """Create a mock ImmichConnection."""
    return ImmichConnection("http://test-immich.com", "test-api-key")


class TestImmichConnection:
    """Tests for ImmichConnection class."""
    
    def test_init(self, mock_connection):
        """Test initialization."""
        assert mock_connection.base_url == "http://test-immich.com"
        assert mock_connection.api_key == "test-api-key"
        assert "x-api-key" in mock_connection.session.headers
        assert mock_connection.session.headers["x-api-key"] == "test-api-key"
    
    def test_base_url_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        conn = ImmichConnection("http://test-immich.com/", "key")
        assert conn.base_url == "http://test-immich.com"
    
    @patch('immich_connection.requests.Session.get')
    def test_validate_connection_success(self, mock_get, mock_connection):
        """Test successful connection validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = mock_connection.validate_connection()
        
        assert result is True
        mock_get.assert_called_once_with("http://test-immich.com/api/server/ping")
    
    @patch('immich_connection.requests.Session.get')
    def test_validate_connection_failure(self, mock_get, mock_connection):
        """Test failed connection validation."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = mock_connection.validate_connection()
        
        assert result is False
    
    @patch('immich_connection.requests.Session.get')
    def test_get_album_assets(self, mock_get, mock_connection):
        """Test fetching assets from an album."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assets": [
                {"id": "asset1", "originalFileName": "test1.jpg"},
                {"id": "asset2", "originalFileName": "test2.jpg"}
            ]
        }
        mock_get.return_value = mock_response
        
        assets = mock_connection._get_album_assets("album123")
        
        assert len(assets) == 2
        assert assets[0]["id"] == "asset1"
        assert "albums" in assets[0]
        assert "album123" in assets[0]["albums"]
    
    @patch('immich_connection.requests.Session.post')
    def test_search_assets_simple(self, mock_post, mock_connection):
        """Test searching assets with simple response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assets": {
                "items": [
                    {"id": "asset1", "originalFileName": "test1.jpg"}
                ],
                "nextPage": None
            }
        }
        mock_post.return_value = mock_response
        
        assets = mock_connection.search_assets(updated_after="2025-01-01T00:00:00Z")
        
        assert len(assets) == 1
        assert assets[0]["id"] == "asset1"
    
    @patch('immich_connection.requests.Session.post')
    def test_search_assets_pagination(self, mock_post, mock_connection):
        """Test searching assets with pagination."""
        # First page
        response1 = Mock()
        response1.status_code = 200
        response1.json.return_value = {
            "assets": {
                "items": [{"id": "asset1"}],
                "nextPage": 2
            }
        }
        
        # Second page
        response2 = Mock()
        response2.status_code = 200
        response2.json.return_value = {
            "assets": {
                "items": [{"id": "asset2"}],
                "nextPage": None
            }
        }
        
        mock_post.side_effect = [response1, response2]
        
        assets = mock_connection.search_assets()
        
        assert len(assets) == 2
        assert assets[0]["id"] == "asset1"
        assert assets[1]["id"] == "asset2"
        assert mock_post.call_count == 2
    
    @patch('immich_connection.requests.Session.post')
    def test_search_assets_with_album(self, mock_post, mock_connection):
        """Test that search with album_id uses album endpoint instead."""
        with patch.object(mock_connection, '_get_album_assets') as mock_album:
            mock_album.return_value = [{"id": "asset1"}]
            
            assets = mock_connection.search_assets(album_id="album123")
            
            mock_album.assert_called_once_with("album123")
            mock_post.assert_not_called()
            assert len(assets) == 1
    
    @patch('immich_connection.requests.Session.get')
    def test_get_asset_details_success(self, mock_get, mock_connection):
        """Test getting asset details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "asset1",
            "originalFileName": "test.jpg",
            "description": "Test image"
        }
        mock_get.return_value = mock_response
        
        details = mock_connection.get_asset_details("asset1")
        
        assert details is not None
        assert details["id"] == "asset1"
        assert details["description"] == "Test image"
    
    @patch('immich_connection.requests.Session.get')
    def test_get_asset_details_not_found(self, mock_get, mock_connection):
        """Test getting asset details for non-existent asset."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        details = mock_connection.get_asset_details("nonexistent")
        
        assert details is None
    
    @patch('immich_connection.requests.Session.get')
    def test_get_album_info(self, mock_get, mock_connection):
        """Test getting album info."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "album1",
            "albumName": "Test Album",
            "assets": []
        }
        mock_get.return_value = mock_response
        
        info = mock_connection.get_album_info("album1")
        
        assert info is not None
        assert info["albumName"] == "Test Album"
    
    def test_extract_assets_from_response_format1(self, mock_connection):
        """Test extracting assets from format 1."""
        data = {
            "assets": {
                "items": [{"id": "asset1"}, {"id": "asset2"}]
            }
        }
        
        assets = mock_connection._extract_assets_from_response(data)
        
        assert len(assets) == 2
        assert assets[0]["id"] == "asset1"
    
    def test_extract_assets_from_response_format2(self, mock_connection):
        """Test extracting assets from format 2 (list)."""
        data = {"assets": [{"id": "asset1"}]}
        
        assets = mock_connection._extract_assets_from_response(data)
        
        assert len(assets) == 1
    
    def test_extract_assets_from_response_format3(self, mock_connection):
        """Test extracting assets from format 3 (direct list)."""
        data = [{"id": "asset1"}, {"id": "asset2"}]
        
        assets = mock_connection._extract_assets_from_response(data)
        
        assert len(assets) == 2
    
    def test_get_next_page_nested(self, mock_connection):
        """Test getting next page from nested structure."""
        data = {"assets": {"nextPage": 2}}
        
        next_page = mock_connection._get_next_page(data)
        
        assert next_page == 2
    
    def test_get_next_page_top_level(self, mock_connection):
        """Test getting next page from top level."""
        data = {"nextPage": 3}
        
        next_page = mock_connection._get_next_page(data)
        
        assert next_page == 3
    
    def test_get_next_page_none(self, mock_connection):
        """Test getting next page when there is none."""
        data = {"assets": {}}
        
        next_page = mock_connection._get_next_page(data)
        
        assert next_page is None
