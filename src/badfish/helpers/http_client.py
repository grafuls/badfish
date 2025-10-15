import json
from typing import Any, Dict, Optional

import aiohttp

from src.badfish.helpers.async_lru import alru_cache
from src.badfish.helpers.exceptions import BadfishException
from src.badfish.helpers.session_manager import SessionManager


class HTTPClient:

    def __init__(self, host: str, username: str, password: str, logger, retries: int = 15):
        self.host = host
        self.username = username
        self.password = password
        self.logger = logger
        self.retries = retries
        self.host_uri = f"https://{host}"
        self.redfish_uri = "/redfish/v1"
        self.root_uri = f"{self.host_uri}{self.redfish_uri}"
        self.session_manager: Optional[SessionManager] = None
        self.token = None
        self.session_id = None

    async def _ensure_session_manager(self):
        """Lazy initialization of session manager."""
        if self.session_manager is None:
            self.session_manager = await SessionManager.get_instance()

    async def error_handler(self, response: aiohttp.ClientResponse, message: Optional[str] = None) -> None:
        try:
            raw = await response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        except ValueError:
            raise BadfishException("Error reading response from host.")

        detail_message = data
        if "error" in data:
            try:
                detail_message = str(data["error"]["@Message.ExtendedInfo"][0]["Message"])
                resolution = str(data["error"]["@Message.ExtendedInfo"][0]["Resolution"])
                self.logger.debug(resolution)
            except (KeyError, IndexError) as ex:
                self.logger.debug(ex)
        if message:
            self.logger.debug(detail_message)
            raise BadfishException(message)
        else:
            raise BadfishException(detail_message)

    @alru_cache(maxsize=64)
    async def get_request(self, uri: str, _continue: bool = False, _get_token: bool = False):
        return await self.get_raw(uri, _continue, _get_token)

    @alru_cache(maxsize=64)
    async def get_json(self, uri: str, _continue: bool = False, _get_token: bool = False):
        response = await self.get_raw(uri, _continue, _get_token)
        if not response:
            return None

        # Parse JSON from response
        try:
            raw = await response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            return data
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.debug(f"Failed to parse JSON response: {e}")
            return None

    async def get_raw(self, uri: str, _continue: bool = False, _get_token: bool = False):
        await self._ensure_session_manager()

        # Check token cache first (unless we're getting a new token)
        if not _get_token and not self.token:
            cached_token = self.session_manager.get_token(self.host)
            if cached_token:
                self.token = cached_token
                cached_session_id = self.session_manager.get_session_id(self.host)
                if cached_session_id:
                    self.session_id = cached_session_id

        headers = {}
        auth = None

        if _get_token:
            auth = aiohttp.BasicAuth(self.username, self.password)
        elif self.token:
            headers["X-Auth-Token"] = self.token

        try:
            _response = await self.session_manager.get_request(uri, headers, auth)
        except (Exception, TimeoutError) as ex:
            if _continue:
                return None
            else:
                self.logger.debug(f"HTTPClient get_raw exception: {ex}")
                self.logger.debug(f"Exception type: {type(ex)}")
                raise BadfishException("Failed to communicate with server.")

        return _response

    async def post_request(
        self,
        uri: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        _get_token: bool = False,
    ):
        await self._ensure_session_manager()

        if not _get_token and self.token:
            headers = headers.copy()  # Avoid mutating caller's dict
            headers.update({"X-Auth-Token": self.token})

        try:
            _response = await self.session_manager.post_request(uri, payload, headers)
        except (Exception, TimeoutError):
            raise BadfishException("Failed to communicate with server.")
        return _response

    async def patch_request(self, uri: str, payload: Dict[str, Any], headers: Dict[str, str], _continue: bool = False):
        await self._ensure_session_manager()

        if self.token:
            headers = headers.copy()  # Avoid mutating caller's dict
            headers.update({"X-Auth-Token": self.token})

        try:
            _response = await self.session_manager.patch_request(uri, payload, headers)
            return _response
        except Exception as ex:
            if _continue:
                return None
            else:
                self.logger.debug(ex)
                raise BadfishException("Failed to communicate with server.")

    async def delete_request(self, uri: str, headers: Dict[str, str]):
        await self._ensure_session_manager()

        if self.token:
            headers = headers.copy()  # Avoid mutating caller's dict
            headers.update({"X-Auth-Token": self.token})

        try:
            _response = await self.session_manager.delete_request(uri, headers)
            return _response
        except (Exception, TimeoutError):
            raise BadfishException("Failed to communicate with server.")

    async def find_session_uri(self):
        _response = await self.get_request(self.root_uri, _get_token=True)

        status = _response.status
        if status == 401:
            raise BadfishException(f"Failed to authenticate. Verify your credentials for {self.host}")
        if status not in [200, 201]:
            raise BadfishException(f"Failed to communicate with {self.host}")

        raw = await _response.text("utf-8", "ignore")
        data = json.loads(raw.strip())

        redfish_version = int(data["RedfishVersion"].replace(".", ""))
        session_uri = None
        if redfish_version >= 160:
            session_uri = "/redfish/v1/SessionService/Sessions"
        elif redfish_version < 160:
            session_uri = "/redfish/v1/Sessions"

        _uri = "%s%s" % (self.host_uri, session_uri)
        check_response = await self.get_request(_uri, _get_token=True)
        if check_response.status == 404:
            session_uri = "/redfish/v1/SessionService/Sessions"

        return session_uri

    async def validate_credentials(self):
        await self._ensure_session_manager()

        payload = {"UserName": self.username, "Password": self.password}
        headers = {"content-type": "application/json"}
        session_uri = await self.find_session_uri()
        _uri = "%s%s" % (self.host_uri, session_uri)
        _response = await self.post_request(_uri, payload, headers, _get_token=True)

        # Mock shifting value on value access and not on call.
        await _response.text("utf-8", "ignore")

        status = _response.status
        if status == 401:
            raise BadfishException(f"Failed to authenticate. Verify your credentials for {self.host}")
        if status not in [200, 201]:
            raise BadfishException(f"Failed to communicate with {self.host}")

        self.session_id = _response.headers.get("Location")
        token = _response.headers.get("X-Auth-Token")

        # Cache token in session manager
        self.session_manager.cache_token(self.host, token, self.session_id, ttl_seconds=3600)

        return token

    async def delete_session(self):
        try:
            try:
                if not self.session_id:
                    self.logger.debug("No session ID found, skipping session deletion")
                    return
                headers = {"content-type": "application/json"}
                _uri = "%s%s" % (self.host_uri, self.session_id)
                try:
                    _response = await self.delete_request(_uri, headers=headers)
                    if _response.status in [200, 201]:
                        self.logger.debug(f"Session successfully deleted for {self.host}")
                    elif _response.status == 404:
                        self.logger.debug(f"Session not found (404) for {self.host}, may have been already deleted")
                    else:
                        self.logger.warning(
                            f"Unexpected status {_response.status} when deleting session for {self.host}."
                        )
                except Exception as ex:
                    self.logger.warning(f"Failed to delete session for {self.host}: {ex}")
            finally:
                # Invalidate cached token in session manager
                if self.session_manager:
                    self.session_manager.invalidate_token(self.host)
                self.session_id = None
                self.token = None
        except Exception:
            if self.session_manager:
                self.session_manager.invalidate_token(self.host)
            self.session_id = None
            self.token = None
