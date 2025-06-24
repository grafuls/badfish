class SriovOperations:
    """SR-IOV management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
        
    async def get_sriov_mode(self):
        self.logger.debug("Getting global SRIOV mode.")
        attribute = "SriovGlobalEnable"
        sriov_mode = await self.get_bios_attribute(attribute)
        return sriov_mode

    async def send_sriov_mode(self, enable):
        value = "Enabled" if enable else "Disabled"
        _payload = {
            "Attributes": {
                "SriovGlobalEnable": value,
            }
        }

        sriov_mode = await self.get_sriov_mode()
        if (sriov_mode.lower() == "enabled" and enable) or (sriov_mode.lower() == "disabled" and not enable):
            self.logger.warning("SRIOV mode is already in that state. IGNORING.")
            return

        await self.patch_bios(_payload)
        await self.reboot_server()
