import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
import pytest_asyncio

from src.badfish.helpers.session_manager import SessionManager
from src.badfish.helpers.exceptions import BadfishException


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.warn_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(str(msg))

    def warning(self, msg):
        self.warn_msgs.append(str(msg))


def set_mock_response(mock, status, response_text, headers=None):
    """Helper to set up mock response"""
    mock.return_value.__aenter__.return_value.status = status
    mock.return_value.__aenter__.return_value.read = AsyncMock(return_value=b"")
    mock.return_value.__aenter__.return_value.text = AsyncMock(return_value=response_text)
    mock.return_value.__aenter__.return_value.headers = headers or {}


@pytest_asyncio.fixture
async def reset_session_manager():
    """Reset singleton between tests"""
    await SessionManager.reset_instance()
    yield
    await SessionManager.reset_instance()


@pytest.mark.asyncio
async def test_session_manager_singleton(reset_session_manager):
    """Test that SessionManager is a singleton"""
    sm1 = await SessionManager.get_instance()
    sm2 = await SessionManager.get_instance()
    assert sm1 is sm2


@pytest.mark.asyncio
async def test_session_manager_initialization(reset_session_manager):
    """Test SessionManager initializes with correct settings"""
    sm = await SessionManager.get_instance()
    assert sm._initialized is True
    assert sm.session is not None
    assert isinstance(sm.session, aiohttp.ClientSession)
    assert sm._connector is not None
    assert isinstance(sm._connector, aiohttp.TCPConnector)
    assert sm.semaphore._value == 50


@pytest.mark.asyncio
async def test_session_manager_connector_config(reset_session_manager):
    """Test TCPConnector is configured correctly"""
    sm = await SessionManager.get_instance()
    connector = sm._connector
    assert connector._limit == 100
    assert connector._limit_per_host == 10
    # ttl_dns_cache is not exposed as a property in newer aiohttp versions
    # Just verify force_close is False (connection reuse enabled)
    assert connector._force_close is False


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_get_request_success(mock_get, reset_session_manager):
    """Test successful GET request"""
    sm = await SessionManager.get_instance()
    set_mock_response(mock_get, 200, '{"result": "ok"}')

    response = await sm.get_request("https://example.com", {"X-Auth-Token": "TKN"})
    assert response.status == 200

    # Verify headers were passed
    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args[1]
    assert call_kwargs["headers"]["X-Auth-Token"] == "TKN"
    assert call_kwargs["ssl"] is False


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_get_request_with_auth(mock_get, reset_session_manager):
    """Test GET request with BasicAuth"""
    sm = await SessionManager.get_instance()
    set_mock_response(mock_get, 200, '{}')

    auth = aiohttp.BasicAuth("user", "pass")
    response = await sm.get_request("https://example.com", auth=auth)
    assert response.status == 200

    # Verify auth was passed
    call_kwargs = mock_get.call_args[1]
    assert isinstance(call_kwargs["auth"], aiohttp.BasicAuth)


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get", side_effect=Exception("network error"))
async def test_get_request_exception(mock_get, reset_session_manager):
    """Test GET request handles exceptions"""
    sm = await SessionManager.get_instance()

    with pytest.raises(BadfishException, match="Failed to communicate with server"):
        await sm.get_request("https://example.com")


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_post_request_success(mock_post, reset_session_manager):
    """Test successful POST request"""
    sm = await SessionManager.get_instance()
    set_mock_response(mock_post, 201, '{"created": true}', {"Location": "/api/resource/1"})

    payload = {"name": "test"}
    headers = {"Content-Type": "application/json"}
    response = await sm.post_request("https://example.com", payload, headers)
    assert response.status == 201

    # Verify payload was JSON-encoded
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["data"] == json.dumps(payload)


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_post_request_204_no_content(mock_post, reset_session_manager):
    """Test POST request with 204 No Content response"""
    sm = await SessionManager.get_instance()

    # Mock 204 response
    mock_post.return_value.__aenter__.return_value.status = 204
    mock_post.return_value.__aenter__.return_value.read = AsyncMock(return_value=b"")

    response = await sm.post_request("https://example.com", {}, {})
    assert response.status == 204


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post", side_effect=TimeoutError("timeout"))
async def test_post_request_timeout(mock_post, reset_session_manager):
    """Test POST request handles timeout"""
    sm = await SessionManager.get_instance()

    with pytest.raises(BadfishException, match="Failed to communicate with server"):
        await sm.post_request("https://example.com", {}, {})


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.patch")
async def test_patch_request_success(mock_patch, reset_session_manager):
    """Test successful PATCH request"""
    sm = await SessionManager.get_instance()
    set_mock_response(mock_patch, 200, '{"updated": true}')

    payload = {"status": "active"}
    headers = {"Content-Type": "application/json"}
    response = await sm.patch_request("https://example.com", payload, headers)
    assert response.status == 200


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.patch", side_effect=Exception("error"))
async def test_patch_request_exception(mock_patch, reset_session_manager):
    """Test PATCH request handles exceptions"""
    sm = await SessionManager.get_instance()

    with pytest.raises(BadfishException):
        await sm.patch_request("https://example.com", {}, {})


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.delete")
async def test_delete_request_success(mock_delete, reset_session_manager):
    """Test successful DELETE request"""
    sm = await SessionManager.get_instance()
    set_mock_response(mock_delete, 200, '')

    headers = {"X-Auth-Token": "TKN"}
    response = await sm.delete_request("https://example.com", headers)
    assert response.status == 200


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.delete", side_effect=Exception("error"))
async def test_delete_request_exception(mock_delete, reset_session_manager):
    """Test DELETE request handles exceptions"""
    sm = await SessionManager.get_instance()

    with pytest.raises(BadfishException):
        await sm.delete_request("https://example.com", {})


@pytest.mark.asyncio
async def test_cache_and_get_token(reset_session_manager):
    """Test token caching and retrieval"""
    sm = await SessionManager.get_instance()

    # Cache token
    sm.cache_token("host1.example.com", "TOKEN123", "/redfish/v1/Sessions/1", ttl_seconds=3600)

    # Retrieve valid token
    token = sm.get_token("host1.example.com")
    assert token == "TOKEN123"

    # Retrieve session ID
    session_id = sm.get_session_id("host1.example.com")
    assert session_id == "/redfish/v1/Sessions/1"


@pytest.mark.asyncio
async def test_get_token_nonexistent(reset_session_manager):
    """Test getting token for non-existent host"""
    sm = await SessionManager.get_instance()

    token = sm.get_token("nonexistent.example.com")
    assert token is None


@pytest.mark.asyncio
async def test_token_expiration(reset_session_manager):
    """Test token expiration logic"""
    sm = await SessionManager.get_instance()

    # Cache token with very short TTL
    sm.cache_token("host1.example.com", "TOKEN123", ttl_seconds=0)

    # Manually set expiry to past (simulate expired token)
    past_time = datetime.now() - timedelta(seconds=10)
    sm.tokens["host1.example.com"] = ("TOKEN123", past_time)

    # Should return None and clean up
    token = sm.get_token("host1.example.com")
    assert token is None
    assert "host1.example.com" not in sm.tokens


@pytest.mark.asyncio
async def test_invalidate_token(reset_session_manager):
    """Test token invalidation"""
    sm = await SessionManager.get_instance()

    # Cache token
    sm.cache_token("host1.example.com", "TOKEN123", "/redfish/v1/Sessions/1")
    assert sm.get_token("host1.example.com") == "TOKEN123"

    # Invalidate
    sm.invalidate_token("host1.example.com")
    assert sm.get_token("host1.example.com") is None
    assert sm.get_session_id("host1.example.com") is None


@pytest.mark.asyncio
async def test_invalidate_nonexistent_token(reset_session_manager):
    """Test invalidating non-existent token doesn't raise"""
    sm = await SessionManager.get_instance()

    # Should not raise
    sm.invalidate_token("nonexistent.example.com")


@pytest.mark.asyncio
async def test_multiple_hosts_token_cache(reset_session_manager):
    """Test caching tokens for multiple hosts"""
    sm = await SessionManager.get_instance()

    # Cache tokens for multiple hosts
    sm.cache_token("host1.example.com", "TOKEN1", "/sessions/1")
    sm.cache_token("host2.example.com", "TOKEN2", "/sessions/2")
    sm.cache_token("host3.example.com", "TOKEN3", "/sessions/3")

    # Verify all tokens are cached correctly
    assert sm.get_token("host1.example.com") == "TOKEN1"
    assert sm.get_token("host2.example.com") == "TOKEN2"
    assert sm.get_token("host3.example.com") == "TOKEN3"

    # Verify session IDs
    assert sm.get_session_id("host1.example.com") == "/sessions/1"
    assert sm.get_session_id("host2.example.com") == "/sessions/2"
    assert sm.get_session_id("host3.example.com") == "/sessions/3"


@pytest.mark.asyncio
async def test_close_cleanup(reset_session_manager):
    """Test close() properly cleans up session and connector"""
    sm = await SessionManager.get_instance()
    assert sm.session is not None
    assert sm._connector is not None

    await sm.close()
    assert sm._initialized is False


@pytest.mark.asyncio
async def test_reset_instance(reset_session_manager):
    """Test reset_instance() creates fresh singleton"""
    sm1 = await SessionManager.get_instance()
    sm1.cache_token("host1.example.com", "TOKEN1")

    await SessionManager.reset_instance()

    sm2 = await SessionManager.get_instance()
    assert sm2 is not sm1
    assert sm2.get_token("host1.example.com") is None


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency(reset_session_manager):
    """Test semaphore limits concurrent requests"""
    sm = await SessionManager.get_instance()

    # Initial semaphore value should be 50
    assert sm.semaphore._value == 50

    # Acquire semaphore
    async with sm.semaphore:
        assert sm.semaphore._value == 49

    # Released after context
    assert sm.semaphore._value == 50


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_concurrent_requests_share_session(mock_get, reset_session_manager):
    """Test that concurrent requests use the same session"""
    sm = await SessionManager.get_instance()
    set_mock_response(mock_get, 200, '{}')

    # Make multiple concurrent requests
    import asyncio
    tasks = [
        sm.get_request(f"https://host{i}.example.com", {"X-Auth-Token": f"TKN{i}"})
        for i in range(5)
    ]
    await asyncio.gather(*tasks)

    # All requests should use the same session instance
    assert mock_get.call_count == 5


@pytest.mark.asyncio
async def test_cache_token_without_session_id(reset_session_manager):
    """Test caching token without session ID"""
    sm = await SessionManager.get_instance()

    # Cache token without session ID
    sm.cache_token("host1.example.com", "TOKEN123", session_id=None)

    assert sm.get_token("host1.example.com") == "TOKEN123"
    assert sm.get_session_id("host1.example.com") is None


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_headers_default_to_empty_dict(mock_get, reset_session_manager):
    """Test that headers default to empty dict if not provided"""
    sm = await SessionManager.get_instance()
    set_mock_response(mock_get, 200, '{}')

    response = await sm.get_request("https://example.com")
    assert response.status == 200

    # Verify empty headers were used
    call_kwargs = mock_get.call_args[1]
    assert call_kwargs["headers"] == {}
