import json
from logging import getLogger
from urllib.parse import urlparse

from badfish.core.exceptions import BadfishException


class VirtualMediaOperations:
    """Virtual media management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
        
    async def get_virtual_media_config(self):
        vm_path = "/"
        if self.vendor == "Supermicro":
            vm_path += "VM1"
        else:
            vm_path += "VirtualMedia"

        _uri = "%s%s%s" % (self.host_uri, self.manager_resource, vm_path)
        _response = await self.get_request(_uri)
        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
        except ValueError:
            raise BadfishException("Not able to access virtual media resource.")

        if self.vendor == "Supermicro":
            try:
                vm_path = {
                    "config": "",
                    "count": data["Members@odata.count"],
                    "members": [],
                }
                if data["Oem"].get("Supermicro"):
                    vm_path.update({"config": data["Oem"].get("Supermicro").get("VirtualMediaConfig").get("@odata.id")})
                else:
                    vm_path.update({"config": data["Oem"].get("VirtualMediaConfig").get("@odata.id")})
                if vm_path["count"] > 0:
                    for m in data["Members"]:
                        vm_path["members"].append(m.get("@odata.id"))
            except (ValueError, KeyError, TypeError):
                raise BadfishException("Not able to access virtual media config.")
        else:
            try:
                vm_path = []
                for m in data["Members"]:
                    vm_path.append(m.get("@odata.id"))
            except (ValueError, KeyError):
                raise BadfishException("Not able to access virtual media config.")
        return vm_path

    async def check_virtual_media(self):
        vm_config = await self.get_virtual_media_config()
        if self.vendor == "Supermicro":
            if vm_config.get("count") == 0:
                self.logger.info("No virtual media mounted.")
                return False
            else:
                vm_config = vm_config["members"]

        inserted = False
        for vm in vm_config:
            _uri = "%s%s" % (self.host_uri, vm)
            _response = await self.get_request(_uri)
            try:
                raw = await _response.text("utf-8", "ignore")
                _data = json.loads(raw.strip())
                self.logger.info(f"{_data.get('Id')}:")
                self.logger.info(f"    Name: {_data.get('Name')}")
                self.logger.info(f"    ImageName: {_data.get('ImageName')}")
                self.logger.info(f"    Inserted: {_data.get('Inserted')}")
                if str(_data.get("Inserted")).lower() == "true" and "CD" in str(_data.get("Id")):
                    inserted = True
            except ValueError:
                raise BadfishException("There was something wrong getting values for VirtualMedia")
        return inserted

    async def mount_virtual_media(self, path):
        vm_config = await self.get_virtual_media_config()
        _headers = {"Content-Type": "application/json"}
        if self.vendor == "Supermicro":
            parsed_path = urlparse(path)
            _payload = {
                "Host": f"{parsed_path.scheme}://{parsed_path.netloc}",
                "Path": parsed_path.path,
                "Username": "",
                "Password": "",
            }
            _uri = "%s%s" % (self.host_uri, vm_config["config"])
            _response = await self.patch_request(_uri, payload=_payload, headers=_headers)

            _uri = "%s%s/Actions/IsoConfig.Mount" % (self.host_uri, vm_config["config"])
            _response = await self.post_request(_uri, payload={}, headers=_headers)
            if _response.status in [200, 202]:
                self.logger.info("Image mounting operation was successful.")
            else:
                raise BadfishException("There was something wrong trying to mount virtual media.")
        else:
            vcd = [x for x in vm_config if "CD" in x][0]
            _uri = "%s%s/Actions/VirtualMedia.InsertMedia" % (self.host_uri, vcd)
            _payload = {"Image": path}
            _response = await self.post_request(_uri, payload=_payload, headers=_headers)
            status = _response.status
            if status == 204:
                self.logger.info("Image mounting operation was successful.")
            elif status == 405:
                self.logger.error("Virtual media mounting is not allowed on this server.")
                return False
            elif status == 500:
                self.logger.error("Couldn't mount virtual media, because there is virtual media mounted already.")
                return False
            else:
                raise BadfishException("There was something wrong trying to mount virtual media.")
        return True

    async def unmount_virtual_media(self):
        vm_config = await self.get_virtual_media_config()
        _headers = {"Content-Type": "application/json"}
        if self.vendor == "Supermicro":
            _uri = "%s%s/Actions/IsoConfig.UnMount" % (
                self.host_uri,
                vm_config["config"],
            )
            _response = await self.post_request(_uri, payload="{}", headers=_headers)
            if _response.status in [200, 202]:
                self.logger.info("Image unmount operation was successful.")
            else:
                raise BadfishException("There was something wrong trying to unmount virtual media.")
            _payload = {"Host": "", "Path": "", "Username": "", "Password": ""}
            _uri = "%s%s" % (self.host_uri, vm_config["config"])
            _response = await self.patch_request(_uri, payload=_payload, headers=_headers)
        else:
            vcd = [x for x in vm_config if "CD" in x][0]
            _uri = "%s%s/Actions/VirtualMedia.EjectMedia" % (self.host_uri, vcd)
            _response = await self.post_request(_uri, payload={}, headers=_headers)
            status = _response.status
            if status == 204:
                self.logger.info("Image unmount operation was successful.")
            elif status == 405:
                self.logger.error("Virtual media unmounting is not allowed on this server.")
                return False
            elif status == 500:
                self.logger.error("Couldn't unmount virtual media, because there isn't any virtual media mounted.")
                return False
            else:
                raise BadfishException("There was something wrong trying to unmount virtual media.")
        return True

    async def boot_to_virtual_media(self):
        og_log = self.logger
        self.logger = getLogger("Temp")
        inserted = await self.check_virtual_media()
        self.logger = og_log
        if not inserted:
            self.logger.error("No virtual CD is inserted.")
            return False

        _uri = "%s%s" % (self.host_uri, self.system_resource)
        _headers = {"Content-Type": "application/json"}
        if self.vendor == "Supermicro":
            _payload = {"Boot": {"BootSourceOverrideEnabled": "Once"}}

            _response = await self.get_request(_uri)
            try:
                raw = await _response.text("utf-8", "ignore")
                _data = json.loads(raw.strip())
                allowable_boot_targets = _data.get("Boot").get("BootSourceOverrideTarget@Redfish.AllowableValues")
            except ValueError:
                raise BadfishException("There was something wrong trying to boot to virtual media.")
            if "UsbCd" in allowable_boot_targets:
                _payload.get("Boot").update({"BootSourceOverrideTarget": "UsbCd"})
            else:
                _payload.get("Boot").update({"BootSourceOverrideTarget": "Cd"})

            _response = await self.patch_request(_uri, headers=_headers, payload=_payload)
            if _response.status == 200:
                self.logger.info("Command passed to set next onetime boot device to virtual media.")
            else:
                self.logger.error("Command failed to set next onetime boot device to virtual media.")
                return False
        else:
            vcd_check = await self.check_device("Optical.iDRACVirtual.1-1")
            if vcd_check:
                await self.boot_to("Optical.iDRACVirtual.1-1", True)
            else:
                self.logger.error(
                    "Command failed to set next onetime boot to virtual media. " "No virtual optical media boot device."
                )
                return False
        return True
