import base64
import json
import time
from badfish.core.exceptions import BadfishException


class ScreenshotOperations:
    """Screenshot management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
        
    async def get_screenshot(self):
        _uri = self.host_uri + self.redfish_uri + "/Dell" + self.manager_resource[11:]
        _url = "%s/DellLCService/Actions/DellLCService.ExportServerScreenShot" % _uri
        _headers = {"content-type": "application/json"}
        _payload = {"FileType": "ServerScreenShot"}
        _response = await self.post_request(_url, _payload, _headers)

        status_code = _response.status
        if status_code in [200, 202]:
            self.logger.debug("POST command passed to get server screenshot.")
        elif status_code == 404:
            raise BadfishException("The system does not support screenshots.")
        else:
            if status_code == 400:
                self.logger.error("POST command failed to get the server screenshot.")
                await self.error_handler(_response)
            else:
                return None

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        except ValueError:
            raise BadfishException("Error reading response from host.")

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        fqdn_short = self.host.split(".")[0]
        filename = f"{fqdn_short}_screenshot_{timestamp}.png"
        with open(filename, "wb") as fh:
            fh.write(base64.decodebytes(bytes(data["ServerScreenShotFile"], "utf-8")))
        return filename

    async def take_screenshot(self):
        filename = await self.get_screenshot()
        self.logger.info(f"Image saved: {filename}")
        return True
