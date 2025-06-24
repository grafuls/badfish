import json
from badfish.core.exceptions import BadfishException


class MiscOperations:
    """Miscellaneous operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
    async def get_serial_summary(self):
        _uri = "%s%s" % (self.host_uri, self.redfish_uri)
        _response = await self.get_request(_uri)

        if _response.status in [400, 404]:
            raise BadfishException("Server does not support this functionality")

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            service_data = data.get("Oem").get("Dell")

            if not service_data:
                serial_uri = "%s%s/Systems/1" % (self.host_uri, self.redfish_uri)
                serial_response = await self.get_request(serial_uri)

                if _response.status in [400, 404]:
                    raise BadfishException("Server does not support this functionality")

                serial_raw = await serial_response.text("utf-8", "ignore")
                serial_data = json.loads(serial_raw.strip())
                serial_number_data = serial_data.get("SerialNumber")

                if not serial_number_data:
                    raise BadfishException("Server does not support this functionality")
                else:
                    return serial_number_data

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting serial summary")

        return service_data

    async def list_serial(self):
        data = await self.get_serial_summary()

        if "ServiceTag" in data:
            self.logger.info("ServiceTag:")
            self.logger.info(f"    {self.host}: {data.get('ServiceTag')}")
        else:
            self.logger.info("Serial Number:")
            self.logger.info(f"    {self.host}: {data}")

        return True
