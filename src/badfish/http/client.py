import json
import aiohttp
from badfish.core.exceptions import BadfishException


class HTTPClient:
    """HTTP client for Redfish API operations."""
    
    def __init__(self, host_uri, token, username, password, logger, retries, semaphore):
        self.host_uri = host_uri
        self.token = token
        self.username = username
        self.password = password
        self.logger = logger
        self.retries = retries
        self.semaphore = semaphore

    async def get_request(self, uri, _continue=False, _get_token=False):
        """Make a GET request to the Redfish API."""
        return await self.get_raw(uri, _continue, _get_token)

    async def get_raw(self, uri, _continue=False, _get_token=False):
        """Make a raw GET request."""
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    if not _get_token:
                        async with session.get(
                            uri,
                            headers={"X-Auth-Token": self.token},
                            ssl=False,
                            timeout=60,
                        ) as _response:
                            await _response.read()
                    else:
                        async with session.get(
                            uri,
                            auth=aiohttp.BasicAuth(self.username, self.password),
                            ssl=False,
                            timeout=60,
                        ) as _response:
                            await _response.read()
        except (Exception, TimeoutError) as ex:
            if _continue:
                return
            else:
                self.logger.debug(ex)
                raise BadfishException("Failed to communicate with server.")
        return _response

    async def post_request(self, uri, payload, headers, _get_token=False):
        """Make a POST request to the Redfish API."""
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    if not _get_token:
                        headers.update({"X-Auth-Token": self.token})
                    async with session.post(
                        uri,
                        data=json.dumps(payload),
                        headers=headers,
                        ssl=False,
                    ) as _response:
                        if _response.status != 204:
                            await _response.read()
                        else:
                            return _response
        except (Exception, TimeoutError):
            raise BadfishException("Failed to communicate with server.")
        return _response

    async def patch_request(self, uri, payload, headers, _continue=False):
        """Make a PATCH request to the Redfish API."""
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    headers.update({"X-Auth-Token": self.token})
                    async with session.patch(
                        uri,
                        data=json.dumps(payload),
                        headers=headers,
                        ssl=False,
                    ) as _response:
                        await _response.read()
        except Exception as ex:
            if _continue:
                return
            else:
                self.logger.debug(ex)
                raise BadfishException("Failed to communicate with server.")
        return _response

    async def delete_request(self, uri, headers):
        """Make a DELETE request to the Redfish API."""
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession() as session:
                    headers.update({"X-Auth-Token": self.token})
                    async with session.delete(
                        uri,
                        headers=headers,
                        ssl=False,
                    ) as _response:
                        await _response.read()
        except (Exception, TimeoutError):
            raise BadfishException("Failed to communicate with server.")
        return _response

    async def error_handler(self, _response, message=None):
        """Handle error responses from the Redfish API."""
        try:
            raw = await _response.text("utf-8", "ignore")
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