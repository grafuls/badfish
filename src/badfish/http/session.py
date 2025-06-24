import json
from badfish.core.exceptions import BadfishException


class SessionManager:
    """Manages Redfish API sessions."""
    
    def __init__(self, http_client, host_uri, root_uri, username, password, logger):
        self.http_client = http_client
        self.host_uri = host_uri
        self.root_uri = root_uri
        self.username = username
        self.password = password
        self.logger = logger
        self.session_uri = None
        self.session_id = None
        self.token = None

    async def find_session_uri(self):
        """Find the appropriate session URI based on Redfish version."""
        _response = await self.http_client.get_request(self.root_uri, _get_token=True)
        raw = await _response.text("utf-8", "ignore")
        data = json.loads(raw.strip())

        status = _response.status
        if status == 401:
            raise BadfishException(f"Failed to authenticate. Verify your credentials for {self.host_uri}")
        if status not in [200, 201]:
            raise BadfishException(f"Failed to communicate with {self.host_uri}")

        redfish_version = int(data["RedfishVersion"].replace(".", ""))
        session_uri = None
        if redfish_version >= 160:
            session_uri = "/redfish/v1/SessionService/Sessions"
        elif redfish_version < 160:
            session_uri = "/redfish/v1/Sessions"

        _uri = "%s%s" % (self.host_uri, session_uri)
        check_response = await self.http_client.get_request(_uri, _get_token=True)
        if check_response.status == 404:
            session_uri = "/redfish/v1/SessionService/Sessions"

        return session_uri

    async def validate_credentials(self):
        """Validate credentials and create a session."""
        payload = {"UserName": self.username, "Password": self.password}
        headers = {"content-type": "application/json"}
        _uri = "%s%s" % (self.host_uri, self.session_uri)
        _response = await self.http_client.post_request(_uri, headers=headers, payload=payload, _get_token=True)

        # Mock shifting value on value access and not on call.
        await _response.text("utf-8", "ignore")

        status = _response.status
        if status == 401:
            raise BadfishException(f"Failed to authenticate. Verify your credentials for {self.host_uri}")
        if status not in [200, 201]:
            raise BadfishException(f"Failed to communicate with {self.host_uri}")

        self.session_id = _response.headers.get("Location")
        return _response.headers.get("X-Auth-Token")

    async def delete_session(self):
        """Delete the current session."""
        try:
            try:
                if not self.session_id:
                    self.logger.debug("No session ID found, skipping session deletion")
                    return
                headers = {"content-type": "application/json"}
                _uri = "%s%s" % (self.host_uri, self.session_id)
                try:
                    _response = await self.http_client.delete_request(_uri, headers=headers)
                    if _response.status in [200, 201]:
                        self.logger.debug(f"Session successfully deleted for {self.host_uri}")
                    elif _response.status == 404:
                        self.logger.debug(f"Session not found (404) for {self.host_uri}, may have been already deleted")
                    else:
                        self.logger.warning(f"Unexpected status {_response.status} when deleting session for {self.host_uri}.")
                except Exception as ex:
                    self.logger.warning(f"Failed to delete session for {self.host_uri}: {ex}")
            finally:
                self.session_id = None
                self.token = None
        except Exception:
            self.session_id = None
            self.token = None 