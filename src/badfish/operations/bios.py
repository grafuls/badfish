import asyncio
import json

from badfish.core.exceptions import BadfishException


class BiosOperations:
    """BIOS management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
    async def get_bios_attributes_registry(self):
        self.logger.debug("Getting BIOS attribute registry.")
        _uri = "%s%s/Bios/BiosRegistry" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_uri)

        if _response.status == 404:
            self.logger.error("Operation not supported by vendor.")
            return False

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        except ValueError:
            raise BadfishException("Could not retrieve Bios Attributes.")

        return data

    async def get_bios_attribute_registry(self, attribute):
        data = await self.get_bios_attributes_registry()
        attribute_value = await self.get_bios_attribute(attribute)
        for entry in data["RegistryEntries"]["Attributes"]:
            entries = [low_entry.lower() for low_entry in entry.values() if isinstance(low_entry, str)]
            if attribute.lower() in entries:
                for values in entry.items():
                    if values[0] == "CurrentValue":
                        self.logger.info(f"{values[0]}: {attribute_value}")
                    else:
                        self.logger.info(f"{values[0]}: {values[1]}")
                return True
        raise BadfishException(f"Unable to locate the Bios attribute: {attribute}")

    async def get_bios_attributes(self):
        self.logger.debug("Getting BIOS attributes.")
        _uri = "%s%s/Bios" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_uri)

        if _response.status == 404:
            self.logger.error("Operation not supported by vendor.")
            return False

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        except ValueError:
            raise BadfishException("Could not retrieve Bios Attributes.")
        return data

    async def get_bios_attribute(self, attribute):
        data = await self.get_bios_attributes()
        try:
            bios_attribute = data["Attributes"][attribute]
            return bios_attribute
        except (KeyError, TypeError):
            self.logger.warning("Could not retrieve Bios Attributes.")
            return None

    async def set_bios_attribute(self, attributes):
        data = await self.get_bios_attributes_registry()
        accepted = False
        for entry in data["RegistryEntries"]["Attributes"]:
            entries = [low_entry.lower() for low_entry in entry.values() if isinstance(low_entry, str)]
            _warnings = []
            _not_found = []
            _remove = []
            for attribute, value in attributes.items():
                if attribute.lower() in entries:
                    for values in entry.items():
                        if values[0] == "Value":
                            accepted_values = [value["ValueName"] for value in values[1]]
                            for accepted_value in accepted_values:
                                if value.lower() == accepted_value.lower():
                                    value = accepted_value
                                    accepted = True
                            if not accepted:
                                _warnings.append(f"List of accepted values for '{attribute}': {accepted_values}")

                attribute_value = await self.get_bios_attribute(attribute)
                if attribute_value:
                    if value.lower() == attribute_value.lower():
                        self.logger.warning(f"Attribute value for {attribute} is already in that state. IGNORING.")
                        _remove.append(attribute)
                else:
                    _not_found.append(f"{attribute} not found. Please check attribute name.")
            if _warnings:
                for warning in _warnings:
                    self.logger.warning(warning)
                raise BadfishException("Value not accepted")
            if _not_found:
                for warning in _not_found:
                    self.logger.error(warning)
                raise BadfishException("Attribute not found")
            if _remove:
                for attribute in _remove:
                    attributes.pop(attribute)

        _payload = {"Attributes": attributes}

        await self.patch_bios(_payload, insist=False)
        await self.reboot_server()

    async def change_bios_password(self, old_password, new_password):
        _url = "%s%s/Bios/Actions/Bios.ChangePassword" % (
            self.host_uri,
            self.system_resource,
        )
        _payload = {
            "PasswordName": "SetupPassword",
            "OldPassword": old_password,
            "NewPassword": new_password,
        }
        _headers = {"content-type": "application/json"}
        _response = await self.post_request(_url, _payload, _headers)

        status_code = _response.status

        if status_code in [200, 204]:
            self.logger.info("Command passed to set BIOS password.")
        elif status_code == 404:
            self.logger.error("BIOS password change not supported on this system.")
            return False
        else:
            self.logger.warning("Command failed to set BIOS password")

            await self.error_handler(_response)

        job_id = await self.create_bios_config_job(self.bios_uri)
        self.logger.warning("Host will now be rebooted for changes to take place.")
        await asyncio.sleep(5)
        await self.reboot_server()
        await asyncio.sleep(5)
        await self.check_job_status(job_id)

    async def set_bios_password(self, old_password, new_password):
        if new_password == "":
            self.logger.error("Missing argument: `--new-password`")
            return False

        await self.change_bios_password(old_password, new_password)

    async def remove_bios_password(self, old_password):
        if old_password == "":
            self.logger.error("Missing argument: `--old-password`")
            return False
        await self.change_bios_password(old_password, "")
