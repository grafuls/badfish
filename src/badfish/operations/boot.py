import asyncio
import json
import os

from badfish.core.exceptions import BadfishException


class BootOperations:
    """Boot management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
    async def get_boot_seq(self):
        bios_boot_mode = await self.get_bios_boot_mode()
        if bios_boot_mode == "Uefi":
            return "UefiBootSeq"
        else:
            return "BootSeq"

    async def get_bios_boot_mode(self):
        self.logger.debug("Getting bios boot mode.")
        attribute = "BootMode"
        bios_boot_mode = await self.get_bios_attribute(attribute)
        if not bios_boot_mode:
            self.logger.warning("Assuming boot mode is Bios.")
            bios_boot_mode = "Bios"
        self.logger.debug("Current boot mode: %s" % bios_boot_mode)
        return bios_boot_mode

    async def get_boot_devices(self):
        if not self.boot_devices:
            _boot_seq = await self.get_boot_seq()
            _uri = "%s%s/BootSources" % (self.host_uri, self.system_resource)
            _response = await self.get_request(_uri)

            if _response.status == 404:
                self.logger.debug(_response.text)
                raise BadfishException("Boot order modification is not supported by this host.")

            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            if "Attributes" in data:
                try:
                    self.boot_devices = data["Attributes"][_boot_seq]
                except KeyError:
                    for key in data["Attributes"].keys():
                        if "bootseq" in key.lower():
                            self.logger.debug("Boot sequence found: %s" % key)
                    raise BadfishException(
                        "The boot mode does not match the boot sequence. Try again in a few minutes."
                    )
            else:
                self.logger.debug(data)
                raise BadfishException("Boot order modification is not supported by this host.")

    async def boot_to(self, device, skip_job=False):
        device_check = await self.check_device(device)
        if device_check:
            await self.clear_job_queue()
            await self.send_one_time_boot(device)
            if not skip_job:
                await self.create_bios_config_job(self.bios_uri)
        else:
            return False
        return True

    async def boot_to_type(self, host_type, _interfaces_path):
        if _interfaces_path:
            if not os.path.exists(_interfaces_path):
                raise BadfishException("No such file or directory: %s." % _interfaces_path)
        else:
            raise BadfishException("You must provide a path to the interfaces yaml via `-i` optional argument.")
        host_types = await self.get_host_types_from_yaml(_interfaces_path)
        if host_type.lower() not in host_types:
            raise BadfishException(f"Expected values for -t argument are: {host_types}")

        device = await self.get_host_type_boot_device(host_type, _interfaces_path)

        await self.boot_to(device, True)

    async def boot_to_mac(self, mac_address):
        interfaces_endpoints = await self.get_interfaces_endpoints()

        device = None
        for endpoint in interfaces_endpoints:
            interface = await self.get_interface(endpoint)
            if interface.get("MACAddress", "").upper() == mac_address.upper():
                device = interface.get("Id")
                break

        if device:
            await self.boot_to(device)
        else:
            raise BadfishException("MAC Address does not match any of the existing")

    async def send_one_time_boot(self, device):
        boot_seq = await self.get_boot_seq()
        _payload = {
            "Attributes": {
                "OneTimeBootMode": f"OneTime{boot_seq}",
                f"OneTime{boot_seq}Dev": device,
            }
        }
        await self.patch_bios(_payload)

    async def change_boot(self, host_type, interfaces_path, pxe=False):
        if interfaces_path:
            if not os.path.exists(interfaces_path):
                raise BadfishException("No such file or directory: '%s'." % interfaces_path)
            host_types = await self.get_host_types_from_yaml(interfaces_path)
            if host_type.lower() not in host_types:
                raise BadfishException(f"Expected values for -t argument are: {host_types}")
        else:
            raise BadfishException("You must provide a path to the interfaces yaml via `-i` optional argument.")
        _type = None
        if host_type.lower() != "uefi":
            _type = await self.get_host_type(interfaces_path)
        if (_type and _type.lower() != host_type.lower()) or not _type:
            await self.clear_job_queue()
            if host_type.lower() == "uefi":
                payload = dict()
                boot_mode = await self.get_bios_boot_mode()
                if boot_mode.lower() != "uefi":
                    payload["BootMode"] = "Uefi"
                interfaces = await self.get_interfaces_by_type(host_type, interfaces_path)

                for i, interface in enumerate(interfaces, 1):
                    payload[f"PxeDev{i}Interface"] = interface
                    payload[f"PxeDev{i}EnDis"] = "Enabled"

                await self.set_bios_attribute(payload)

            else:
                boot_mode = await self.get_bios_boot_mode()
                if boot_mode.lower() == "uefi":
                    self.logger.warning(
                        "Changes being requested will be valid for Bios BootMode. " "Current boot mode is set to Uefi."
                    )
                await self.change_boot_order(host_type, interfaces_path)

                if pxe:
                    await self.set_next_boot_pxe()

                await self.create_bios_config_job(self.bios_uri)

                await self.reboot_server(graceful=False)

        else:
            self.logger.warning("No changes were made since the boot order already matches the requested.")
        return True

    async def change_boot_order(self, _host_type, _interfaces_path):
        interfaces = await self.get_interfaces_by_type(_host_type, _interfaces_path)

        await self.get_boot_devices()
        devices = [device["Name"] for device in self.boot_devices]
        valid_devices = [device for device in interfaces if device in devices]
        if len(valid_devices) < len(interfaces):
            diff = [device for device in interfaces if device not in valid_devices]
            self.logger.warning("Some interfaces are not valid boot devices. Ignoring: %s" % ", ".join(diff))
        change = False
        ordered_devices = self.boot_devices.copy()
        for i, interface in enumerate(valid_devices):
            for device in ordered_devices:
                if interface == device["Name"]:
                    if device["Index"] != i:
                        device["Index"] = i
                        change = True
                    break

        if change:
            await self.patch_boot_seq(ordered_devices)
        else:
            self.logger.warning("No changes were made since the boot order already matches the requested.")

    async def patch_boot_seq(self, ordered_devices):
        _boot_seq = await self.get_boot_seq()
        boot_sources_uri = "%s/BootSources/Settings" % self.system_resource
        url = "%s%s" % (self.host_uri, boot_sources_uri)
        payload = {"Attributes": {_boot_seq: ordered_devices}}
        headers = {"content-type": "application/json"}
        response = None
        _status_code = 400

        for _ in range(self.retries):
            if _status_code != 200:
                response = await self.patch_request(url, payload, headers, True)
                if response:
                    raw = await response.text("utf-8", "ignore")
                    self.logger.debug(raw)
                    _status_code = response.status
            else:
                break

        if _status_code == 200:
            self.logger.debug("PATCH command passed to update boot order.")
        else:
            self.logger.error("There was something wrong with your request.")

            if response:
                await self.error_handler(response)

    async def set_next_boot_pxe(self):
        _url = "%s%s" % (self.host_uri, self.system_resource)
        _payload = {
            "Boot": {
                "BootSourceOverrideTarget": "Pxe",
                "BootSourceOverrideEnabled": "Once",
            }
        }
        _headers = {"content-type": "application/json"}
        _response = await self.patch_request(_url, _payload, _headers)

        await asyncio.sleep(5)

        if _response.status == 200:
            self.logger.info('PATCH command passed to set next boot onetime boot device to: "%s".' % "Pxe")
        else:
            self.logger.error("Command failed, error code is %s." % _response.status)

            await self.error_handler(_response)

    async def check_supported_idrac_version(self):
        _url = "%s/Dell/Managers/iDRAC.Embedded.1/DellJobService/" % self.root_uri
        _response = await self.get_request(_url)
        if _response.status != 200:
            self.logger.warning("iDRAC version installed does not support DellJobService")
            return False

        return True

    async def get_host_type(self, _interfaces_path):
        await self.get_boot_devices()
        if _interfaces_path:
            host_types = await self.get_host_types_from_yaml(_interfaces_path)
            for host_type in host_types:
                match = True
                interfaces = await self.get_interfaces_by_type(host_type, _interfaces_path)

                for device in sorted(self.boot_devices[: len(interfaces)], key=lambda x: x["Index"]):
                    if device["Name"] == interfaces[device["Index"]]:
                        continue
                    else:
                        match = False
                        break
                if match:
                    return host_type

        return None

    async def patch_bios(self, payload, insist=True):
        _url = "%s%s" % (self.root_uri, self.bios_uri)
        _headers = {"content-type": "application/json"}
        _first_reset = False
        payload_patch = {"@Redfish.SettingsApplyTime": {"ApplyTime": "OnReset"}}
        payload_patch.update(payload)
        for i in range(self.retries):
            _response = await self.patch_request(_url, payload_patch, _headers)
            status_code = _response.status
            if status_code in [200, 202]:
                self.logger.info("Command passed to set BIOS attribute pending values.")
                break
            else:
                self.logger.error("Command failed, error code is: %s." % status_code)
                if status_code == 503 and i - 1 != self.retries:
                    self.logger.info("Retrying to send one time boot.")
                    continue
                elif status_code == 400 and insist:
                    await self.clear_job_queue()
                    if not _first_reset:
                        await self.reset_idrac()
                        await asyncio.sleep(10)
                        _first_reset = True
                        await self.polling_host_state("On")
                    continue
                await self.error_handler(_response)

    async def check_boot(self, _interfaces_path):
        if not self.boot_devices:
            await self.get_boot_devices()

        if _interfaces_path:
            _host_type = await self.get_host_type(_interfaces_path)
            if _host_type:
                self.logger.warning("Current boot order is set to: %s." % _host_type)
                return True
            else:
                self.logger.warning("Current boot order does not match any of the given.")
                self.logger.info("Current boot order:")
        else:
            self.logger.info("Current boot order:")
        for device in sorted(self.boot_devices, key=lambda x: x["Index"]):
            enabled = "" if device["Enabled"] else " (DISABLED)"
            self.logger.info("%s: %s%s" % (int(device["Index"]) + 1, device["Name"], enabled))
        return True

    async def get_host_type_boot_device(self, host_type, _interfaces_path):
        if _interfaces_path:
            interfaces = await self.get_interfaces_by_type(host_type, _interfaces_path)
        else:
            raise BadfishException("You must provide a path to the interfaces yaml via `-i` optional argument.")

        return interfaces[0]

    async def toggle_boot_device(self, device):
        if not self.boot_devices:
            await self.get_boot_devices()

        if device not in [boot_device["Name"] for boot_device in self.boot_devices]:
            self.logger.warning("Accepted device names:")
            for device in self.boot_devices:
                self.logger.warning(f"{device['Name']}")
            raise BadfishException("Boot device name not found")

        new_boot_seq = self.boot_devices.copy()
        state = ""
        for boot_device in new_boot_seq:
            if boot_device["Name"] == device:
                boot_device["Enabled"] = not boot_device["Enabled"]
                state = "enabled" if boot_device["Enabled"] else "disabled"

        await self.patch_boot_seq(new_boot_seq)
        if state:
            self.logger.info(f"{device} has now been {state}")

        await self.create_bios_config_job(self.bios_uri)
        await self.reboot_server(graceful=False)
        return True

    async def check_remote_image(self):
        if not await self.check_os_deployment_support():
            return False
        _uri = (
            "%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService."
            "GetAttachStatus" % self.host_uri
        )
        _headers = {"Content-Type": "application/json"}
        _response = await self.post_request(_uri, payload={}, headers=_headers)
        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            if _response.status == 200:
                self.logger.info("Current ISO attach status: %s" % data.get("ISOAttachStatus"))
                if data.get("ISOAttachStatus") == "Attached":
                    return True
            else:
                self.logger.error("Command failed to get attach status of the remote mounted ISO.")
        except ValueError:
            raise BadfishException("There was something wrong trying to check remote image attach status.")
        return False

    async def boot_remote_image(self, nfs_path):
        if not await self.check_os_deployment_support():
            return False
        _uri = (
            "%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService"
            ".BootToNetworkISO" % self.host_uri
        )
        _headers = {"Content-Type": "application/json"}
        try:
            split_path = str(nfs_path).split(":")
            last_slash_pos = split_path[1].rindex("/") + 1
            _payload = {
                "ShareType": "NFS",
                "IPAddress": split_path[0],
                "ShareName": split_path[1][:last_slash_pos],
                "ImageName": split_path[1][last_slash_pos:],
            }
            if len(_payload.get("ImageName")) == 0:
                raise ValueError
        except (ValueError, IndexError):
            self.logger.error("Wrong NFS path format.")
            return False
        _response = await self.post_request(_uri, payload=_payload, headers=_headers)
        if _response.status == 202:
            self.logger.info("Command for booting to remote ISO was successful, job was created.")
            try:
                task_path = _response.headers.get("Location")
                response = await self.get_request(f"{self.host_uri}{task_path}")
                raw = await response.text("utf-8", "ignore")
                data = json.loads(raw.strip())
                if data.get("TaskStatus") == "OK":
                    self.logger.info("OSDeployment task status is OK.")
                else:
                    self.logger.error("OSDeployment task failed and couldn't be completed.")
                    return False
            except (ValueError, AttributeError):
                raise BadfishException("There was something wrong trying to check remote image attach status.")
            return True
        else:
            self.logger.error("Command failed to boot to remote ISO. No job was created.")
        return False

    async def detach_remote_image(self):
        if not await self.check_os_deployment_support():
            return False
        _uri = (
            "%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService/Actions/DellOSDeploymentService"
            ".DetachISOImage" % self.host_uri
        )
        _headers = {"Content-Type": "application/json"}
        _response = await self.post_request(_uri, payload={}, headers=_headers)
        if _response.status == 200:
            self.logger.info("Command to detach remote ISO was successful.")
            return True
        else:
            self.logger.error("Command failed to detach remote mounted ISO.")
        return False

    async def check_os_deployment_support(self):
        _uri = "%s/redfish/v1/Dell/Systems/System.Embedded.1/DellOSDeploymentService" % self.host_uri
        _response = await self.get_request(_uri)
        await _response.text("utf-8", "ignore")
        if _response.status != 200:
            self.logger.error(
                "iDRAC version installed doesn't support DellOSDeploymentService needed for this feature."
            )
            return False
        return True
    
    async def check_device(self, device):
        self.logger.debug("Checking device %s." % device)
        await self.get_boot_devices()
        self.logger.debug(self.boot_devices)
        boot_devices = [_device["Name"].lower() for _device in self.boot_devices]
        if device.lower() in boot_devices:
            return True
        else:
            self.logger.error(
                "Device %s does not match any of the available boot devices for host %s" % (device, self.host)
            )
            return False