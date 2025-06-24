import asyncio
import json
from badfish.core.exceptions import BadfishException
from badfish.http.client import HTTPClient
from badfish.http.session import SessionManager
from badfish.operations.power import PowerOperations
from badfish.utils.yaml_utils import get_host_types_from_yaml, get_interfaces_by_type


class Badfish:
    """Main Badfish class for Redfish API operations."""
    
    def __init__(self, _host, _username, _password, _logger, _retries, _loop=None):
        self.host = _host
        self.username = _username
        self.password = _password
        self.retries = _retries
        self.host_uri = "https://%s" % _host
        self.redfish_uri = "/redfish/v1"
        self.root_uri = "%s%s" % (self.host_uri, self.redfish_uri)
        self.logger = _logger
        self.semaphore = asyncio.Semaphore(50)
        self.loop = _loop
        if not self.loop:
            self.loop = asyncio.get_event_loop()
        
        # Core resources
        self.system_resource = None
        self.manager_resource = None
        self.bios_uri = None
        self.boot_devices = None
        self.vendor = None
        
        # Initialize components
        self.http_client = HTTPClient(
            self.host_uri, None, self.username, self.password, 
            self.logger, self.retries, self.semaphore
        )
        self.session_manager = SessionManager(
            self.http_client, self.host_uri, self.root_uri,
            self.username, self.password, self.logger
        )
        
        # Initialize operation modules
        self.power_ops = None  # Will be initialized after system_resource is set

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.delete_session()
        if exc_type is not None:
            self.logger.debug(f"Exiting context with exception: {exc_type.__name__}: {exc_val}")
        return False

    async def init(self):
        """Initialize the Badfish instance."""
        self.session_manager.session_uri = await self.session_manager.find_session_uri()
        self.session_manager.token = await self.session_manager.validate_credentials()
        
        # Update HTTP client with token
        self.http_client.token = self.session_manager.token
        
        self.system_resource = await self.find_systems_resource()
        self.manager_resource = await self.find_managers_resource()
        self.bios_uri = "%s/Bios/Settings" % self.system_resource[len(self.redfish_uri) :]
        
        # Initialize operation modules
        self.power_ops = PowerOperations(
            self.http_client, self.host_uri, self.system_resource,
            self.logger, self.retries
        )

    async def find_systems_resource(self):
        """Find the systems resource URI."""
        response = await self.http_client.get_request(self.root_uri)
        if response:
            if response.status == 401:
                raise BadfishException("Failed to authenticate. Verify your credentials.")

            raw = await response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            if "Systems" not in data:
                raise BadfishException("Systems resource not found")
            else:
                systems = data["Systems"]["@odata.id"]
                _response = await self.http_client.get_request(self.host_uri + systems)
                if _response.status == 401:
                    raise BadfishException("Authorization Error: verify credentials.")

                raw = await _response.text("utf-8", "ignore")
                data = json.loads(raw.strip())
                if data.get("Members"):
                    for member in data["Members"]:
                        systems_service = member["@odata.id"]
                        self.logger.debug("Systems service: %s." % systems_service)
                        return systems_service
                else:
                    await self.http_client.error_handler(
                        _response,
                        message="ComputerSystem's Members array is either empty or missing",
                    )
        else:
            raise BadfishException("Failed to communicate with server.")

    async def find_managers_resource(self):
        """Find the managers resource URI."""
        response = await self.http_client.get_request(self.root_uri)
        if response:
            raw = await response.text("utf-8", "ignore")
            data = json.loads(raw.strip())

            self.vendor = "Dell" if "Dell" in data["Oem"] else "Supermicro"

            if "Managers" not in data:
                raise BadfishException("Managers resource not found")
            else:
                managers = data["Managers"]["@odata.id"]
                response = await self.http_client.get_request(self.host_uri + managers)
                if response and response.status in [200, 201]:
                    raw = await response.text("utf-8", "ignore")
                    data = json.loads(raw.strip())
                    if data.get("Members"):
                        for member in data["Members"]:
                            managers_service = member["@odata.id"]
                            self.logger.debug("Managers service: %s." % managers_service)
                            return managers_service
                    else:
                        raise BadfishException("Manager's Members array is either empty or missing")

    async def delete_session(self):
        """Delete the current session."""
        await self.session_manager.delete_session()

    # Delegate power operations to the power_ops module
    async def get_power_state(self):
        return await self.power_ops.get_power_state()

    async def set_power_state(self, state):
        return await self.power_ops.set_power_state(state)

    async def get_power_consumed_watts(self):
        return await self.power_ops.get_power_consumed_watts()

    async def reboot_server(self, graceful=True):
        return await self.power_ops.reboot_server(graceful)

    # YAML utilities
    async def get_host_types_from_yaml(self, _interfaces_path):
        return await get_host_types_from_yaml(_interfaces_path, self.logger)

    async def get_interfaces_by_type(self, host_type, _interfaces_path):
        return await get_interfaces_by_type(host_type, _interfaces_path, self.host, self.logger)

    # Additional methods would be added here as they're moved from the original file
    # For now, this shows the structure of how the refactored code would look 