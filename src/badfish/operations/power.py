import asyncio
import json
from badfish.core.exceptions import BadfishException
from badfish.utils.progress import progress_bar


class PowerOperations:
    """Power management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries

    async def get_power_state(self):
        """Get the current power state of the server."""
        _uri = "%s%s" % (self.host_uri, self.system_resource)
        self.logger.debug("url: %s" % _uri)

        _response = await self.http_client.get_request(_uri, _continue=True)
        if not _response:
            return "Down"
        if _response.status == 200:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        else:
            self.logger.debug("Couldn't get power state. Retrying.")
            return "Down"

        if not data.get("PowerState"):
            raise BadfishException("Power state not found. Try to racreset.")
        else:
            self.logger.debug("Current server power state is: %s." % data["PowerState"])

        return data["PowerState"]

    async def set_power_state(self, state):
        """Set the power state of the server."""
        if state.lower() not in ["on", "off"]:
            raise BadfishException("Power state not valid. 'on' or 'off' only accepted.")

        _uri = "%s%s" % (self.host_uri, self.system_resource)
        self.logger.debug("url: %s" % _uri)

        _response = await self.http_client.get_request(_uri, _continue=True)
        if not _response and state.lower() == "off":
            self.logger.warning("Power state appears to be already set to 'off'.")
            return

        status = _response.status
        if status == 200:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        else:
            raise BadfishException("Couldn't get power state.")

        if not data.get("PowerState"):
            raise BadfishException("Power state not found. Try to racreset.")
        else:
            self.logger.debug("Current server power state is: %s." % data["PowerState"])

        if state.lower() == "off":
            await self.send_reset("ForceOff")
        elif state.lower() == "on":
            await self.send_reset("On")

        return data["PowerState"]

    async def get_power_consumed_watts(self):
        """Get the current power consumption in watts."""
        _uri = "%s%s/Chassis/%s/Power" % (self.host_uri, self.redfish_uri, self.system_resource.split("/")[-1])
        _response = await self.http_client.get_request(_uri)

        if _response.status == 404:
            self.logger.error("Operation not supported by vendor.")
            return False
        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        except ValueError:
            raise BadfishException("Power value outside operating range.")
        try:
            cwc = data["PowerControl"][0]["PowerConsumedWatts"]
        except IndexError:
            cwc = "N/A. Try to `--racreset`."
        self.logger.info(f"Current watts consumed: {cwc}")
        return

    async def send_reset(self, reset_type):
        """Send a reset command to the server."""
        _url = "%s%s/Actions/ComputerSystem.Reset" % (
            self.host_uri,
            self.system_resource,
        )
        _payload = {"ResetType": reset_type}
        _headers = {"content-type": "application/json"}
        _response = await self.http_client.post_request(_url, _payload, _headers)

        status_code = _response.status
        if status_code in [200, 204]:
            self.logger.info("Command passed to %s server, code return is %s." % (reset_type, status_code))
            await asyncio.sleep(10)
            return True
        elif status_code == 409:
            self.logger.warning("Command failed to %s server, host appears to be already in that state." % reset_type)
        else:
            self.logger.error("Command failed to %s server, status code is: %s." % (reset_type, status_code))

            await self.http_client.error_handler(_response)
        return False

    async def get_reset_types(self, manager=False, bmc=False):
        """Get the allowable reset types for the server."""
        if manager:
            resource = self.manager_resource
            endpoint = "#Manager.Reset"
        else:
            resource = self.system_resource
            endpoint = "#ComputerSystem.Reset"

        self.logger.debug("Getting allowable reset types.")
        _url = "%s%s" % (self.host_uri, resource)
        _response = await self.http_client.get_request(_url)
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

    async def reboot_server(self, graceful=True):
        """Reboot the server."""
        _reset_types = await self.get_reset_types()
        reset_type = "GracefulRestart"
        if reset_type not in _reset_types:
            for rt in _reset_types:
                if "restart" in rt.lower():
                    reset_type = rt

        self.logger.debug("Rebooting server: %s." % self.host_uri)
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

    async def polling_host_state(self, state, equals=True):
        """Poll for a specific host state."""
        state_str = "Not %s" % state if not equals else state
        self.logger.info("Polling for host state: %s" % state_str)
        desired_state = False
        for count in range(self.retries):
            current_state = await self.get_power_state()
            if equals:
                desired_state = current_state.lower() == state.lower()
            else:
                desired_state = current_state.lower() != state.lower()
            await asyncio.sleep(5)
            if desired_state:
                progress_bar(self.retries, self.retries, current_state)
                break
            progress_bar(count, self.retries, current_state)

        return desired_state 