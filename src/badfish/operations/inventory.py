import json

from badfish.core.exceptions import BadfishException


class InventoryOperations:
    """Inventory management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
    async def get_firmware_inventory(self):
        self.logger.debug("Getting firmware inventory for all devices supported by iDRAC.")

        _url = "%s/UpdateService/FirmwareInventory/" % self.root_uri
        _response = await self.get_request(_url)

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        except ValueError:
            raise BadfishException("Not able to access Firmware inventory.")
        installed_devices = []
        if "error" in data:
            self.logger.debug(data["error"])
            raise BadfishException("Not able to access Firmware inventory.")
        for device in data["Members"]:
            a = device["@odata.id"]
            a = a.replace("/redfish/v1/UpdateService/FirmwareInventory/", "")
            if "Installed" in a:
                installed_devices.append(a)

        for device in installed_devices:
            self.logger.debug("Getting device info for %s" % device)
            _uri = "%s/UpdateService/FirmwareInventory/%s" % (self.root_uri, device)

            _response = await self.get_request(_uri, _continue=True)
            if not _response:
                continue

            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            for info in data.items():
                if "Id" == info[0]:
                    self.logger.info("%s:" % info[1])
                if "odata" not in info[0] and "Description" not in info[0] and "Oem" not in info[0]:
                    self.logger.info("    %s: %s" % (info[0], info[1]))
