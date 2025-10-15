import asyncio
import json
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta

import aiohttp

from src.badfish.helpers.exceptions import BadfishException


class SessionManager:
    """
    Manages a shared aiohttp session pool for all Badfish instances.

    This singleton class provides:
    - Single shared ClientSession to avoid DNS resolver (c-ares) exhaustion
    - Connection pooling via TCPConnector for TCP connection reuse
    - Per-host token caching to reduce authentication overhead
    - Thread-safe initialization with asyncio.Lock

    Usage:
        session_manager = await SessionManager.get_instance()
        response = await session_manager.get_request(uri, headers, auth)
    """

    _instance: Optional['SessionManager'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Private constructor. Use get_instance() instead."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.tokens: Dict[str, Tuple[str, datetime]] = {}  # host -> (token, expiry)
        self.session_ids: Dict[str, str] = {}  # host -> session_id
        self.semaphore = asyncio.Semaphore(50)  # Global concurrency limit
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._initialized = False

    @classmethod
    async def get_instance(cls) -> 'SessionManager':
        """
        Get or create the singleton SessionManager instance.

        Returns:
            SessionManager: The singleton instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = SessionManager()
                    await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Initialize shared session with optimized settings."""
        if self._initialized:
            return

        # Create connector with connection pooling
        self._connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=10,  # Connections per host (prevents overwhelming single BMC)
            ttl_dns_cache=300,  # DNS cache TTL (5 minutes)
            ssl=False,  # Redfish typically uses self-signed certs
            enable_cleanup_closed=True,  # Clean up closed connections
            force_close=False,  # Reuse connections (keep-alive)
        )

        # Create single shared session
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
        )

        self._initialized = True

    async def get_request(
        self,
        uri: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[aiohttp.BasicAuth] = None,
    ) -> aiohttp.ClientResponse:
        """
        Execute GET request using shared session.

        Args:
            uri: Full URI to request
            headers: Optional request headers
            auth: Optional BasicAuth for authentication

        Returns:
            ClientResponse object

        Raises:
            BadfishException: If request fails
        """
        if not self._initialized:
            await self._initialize()

        if headers is None:
            headers = {}

        try:
            async with self.semaphore:
                async with self.session.get(
                    uri,
                    headers=headers,
                    auth=auth,
                    ssl=False,
                ) as response:
                    await response.read()
                    return response
        except (Exception, TimeoutError) as ex:
            raise BadfishException(f"Failed to communicate with server: {ex}")

    async def post_request(
        self,
        uri: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> aiohttp.ClientResponse:
        """
        Execute POST request using shared session.

        Args:
            uri: Full URI to request
            payload: JSON payload to send
            headers: Request headers

        Returns:
            ClientResponse object

        Raises:
            BadfishException: If request fails
        """
        if not self._initialized:
            await self._initialize()

        try:
            async with self.semaphore:
                async with self.session.post(
                    uri,
                    data=json.dumps(payload),
                    headers=headers,
                    ssl=False,
                ) as response:
                    if response.status != 204:
                        await response.read()
                    return response
        except (Exception, TimeoutError) as ex:
            raise BadfishException(f"Failed to communicate with server: {ex}")

    async def patch_request(
        self,
        uri: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> aiohttp.ClientResponse:
        """
        Execute PATCH request using shared session.

        Args:
            uri: Full URI to request
            payload: JSON payload to send
            headers: Request headers

        Returns:
            ClientResponse object

        Raises:
            BadfishException: If request fails
        """
        if not self._initialized:
            await self._initialize()

        try:
            async with self.semaphore:
                async with self.session.patch(
                    uri,
                    data=json.dumps(payload),
                    headers=headers,
                    ssl=False,
                ) as response:
                    await response.read()
                    return response
        except Exception as ex:
            raise BadfishException(f"Failed to communicate with server: {ex}")

    async def delete_request(
        self,
        uri: str,
        headers: Dict[str, str],
    ) -> aiohttp.ClientResponse:
        """
        Execute DELETE request using shared session.

        Args:
            uri: Full URI to request
            headers: Request headers

        Returns:
            ClientResponse object

        Raises:
            BadfishException: If request fails
        """
        if not self._initialized:
            await self._initialize()

        try:
            async with self.semaphore:
                async with self.session.delete(
                    uri,
                    headers=headers,
                    ssl=False,
                ) as response:
                    await response.read()
                    return response
        except (Exception, TimeoutError) as ex:
            raise BadfishException(f"Failed to communicate with server: {ex}")

    def cache_token(self, host: str, token: str, session_id: Optional[str] = None, ttl_seconds: int = 3600):
        """
        Cache authentication token for a host.

        Args:
            host: Hostname
            token: X-Auth-Token value
            session_id: Optional Redfish session ID
            ttl_seconds: Token TTL in seconds (default: 1 hour)
        """
        expiry = datetime.now() + timedelta(seconds=ttl_seconds)
        self.tokens[host] = (token, expiry)
        if session_id:
            self.session_ids[host] = session_id

    def get_token(self, host: str) -> Optional[str]:
        """
        Retrieve cached token if still valid.

        Args:
            host: Hostname

        Returns:
            Token string if cached and valid, None otherwise
        """
        if host in self.tokens:
            token, expiry = self.tokens[host]
            if datetime.now() < expiry:
                return token
            else:
                # Token expired, clean up
                del self.tokens[host]
                if host in self.session_ids:
                    del self.session_ids[host]
        return None

    def get_session_id(self, host: str) -> Optional[str]:
        """
        Retrieve cached Redfish session ID.

        Args:
            host: Hostname

        Returns:
            Session ID if cached, None otherwise
        """
        return self.session_ids.get(host)

    def invalidate_token(self, host: str):
        """
        Invalidate cached token and session ID for a host.

        Args:
            host: Hostname
        """
        if host in self.tokens:
            del self.tokens[host]
        if host in self.session_ids:
            del self.session_ids[host]

    async def close(self):
        """Clean shutdown of shared session and connector."""
        if self.session:
            await self.session.close()
        if self._connector:
            await self._connector.close()
        self._initialized = False

    @classmethod
    async def reset_instance(cls):
        """
        Reset the singleton instance (primarily for testing).
        Closes existing session and clears the instance.
        """
        async with cls._lock:
            if cls._instance:
                await cls._instance.close()
                cls._instance = None
