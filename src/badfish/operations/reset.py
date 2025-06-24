import asyncio
import json

from badfish.core.exceptions import BadfishException


class ResetOperations:
    """Reset management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
            
    async def get_reset_types(self, manager=False, bmc=False):
        if manager:
            resource = self.manager_resource
            endpoint = "#Manager.Reset"
        else:
            resource = self.system_resource
            endpoint = "#ComputerSystem.Reset"

        self.logger.debug("Getting allowable reset types.")
        _url = "%s%s" % (self.host_uri, resource)
        _response = await self.get_request(_url)
        reset_types = []
        if _response:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            if "Actions" not in data:
                self.logger.warning("Actions resource not found")
            else:
                reset = data["Actions"].get(endpoint)
                if reset:
                    reset_types = reset.get("ResetType@Redfish.AllowableValues", [])
                    if not reset_types:
                        if bmc:
                            reset_types = ["GracefulRestart", "ForceRestart"]
                        else:
                            self.logger.warning("Could not get allowable reset types")
        return reset_types

    async def send_reset(self, reset_type):
        _url = "%s%s/Actions/ComputerSystem.Reset" % (
            self.host_uri,
            self.system_resource,
        )
        _payload = {"ResetType": reset_type}
        _headers = {"content-type": "application/json"}
        _response = await self.post_request(_url, _payload, _headers)

        status_code = _response.status
        if status_code in [200, 204]:
            self.logger.info("Command passed to %s server, code return is %s." % (reset_type, status_code))
            await asyncio.sleep(10)
            return True
        elif status_code == 409:
            self.logger.warning("Command failed to %s server, host appears to be already in that state." % reset_type)
        else:
            self.logger.error("Command failed to %s server, status code is: %s." % (reset_type, status_code))

            await self.error_handler(_response)
        return False

    async def reboot_server(self, graceful=True):
        _reset_types = await self.get_reset_types()
        reset_type = "GracefulRestart"
        if reset_type not in _reset_types:
            for rt in _reset_types:
                if "restart" in rt.lower():
                    reset_type = rt

        self.logger.debug("Rebooting server: %s." % self.host)
        power_state = await self.get_power_state()
        if power_state.lower() == "on":
            if graceful:
                response = await self.send_reset(reset_type)

                if not response:
                    host_down = await self.polling_host_state("Off")

                    if not host_down:
                        self.logger.warning("Unable to graceful shutdown the server, will perform forced shutdown now.")
                        await self.send_reset("ForceOff")
            else:
                await self.send_reset("ForceOff")

            host_not_down = await self.polling_host_state("Down", False)

            if host_not_down:
                await self.send_reset("On")

        elif power_state.lower() == "off":
            await self.send_reset("On")
        return True

    async def reset_idrac(self):
        if self.vendor != "Dell":
            self.logger.warning("Vendor isn't a Dell, if you are trying this on a Supermicro, use --bmc-reset instead.")
            return False
        self.logger.debug("Running reset iDRAC.")
        _reset_types = await self.get_reset_types(manager=True)
        reset_type = "ForceRestart"
        if reset_type not in _reset_types:
            for rt in _reset_types:
                if "restart" in rt.lower():
                    reset_type = rt
        _url = "%s%s/Actions/Manager.Reset/" % (self.host_uri, self.manager_resource)
        _payload = {"ResetType": reset_type}
        _headers = {"content-type": "application/json"}
        self.logger.debug("url: %s" % _url)
        self.logger.debug("payload: %s" % _payload)
        self.logger.debug("headers: %s" % _headers)
        _response = await self.post_request(_url, _payload, _headers)

        status_code = _response.status
        if status_code in [200, 204]:
            self.logger.info("Status code %s returned for POST command to reset iDRAC." % status_code)
        else:
            data = await _response.text("utf-8", "ignore")
            raise BadfishException("Status code %s returned, error is: \n%s." % (status_code, data))

        self.logger.info("iDRAC will now reset and be back online within a few minutes.")
        return True

    async def reset_bmc(self):
        if self.vendor != "Supermicro":
            self.logger.warning("Vendor isn't a Supermicro, if you are trying this on a Dell, use --racreset instead.")
            return False
        self.logger.debug("Running reset BMC.")
        _reset_types = await self.get_reset_types(manager=True, bmc=True)
        reset_type = "GracefulRestart"
        if reset_type not in _reset_types:
            for rt in _reset_types:
                if "restart" in rt.lower():
                    reset_type = rt
        _url = "%s%s/Actions/Manager.Reset/" % (self.host_uri, self.manager_resource)
        _payload = {"ResetType": reset_type}
        _headers = {"content-type": "application/json"}
        self.logger.debug("url: %s" % _url)
        self.logger.debug("payload: %s" % _payload)
        self.logger.debug("headers: %s" % _headers)
        _response = await self.post_request(_url, _payload, _headers)

        status_code = _response.status
        if status_code == 200:
            self.logger.info("Status code %s returned for POST command to reset BMC." % status_code)
        else:
            data = await _response.text("utf-8", "ignore")
            raise BadfishException("Status code %s returned, error is: \n%s." % (status_code, data))

        self.logger.info("BMC will now reset and be back online within a few minutes.")
        return True

    async def reset_bios(self):
        self.logger.debug("Running BIOS reset.")
        _url = "%s%s/Bios/Actions/Bios.ResetBios/" % (
            self.host_uri,
            self.system_resource,
        )
        _payload = {}
        _headers = {"content-type": "application/json"}
        self.logger.debug("url: %s" % _url)
        self.logger.debug("payload: %s" % _payload)
        self.logger.debug("headers: %s" % _headers)
        _response = await self.post_request(_url, _payload, _headers)

        status_code = _response.status
        if status_code in [200, 204]:
            self.logger.info("Status code %s returned for POST command to reset BIOS." % status_code)
        else:
            data = await _response.text("utf-8", "ignore")
            raise BadfishException("Status code %s returned, error is: \n%s." % (status_code, data))

        self.logger.info("BIOS will now reset and be back online within a few minutes.")
        return True
