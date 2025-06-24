#!/usr/bin/env python3
import asyncio
import functools
import argparse
import sys
import warnings
import tempfile
from typing import Optional, Dict, Any

from badfish.core.exceptions import BadfishException
from badfish.core.factory import badfish_factory, RETRIES
from badfish.helpers.logger import BadfishLogger
from logging import DEBUG, INFO, getLogger

warnings.filterwarnings("ignore")


class BadfishConfig:
    """Configuration class to hold all command line arguments for Badfish operations."""
    
    def __init__(self, args_dict: Dict[str, Any]):
        # Core connection settings
        self.username = args_dict["u"]
        self.password = args_dict["p"]
        self.host_type = args_dict["t"]
        self.interfaces_path = args_dict["i"]
        self.retries = int(args_dict["retries"])
        
        # Boot operations
        self.force = args_dict["force"]
        self.pxe = args_dict["pxe"]
        self.device = args_dict["boot_to"]
        self.boot_to_type = args_dict["boot_to_type"]
        self.boot_to_mac = args_dict["boot_to_mac"]
        self.check_boot = args_dict["check_boot"]
        self.toggle_boot_device = args_dict["toggle_boot_device"]
        
        # Power operations
        self.reboot_only = args_dict["reboot_only"]
        self.power_state = args_dict["power_state"]
        self.power_on = args_dict["power_on"]
        self.power_off = args_dict["power_off"]
        self.power_cycle = args_dict["power_cycle"]
        self.power_consumed_watts = args_dict["get_power_consumed"]
        
        # Reset operations
        self.rac_reset = args_dict["racreset"]
        self.bmc_reset = args_dict["bmc_reset"]
        self.factory_reset = args_dict["factory_reset"]
        
        # Job operations
        self.clear_jobs = args_dict["clear_jobs"]
        self.check_job = args_dict["check_job"]
        self.list_jobs = args_dict["ls_jobs"]
        
        # Inventory operations
        self.firmware_inventory = args_dict["firmware_inventory"]
        self.list_interfaces = args_dict["ls_interfaces"]
        self.list_gpu = args_dict["ls_gpu"]
        self.list_processors = args_dict["ls_processors"]
        self.list_memory = args_dict["ls_memory"]
        self.list_serial = args_dict["ls_serial"]
        
        # Virtual media operations
        self.check_virtual_media = args_dict["check_virtual_media"]
        self.unmount_virtual_media = args_dict["unmount_virtual_media"]
        self.mount_virtual_media = args_dict["mount_virtual_media"]
        self.boot_to_virtual_media = args_dict["boot_to_virtual_media"]
        
        # Remote image operations
        self.check_remote_image = args_dict["check_remote_image"]
        self.boot_remote_image = args_dict["boot_remote_image"]
        self.detach_remote_image = args_dict["detach_remote_image"]
        
        # SRIOV operations
        self.get_sriov = args_dict["get_sriov"]
        self.enable_sriov = args_dict["enable_sriov"]
        self.disable_sriov = args_dict["disable_sriov"]
        
        # BIOS operations
        self.set_bios_attribute = args_dict["set_bios_attribute"]
        self.get_bios_attribute = args_dict["get_bios_attribute"]
        self.attribute = args_dict["attribute"]
        self.value = args_dict["value"]
        self.set_bios_password = args_dict["set_bios_password"]
        self.remove_bios_password = args_dict["remove_bios_password"]
        self.new_password = args_dict["new_password"]
        self.old_password = args_dict["old_password"]
        
        # Screenshot
        self.screenshot = args_dict["screenshot"]
        
        # SCP operations
        self.get_scp_targets = args_dict["get_scp_targets"]
        self.scp_targets = args_dict["scp_targets"]
        self.scp_include_read_only = args_dict["scp_include_read_only"]
        self.export_scp = args_dict["export_scp"]
        self.import_scp = args_dict["import_scp"]
        
        # NIC operations
        self.get_nic_fqdds = args_dict["get_nic_fqdds"]
        self.get_nic_attribute = args_dict["get_nic_attribute"]
        self.set_nic_attribute = args_dict["set_nic_attribute"]
        
        # Host identification
        self.rack = args_dict["rack"]
        self.uloc = args_dict["uloc"]
        self.blade = args_dict["blade"]
        
        # Output and logging
        self.output = args_dict["output"]
        self.host_list = args_dict["host_list"]


class BadfishCommand:
    """Base class for Badfish commands."""
    
    def __init__(self, config: BadfishConfig):
        self.config = config
    
    async def execute(self, badfish) -> bool:
        """Execute the command on the given badfish instance. Returns True if command was executed."""
        raise NotImplementedError


class BootCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.device:
            await badfish.boot_to(self.config.device)
            return True
        elif self.config.boot_to_type:
            await badfish.boot_to_type(self.config.boot_to_type, self.config.interfaces_path)
            return True
        elif self.config.boot_to_mac:
            await badfish.boot_to_mac(self.config.boot_to_mac)
            return True
        elif self.config.check_boot:
            await badfish.check_boot(self.config.interfaces_path)
            return True
        elif self.config.toggle_boot_device:
            await badfish.toggle_boot_device(self.config.toggle_boot_device)
            return True
        elif self.config.host_type:
            await badfish.change_boot(self.config.host_type, self.config.interfaces_path, self.config.pxe)
            return True
        return False


class PowerCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.power_state:
            state = await badfish.get_power_state()
            badfish.logger.info("Power state:")
            badfish.logger.info(f"    {badfish.host}: '{state}'")
            return True
        elif self.config.power_on:
            await badfish.set_power_state("on")
            return True
        elif self.config.power_off:
            await badfish.set_power_state("off")
            return True
        elif self.config.power_cycle:
            await badfish.reboot_server(graceful=False)
            return True
        elif self.config.reboot_only:
            await badfish.reboot_server()
            return True
        elif self.config.power_consumed_watts:
            await badfish.get_power_consumed_watts()
            return True
        return False

<<<<<<< Updated upstream
    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.delete_session()
        if exc_type is not None:
            self.logger.debug(f"Exiting context with exception: {exc_type.__name__}: {exc_val}")
        return False

    async def init(self):
        self.session_uri = await self.find_session_uri()
        self.token = await self.validate_credentials()
        self.system_resource = await self.find_systems_resource()
        self.manager_resource = await self.find_managers_resource()
        self.bios_uri = "%s/Bios/Settings" % self.system_resource[len(self.redfish_uri) :]
=======
>>>>>>> Stashed changes

class ResetCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.rac_reset:
            await badfish.reset_idrac()
            return True
        elif self.config.bmc_reset:
            await badfish.reset_bmc()
            return True
        elif self.config.factory_reset:
            await badfish.reset_bios()
            return True
        return False


class JobCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.clear_jobs:
            await badfish.clear_job_queue(self.config.force)
            return True
        elif self.config.check_job:
            await badfish.check_schedule_job_status(self.config.check_job)
            return True
        elif self.config.list_jobs:
            await badfish.list_job_queue()
            return True
        return False


class InventoryCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.firmware_inventory:
            await badfish.get_firmware_inventory()
            return True
        elif self.config.list_interfaces:
            await badfish.list_interfaces()
            return True
        elif self.config.list_processors:
            await badfish.list_processors()
            return True
        elif self.config.list_gpu:
            await badfish.list_gpu()
            return True
        elif self.config.list_memory:
            await badfish.list_memory()
            return True
        elif self.config.list_serial:
            await badfish.list_serial()
            return True
        return False


class VirtualMediaCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.check_virtual_media:
            await badfish.check_virtual_media()
            return True
        elif self.config.mount_virtual_media:
            await badfish.mount_virtual_media(self.config.mount_virtual_media)
            return True
        elif self.config.unmount_virtual_media:
            await badfish.unmount_virtual_media()
            return True
        elif self.config.boot_to_virtual_media:
            await badfish.boot_to_virtual_media()
            return True
        return False


class RemoteImageCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.check_remote_image:
            await badfish.check_remote_image()
            return True
        elif self.config.boot_remote_image:
            await badfish.boot_remote_image(self.config.boot_remote_image)
            return True
        elif self.config.detach_remote_image:
            await badfish.detach_remote_image()
            return True
        return False


class SRIOVCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.get_sriov:
            sriov_mode = await badfish.get_sriov_mode()
            if sriov_mode:
                badfish.logger.info(sriov_mode)
            return True
        elif self.config.enable_sriov:
            await badfish.send_sriov_mode(True)
            return True
        elif self.config.disable_sriov:
            await badfish.send_sriov_mode(False)
            return True
        return False


class BIOSCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.get_bios_attribute:
            if self.config.attribute:
                await badfish.get_bios_attribute_registry(self.config.attribute)
            else:
                data = await badfish.get_bios_attributes()
                for attribute, value in data["Attributes"].items():
                    badfish.logger.info(f"{attribute}: {value}")
            return True
        elif self.config.set_bios_attribute:
            payload = {self.config.attribute: self.config.value}
            await badfish.set_bios_attribute(payload)
            return True
        elif self.config.set_bios_password:
            await badfish.set_bios_password(self.config.old_password, self.config.new_password)
            return True
        elif self.config.remove_bios_password:
            await badfish.remove_bios_password(self.config.old_password)
            return True
        return False


class ScreenshotCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.screenshot:
            await badfish.take_screenshot()
            return True
        return False


class SCPCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.get_scp_targets:
            await badfish.get_scp_targets(self.config.get_scp_targets)
            return True
        elif self.config.export_scp:
            await badfish.export_scp(self.config.export_scp, self.config.scp_targets, self.config.scp_include_read_only)
            return True
        elif self.config.import_scp:
            await badfish.import_scp(self.config.import_scp, self.config.scp_targets)
            return True
        return False


class NICCommand(BadfishCommand):
    async def execute(self, badfish) -> bool:
        if self.config.get_nic_fqdds:
            await badfish.get_nic_fqdds()
            return True
        elif self.config.get_nic_attribute:
            if self.config.attribute:
                await badfish.get_nic_attribute_info(self.config.get_nic_attribute, self.config.attribute)
            else:
                await badfish.get_nic_attribute(self.config.get_nic_attribute)
            return True
        elif self.config.set_nic_attribute:
            await badfish.set_nic_attribute(self.config.set_nic_attribute, self.config.attribute, self.config.value)
            return True
        return False


class BadfishCommandExecutor:
    """Executes commands on a Badfish instance."""
    
    def __init__(self, config: BadfishConfig):
        self.config = config
        self.commands = [
            BootCommand(config),
            PowerCommand(config),
            ResetCommand(config),
            JobCommand(config),
            InventoryCommand(config),
            VirtualMediaCommand(config),
            RemoteImageCommand(config),
            SRIOVCommand(config),
            BIOSCommand(config),
            ScreenshotCommand(config),
            SCPCommand(config),
            NICCommand(config),
        ]
    
    async def execute(self, badfish) -> bool:
        """Execute the first matching command. Returns True if any command was executed."""
        for command in self.commands:
            if await command.execute(badfish):
                return True
        
        # Handle PXE boot if no other boot command was executed
        if self.config.pxe and not self.config.host_type:
            await badfish.set_next_boot_pxe()
            return True
        
        return False


<<<<<<< Updated upstream
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

    async def polling_host_state(self, state, equals=True):
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
                self.progress_bar(self.retries, self.retries, current_state)
                break
            self.progress_bar(count, self.retries, current_state)

        return desired_state

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

    async def get_network_adapters(self):
        _url = "%s%s/NetworkAdapters" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_url)
        try:
            raw = await _response.text("utf-8", "ignore")
            na_data = json.loads(raw.strip())

            root_nics = []
            if na_data.get("Members"):
                for member in na_data["Members"]:
                    root_nics.append(member["@odata.id"])

            data = {}
            for nic in root_nics:
                net_ports_url = "%s%s/NetworkPorts" % (self.host_uri, nic)
                rn_response = await self.get_request(net_ports_url)
                rn_raw = await rn_response.text("utf-8", "ignore")
                rn_data = json.loads(rn_raw.strip())

                nic_ports = []
                if rn_data.get("Members"):
                    for member in rn_data["Members"]:
                        nic_ports.append(member["@odata.id"])

                net_df_url = "%s%s/NetworkDeviceFunctions" % (self.host_uri, nic)
                ndf_response = await self.get_request(net_df_url)
                ndf_raw = await ndf_response.text("utf-8", "ignore")
                ndf_data = json.loads(ndf_raw.strip())

                ndf_members = []
                if ndf_data.get("Members"):
                    for member in ndf_data["Members"]:
                        ndf_members.append(member["@odata.id"])

                for i, nic_port in enumerate(nic_ports):
                    np_url = "%s%s" % (self.host_uri, nic_port)
                    np_response = await self.get_request(np_url)
                    np_raw = await np_response.text("utf-8", "ignore")
                    np_data = json.loads(np_raw.strip())

                    interface = nic_port.split("/")[-1]

                    fields = [
                        "Id",
                        "LinkStatus",
                        "SupportedLinkCapabilities",
                    ]
                    values = {}
                    for field in fields:
                        value = np_data.get(field)
                        if value:
                            values[field] = value

                    ndf_url = "%s%s" % (self.host_uri, ndf_members[i])
                    ndf_response = await self.get_request(ndf_url)
                    ndf_raw = await ndf_response.text("utf-8", "ignore")
                    ndf_data = json.loads(ndf_raw.strip())
                    oem = ndf_data.get("Oem")
                    ethernet = ndf_data.get("Ethernet")
                    if ethernet:
                        mac_address = ethernet.get("MACAddress")
                        if mac_address:
                            values["MACAddress"] = mac_address
                    if oem:
                        dell = oem.get("Dell")
                        if dell:
                            dell_nic = dell.get("DellNIC")
                            vendor = dell_nic.get("VendorName")
                            if dell_nic.get("VendorName"):
                                values["Vendor"] = vendor

                    data.update({interface: values})

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting network interfaces")

        return data

    async def get_ethernet_interfaces(self):
        _url = "%s%s/EthernetInterfaces" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_url)

        if _response.status == 404:
            raise BadfishException("Server does not support this functionality")

        try:
            raw = await _response.text("utf-8", "ignore")
            ei_data = json.loads(raw.strip())

            interfaces = []
            if ei_data.get("Members"):
                for member in ei_data["Members"]:
                    interfaces.append(member["@odata.id"])

            data = {}
            for interface in interfaces:
                interface_url = "%s%s" % (self.host_uri, interface)
                int_response = await self.get_request(interface_url)
                int_raw = await int_response.text("utf-8", "ignore")
                int_data = json.loads(int_raw.strip())

                int_name = int_data.get("Id")
                fields = [
                    "Name",
                    "MACAddress",
                    "Status",
                    "LinkStatus",
                    "SpeedMbps",
                ]

                values = {}
                for field in fields:
                    value = int_data.get(field)
                    if value:
                        values[field] = value

                data.update({int_name: values})

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting network interfaces")

        return data

    async def list_interfaces(self):
        na_supported = await self.check_supported_network_interfaces("NetworkAdapters")
        if na_supported:
            self.logger.debug("Getting Network Adapters")
            data = await self.get_network_adapters()
        else:
            ei_supported = await self.check_supported_network_interfaces("EthernetInterfaces")
            if ei_supported:
                self.logger.debug("Getting Ethernet interfaces")
                data = await self.get_ethernet_interfaces()
            else:
                self.logger.error("Server does not support this functionality")
                return False

        for interface, properties in data.items():
            self.logger.info(f"{interface}:")
            for key, value in properties.items():
                if key == "SupportedLinkCapabilities":
                    speed_key = "LinkSpeedMbps"
                    speed = value[0].get(speed_key)
                    if speed:
                        self.logger.info(f"    {speed_key}: {speed}")
                elif key == "Status":
                    health_key = "Health"
                    health = value.get(health_key)
                    if health:
                        self.logger.info(f"    {health_key}: {health}")
                else:
                    self.logger.info(f"    {key}: {value}")

        return True

    async def get_processor_summary(self):
        _url = "%s%s" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_url)

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())

            proc_data = data.get("ProcessorSummary")

            if not proc_data:
                raise BadfishException("Server does not support this functionality")

            fields = [
                "Count",
                "LogicalProcessorCount",
                "Model",
            ]

            values = {}
            for field in fields:
                value = proc_data.get(field)
                if value:
                    values[field] = value

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting processor summary")

        return values

    async def get_processor_details(self):
        _url = "%s%s/Processors" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_url)

        if _response.status == 404:
            raise BadfishException("Server does not support this functionality")

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())

            processors = []
            if data.get("Members"):
                for member in data["Members"]:
                    if "CPU" in member["@odata.id"]:
                        processors.append(member["@odata.id"])

            proc_details = {}
            for processor in processors:
                processor_url = "%s%s" % (self.host_uri, processor)
                proc_response = await self.get_request(processor_url)
                proc_raw = await proc_response.text("utf-8", "ignore")
                proc_data = json.loads(proc_raw.strip())

                proc_name = proc_data.get("Id")
                fields = [
                    "Name",
                    "InstructionSet",
                    "Manufacturer",
                    "MemoryDeviceType",
                    "MaxSpeedMHz",
                    "Model",
                    "TotalCores",
                    "TotalThreads",
                ]

                values = {}
                for field in fields:
                    value = proc_data.get(field)
                    if value:
                        values[field] = value

                proc_details.update({proc_name: values})

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting processor details")

        return proc_details

    async def get_gpu_data(self):
        _url = "%s%s/Processors" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_url)

        if _response.status == 404:
            raise BadfishException("GPU endpoint not available on host.")

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting GPU data")
        return data

    async def get_gpu_responses(self, data):
        gpu_responses = []
        gpu_endpoints = []
        try:
            if data.get("Members"):
                for member in data["Members"]:
                    if "Video" in member["@odata.id"] or "ProcAccelerator" in member["@odata.id"]:
                        gpu_endpoints.append(member["@odata.id"])

            for gpu in gpu_endpoints:
                gpu_url = "%s%s" % (self.host_uri, gpu)
                gpu_response = await self.get_request(gpu_url)
                gpu_raw = await gpu_response.text("utf-8", "ignore")
                gpu_data = json.loads(gpu_raw.strip())
                gpu_responses.append(gpu_data)

        except (ValueError, AttributeError):  # pragma: no cover
            raise BadfishException("There was something wrong getting host GPU details")

        return gpu_responses

    async def get_gpu_summary(self, gpu_responses):
        gpu_summary = {}
        try:
            for gpu_data in gpu_responses:

                gpu_model = gpu_data["Model"]

                if not gpu_summary.get(gpu_model):
                    gpu_summary[gpu_model] = 1
                else:
                    gpu_summary[gpu_model] = gpu_summary[gpu_model] + 1

        except (ValueError, AttributeError, KeyError):
            raise BadfishException("There was something wrong getting GPU summary values.")
        return gpu_summary

    async def get_gpu_details(self, gpu_responses):
        try:
            gpu_details = {}
            for gpu_data in gpu_responses:

                gpu_name = gpu_data.get("Id")
                fields = [
                    "Model",
                    "Manufacturer",
                    "ProcessorType",
                ]

                values = {}
                for field in fields:
                    value = gpu_data.get(field)
                    if value:
                        values[field] = value

                gpu_details.update({gpu_name: values})

        except (ValueError, AttributeError):  # pragma: no cover
            raise BadfishException("There was something wrong getting host GPU details values.")

        return gpu_details

    async def get_memory_summary(self):
        _url = "%s%s" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_url)

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())

            proc_data = data.get("MemorySummary")

            if not proc_data:
                raise BadfishException("Server does not support this functionality")

            fields = [
                "MemoryMirroring",
                "TotalSystemMemoryGiB",
            ]

            values = {}
            for field in fields:
                value = proc_data.get(field)
                if value:
                    values[field] = value

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting memory summary")

        return values

    async def get_memory_details(self):
        _url = "%s%s/Memory" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_url)

        if _response.status == 404:
            raise BadfishException("Server does not support this functionality")

        try:
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())

            memories = []
            if data.get("Members"):
                for member in data["Members"]:
                    memories.append(member["@odata.id"])

            mem_details = {}
            for memory in memories:
                memory_url = "%s%s" % (self.host_uri, memory)
                mem_response = await self.get_request(memory_url)
                mem_raw = await mem_response.text("utf-8", "ignore")
                mem_data = json.loads(mem_raw.strip())

                mem_name = mem_data.get("Name")
                fields = [
                    "CapacityMiB",
                    "Description",
                    "Manufacturer",
                    "MemoryDeviceType",
                    "OperatingSpeedMhz",
                ]

                values = {}
                for field in fields:
                    value = mem_data.get(field)
                    if value:
                        values[field] = value

                mem_details.update({mem_name: values})

        except (ValueError, AttributeError):
            raise BadfishException("There was something wrong getting memory details")

        return mem_details

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

    async def list_processors(self):
        data = await self.get_processor_summary()

        self.logger.info("Processor Summary:")
        for _key, _value in data.items():
            self.logger.info(f"    {_key}: {_value}")

        processor_data = await self.get_processor_details()

        for _processor, _properties in processor_data.items():
            self.logger.info(f"{_processor}:")
            for _key, _value in _properties.items():
                self.logger.info(f"    {_key}: {_value}")

        return True

    async def list_gpu(self):
        data = await self.get_gpu_data()
        gpu_responses = await self.get_gpu_responses(data)

        summary = await self.get_gpu_summary(gpu_responses)

        self.logger.info("GPU Summary:")
        for _key, _value in summary.items():
            self.logger.info(f"  Model: {_key} (Count: {_value})")

        self.logger.info("Current GPU's on host:")

        gpu_data = await self.get_gpu_details(gpu_responses)

        for _gpu, _properties in gpu_data.items():
            self.logger.info(f"  {_gpu}:")
            for _key, _value in _properties.items():
                self.logger.info(f"    {_key}: {_value}")

        return True

    async def list_memory(self):
        data = await self.get_memory_summary()

        self.logger.info("Memory Summary:")
        for _key, _value in data.items():
            self.logger.info(f"    {_key}: {_value}")

        memory_data = await self.get_memory_details()

        for _memory, _properties in memory_data.items():
            self.logger.info(f"{_memory}:")
            for _key, _value in _properties.items():
                self.logger.info(f"    {_key}: {_value}")

        return True

    async def list_serial(self):
        data = await self.get_serial_summary()

        if "ServiceTag" in data:
            self.logger.info("ServiceTag:")
            self.logger.info(f"    {self.host}: {data.get('ServiceTag')}")
        else:
            self.logger.info("Serial Number:")
            self.logger.info(f"    {self.host}: {data}")

        return True

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

    async def delete_session(self):
        try:
            try:
                if not self.session_id:
                    self.logger.debug("No session ID found, skipping session deletion")
                    return
                headers = {"content-type": "application/json"}
                _uri = "%s%s" % (self.host_uri, self.session_id)
                try:
                    _response = await self.delete_request(_uri, headers=headers)
                    if _response.status in [200, 201]:
                        self.logger.debug(f"Session successfully deleted for {self.host}")
                    elif _response.status == 404:
                        self.logger.debug(f"Session not found (404) for {self.host}, may have been already deleted")
                    else:
                        self.logger.warning(f"Unexpected status {_response.status} when deleting session for {self.host}.")
                except Exception as ex:
                    self.logger.warning(f"Failed to delete session for {self.host}: {ex}")
            finally:
                self.session_id = None
                self.token = None
        except Exception:
            self.session_id = None
            self.token = None

    async def get_scp_targets(self, op):
        uri = "%s%s" % (self.host_uri, self.manager_resource)
        response = await self.get_request(uri)
        try:
            raw = await response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            _ = response.status
            filtered_data = [
                val for key, val in data.get("Actions").get("Oem").items() if key.endswith(f"{op}SystemConfiguration")
            ]
            if filtered_data:
                if filtered_data[0].get("ShareParameters").get("Target@Redfish.AllowableValues"):
                    self.logger.info(f"The allowable SCP {op} targets are:")
                    for i in filtered_data[0].get("ShareParameters").get("Target@Redfish.AllowableValues"):
                        self.logger.info(i)
                    return True
                else:
                    self.logger.error(
                        f"Couldn't find a list of possible targets, but {op} with SCP " f"should be allowed."
                    )
            else:
                self.logger.error(f"iDRAC on this system doesn't seem to support SCP {op}.")
        except (ValueError, AttributeError, TypeError):
            raise BadfishException(f"There was something wrong trying to get targets for SCP {op}.")
        return False

    async def export_scp(self, file_path, targets="ALL", include_read_only=False):
        uri = "%s%s/Actions/Oem/EID_674_Manager.ExportSystemConfiguration" % (self.host_uri, self.manager_resource)
        headers = {"Content-Type": "application/json"}
        payload = {
            "ExportFormat": "JSON",
            "ExportUse": "Default",
            "IncludeInExport": ("Default" if not include_read_only else "IncludeReadOnly"),
            "ShareParameters": {"Target": targets},
        }
        response = await self.post_request(uri, payload, headers)
        if response.status != 202:
            self.logger.error("Command failed to export system configuration.")
            return False
        try:
            job_id = response.headers["Location"].split("/")[-1]
        except (ValueError, AttributeError, KeyError):
            self.logger.error("Failed to find a job ID in headers of the response.")
            return False
        self.logger.info(f"Job for exporting server configuration, successfully created. Job ID: {job_id}")
        start_time = get_now()
        percentage = 0
        while True:
            ct = get_now() - start_time
            uri = "%s/redfish/v1/TaskService/Tasks/%s" % (self.host_uri, job_id)
            response = await self.get_raw(uri)
            raw = await response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            if "SystemConfiguration" in data:
                now = get_now()
                filename = file_path + now.strftime(f"%Y-%m-%d_%H%M%S_targets_{targets.replace(',', '-')}_export.json")
                open_file = open(filename, "w")
                open_file.write(json.dumps(data, indent=4))
                open_file.close()
                self.logger.info("SCP export went through successfully.")
                self.logger.info("Exported system configuration to file: %s" % filename)
                break
            if response.status in [200, 202]:
                await asyncio.sleep(1)
            else:
                self.logger.error("Unable to get detail for the job, command failed.")
                return False
            if str(ct)[0:7] >= "0:05:00":
                self.logger.error("Job has been timed out, took longer than 5 minutes, command failed.")
                return False
            else:
                try:
                    if percentage < int(data["Oem"]["Dell"]["PercentComplete"]):
                        percentage = int(data["Oem"]["Dell"]["PercentComplete"])
                        self.logger.info(
                            "%s, percent complete: %s"
                            % (data["Oem"]["Dell"]["Message"], data["Oem"]["Dell"]["PercentComplete"])
                        )
                    await asyncio.sleep(1)
                except (ValueError, AttributeError, KeyError):
                    self.logger.info("Unable to get job status message, trying again.")
                    await asyncio.sleep(1)
                continue
        return True

    async def import_scp(self, file_path, targets="ALL"):
        try:
            open_file = open(file_path, "r")
        except IOError:
            self.logger.error("File doesn't exist or couldn't be opened.")
            return False
        modify_file = open_file.read()
        power_state = await self.get_power_state()
        uri = "%s%s/Actions/Oem/EID_674_Manager.ImportSystemConfiguration" % (self.host_uri, self.manager_resource)
        headers = {"Content-Type": "application/json"}
        payload = {
            "ImportBuffer": modify_file,
            "ShutdownType": "Graceful",
            "HostPowerState": power_state,
            "ShareParameters": {"Target": targets},
        }

        response = await self.post_request(uri, payload, headers)
        if response.status != 202:
            self.logger.error("Command failed to import system configuration.")
            return False
        try:
            job_id = response.headers["Location"].split("/")[-1]
        except (ValueError, AttributeError, KeyError):
            self.logger.error("Failed to find a job ID in headers of the response.")
            return False
        self.logger.info(f"Job for importing server configuration, successfully created. Job ID: {job_id}")
        start_time = get_now()
        percentage = 0
        fail_states = ["Failed", "CompletedWithErrors"]
        while True:
            ct = get_now() - start_time
            uri = "%s/redfish/v1/TaskService/Tasks/%s" % (self.host_uri, job_id)
            response = await self.get_raw(uri)
            raw = await response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            if response.status in [200, 202]:
                await asyncio.sleep(1)
            else:
                self.logger.error("Unable to get detail for the job, command failed.")
                return False
            if str(ct)[0:7] >= "0:15:00":
                self.logger.error("Job has been timed out, took longer than 5 minutes, command failed.")
                return False
            if "Oem" not in data:
                self.logger.info("Unable to locate OEM data in JSON response, trying again.")
                await asyncio.sleep(3)
                continue
            try:
                if percentage < int(data["Oem"]["Dell"]["PercentComplete"]):
                    percentage = int(data["Oem"]["Dell"]["PercentComplete"])
                    self.logger.info(
                        "%s, percent complete: %s"
                        % (data["Oem"]["Dell"]["Message"], data["Oem"]["Dell"]["PercentComplete"])
                    )
                await asyncio.sleep(1)
                if percentage != 100:
                    continue
            except (ValueError, AttributeError, KeyError):
                self.logger.info("Unable to get job status message, trying again.")
                await asyncio.sleep(3)
                continue
            try:
                if data["Oem"]["Dell"]["JobState"] in fail_states:
                    self.logger.error(f"Command failed, job status = {data['Oem']['Dell']['JobState']}")
                    return False
                elif data["Oem"]["Dell"]["JobState"] == "Completed":
                    self.logger.info("Command passed, job successfully marked as completed. Going to reboot.")
                    break
            except (ValueError, AttributeError, KeyError):
                self.logger.info("Unable to get job status, trying again")
                await asyncio.sleep(3)
                continue
        return True

    async def get_nic_fqdds(self):
        uri = "%s%s/NetworkAdapters" % (self.host_uri, self.system_resource)
        resp = await self.get_request(uri)
        if resp.status == 404 or self.vendor == "Supermicro":
            self.logger.error("Operation not supported by vendor.")
            return False

        try:
            raw = await resp.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            nic_list = [[nic[1].split("/")[-1] for nic in member.items()][0] for member in data.get("Members")]
            self.logger.debug("Detected NIC FQDDs for existing network adapters.")
            for nic in nic_list:
                uri = "%s%s/NetworkAdapters/%s/NetworkDeviceFunctions" % (self.host_uri, self.system_resource, nic)
                resp = await self.get_request(uri)
                raw = await resp.text("utf-8", "ignore")
                data = json.loads(raw.strip())
                nic_fqqds = [[fqdd[1].split("/")[-1] for fqdd in member.items()][0] for member in data.get("Members")]
                self.logger.info(f"{nic}:")
                for i, fqdd in enumerate(nic_fqqds, start=1):
                    self.logger.info(f"    {i}: {fqdd}")
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            self.logger.error("Was unable to get NIC FQDDs, invalid server response.")
            return False
        return True

    async def get_nic_attribute(self, fqdd, log=True):
        uri = "%s/Chassis/%s/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s" % (
            self.root_uri,
            self.system_resource.split("/")[-1],
            fqdd.split("-")[0],
            fqdd,
            fqdd,
        )
        resp = await self.get_request(uri)
        if resp.status == 404 or self.vendor == "Supermicro":
            self.logger.error("Operation not supported by vendor.")
            return False

        try:
            raw = await resp.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            attributes_list = [(key, value) for key, value in data.get("Attributes").items()]
            if not log:
                return attributes_list
            self.logger.debug(f"All NIC attributes of {fqdd}.")
            self.logger.info(f"{fqdd}")
            for key, value in attributes_list:
                self.logger.info(f"    {key}: {value}")
        except (AttributeError, KeyError, TypeError, ValueError):
            self.logger.error("Was unable to get NIC attribute(s) info, invalid server response.")
            return False
        return True

    async def get_idrac_fw_version(self):
        idrac_fw_version = 0
        try:
            uri = "%s%s/" % (self.host_uri, self.manager_resource)
            resp = await self.get_request(uri)
            if resp.status == 404 or self.vendor == "Supermicro":
                self.logger.error("Operation not supported by vendor.")
                return 0
            raw = await resp.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            idrac_fw_version = int(data["FirmwareVersion"].replace(".", ""))
        except (AttributeError, ValueError, StopIteration):
            self.logger.error("Was unable to get iDRAC Firmware Version.")
            return 0
        return idrac_fw_version

    async def get_nic_attribute_registry(self, fqdd=None):
        registry = []
        idrac_fw_version = await self.get_idrac_fw_version()
        if not idrac_fw_version or idrac_fw_version < 5100000:
            self.logger.error("Unsupported iDRAC version.")
            return []
        try:
            uri = "%s/Registries/NetworkAttributesRegistry_%s/NetworkAttributesRegistry_%s.json" % (
                self.root_uri,
                fqdd,
                fqdd,
            )
            resp = await self.get_request(uri)
            if resp.status == 404:
                self.logger.error("Was unable to get network attribute registry.")
                return []
            raw = await resp.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            registry = [attr for attr in data.get("RegistryEntries").get("Attributes")]
        except (AttributeError, KeyError, TypeError, ValueError):
            self.logger.error("Was unable to get network attribute registry.")
            return []
        return registry

    async def get_nic_attribute_info(self, fqdd, attribute, log=True):
        if self.vendor == "Supermicro":
            self.logger.error("Operation not supported by vendor.")
            return False
        registry = await self.get_nic_attribute_registry(fqdd)
        if not registry:
            self.logger.error("Was unable to get network attribute info.")
            return False
        try:
            registry = [attr_dict for attr_dict in registry if attr_dict.get("AttributeName") == attribute][0]
            current_value = await self.get_nic_attribute(fqdd, False)
            current_value = [tup[1] for tup in current_value if tup[0] == attribute][0]
            registry.update({"CurrentValue": current_value})
            if not log:
                return registry
            for key, value in registry.items():
                self.logger.info(f"{key}: {value}")
        except (AttributeError, IndexError, KeyError, TypeError):
            self.logger.error("Was unable to get network attribute info.")
            return False
        return True

    async def set_nic_attribute(self, fqdd, attribute, value):
        if self.vendor == "Supermicro":
            self.logger.error("Operation not supported by vendor.")
            return False

        attr_info = await self.get_nic_attribute_info(fqdd, attribute, False)
        if not attr_info:
            self.logger.error("Was unable to set a network attribute. Attribute most likely doesn't exist.")
            return False

        try:
            type = attr_info.get("Type")
            current_value = attr_info.get("CurrentValue")
            if value == current_value:
                self.logger.warning("This attribute already is set to this value. Skipping.")
                return True
            if type == "Enumeration":
                allowed_values = [value_spec.get("ValueName") for value_spec in attr_info.get("Value")]
                if value not in allowed_values:
                    self.logger.error("Value not allowed for this attribute.")
                    self.logger.error("Was unable to set a network attribute.")
                    return False
            if type == "String":
                max, min = int(attr_info.get("MaxLength")), int(attr_info.get("MinLength"))
                if len(value) > max or len(value) < min:
                    self.logger.error("Value not allowed for this attribute. (Incorrect string length)")
                    self.logger.error("Was unable to set a network attribute.")
                    return False
            if type == "Integer":
                max, min = int(attr_info.get("UpperBound")), int(attr_info.get("LowerBound"))
                value = int(value)
                if value > max or value < min:
                    self.logger.error("Value not allowed for this attribute. (Incorrect number bounds)")
                    self.logger.error("Was unable to set a network attribute.")
                    return False
        except (AttributeError, IndexError, KeyError, TypeError):
            self.logger.error("Was unable to set a network attribute.")
            return False

        try:
            uri = (
                "%s/Chassis/System.Embedded.1/NetworkAdapters/%s/NetworkDeviceFunctions/%s/Oem/Dell/DellNetworkAttributes/%s/Settings"
                % (
                    self.root_uri,
                    fqdd.split("-")[0],
                    fqdd,
                    fqdd,
                )
            )
            self.logger.debug(uri)
        except (IndexError, ValueError):
            self.logger.error("Invalid FQDD suplied.")
            return False

        headers = {"content-type": "application/json"}
        payload = {
            "@Redfish.SettingsApplyTime": {"ApplyTime": "OnReset"},
            "Attributes": {attribute: value},
        }
        first_reset = False
        try:
            for i in range(self.retries):
                response = await self.patch_request(uri, payload, headers)
                status_code = response.status
                if status_code in [200, 202]:
                    self.logger.info("Patch command to set network attribute values and create next reboot job PASSED.")
                    break
                else:
                    self.logger.error(
                        "Patch command to set network attribute values and create next reboot job FAILED, error code is: %s."
                        % status_code
                    )
                    if status_code == 503 and i - 1 != self.retries:
                        self.logger.info("Retrying to send the patch command.")
                        continue
                    elif status_code == 400:
                        self.logger.info("Retrying to send the patch command.")
                        await self.clear_job_queue()
                        if not first_reset:
                            await self.reset_idrac()
                            await asyncio.sleep(10)
                            first_reset = True
                        continue
                    self.logger.error(
                        "Patch command to set network attribute values and create next reboot job FAILED, error code is: %s."
                        % status_code
                    )
                    self.logger.error("Was unable to set a network attribute.")
                    return False
        except (AttributeError, ValueError):
            self.logger.error("Was unable to set a network attribute.")

        await self.reboot_server()


async def execute_badfish(_host, _args, logger, format_handler=None):
    _username = _args["u"]
    _password = _args["p"]
    host_type = _args["t"]
    interfaces_path = _args["i"]
    force = _args["force"]
    pxe = _args["pxe"]
    device = _args["boot_to"]
    boot_to_type = _args["boot_to_type"]
    boot_to_mac = _args["boot_to_mac"]
    reboot_only = _args["reboot_only"]
    power_state = _args["power_state"]
    power_on = _args["power_on"]
    power_off = _args["power_off"]
    power_cycle = _args["power_cycle"]
    power_consumed_watts = _args["get_power_consumed"]
    rac_reset = _args["racreset"]
    bmc_reset = _args["bmc_reset"]
    factory_reset = _args["factory_reset"]
    check_boot = _args["check_boot"]
    toggle_boot_device = _args["toggle_boot_device"]
    firmware_inventory = _args["firmware_inventory"]
    clear_jobs = _args["clear_jobs"]
    check_job = _args["check_job"]
    list_jobs = _args["ls_jobs"]
    list_interfaces = _args["ls_interfaces"]
    list_gpu = _args["ls_gpu"]
    list_processors = _args["ls_processors"]
    list_memory = _args["ls_memory"]
    list_serial = _args["ls_serial"]
    check_virtual_media = _args["check_virtual_media"]
    unmount_virtual_media = _args["unmount_virtual_media"]
    mount_virtual_media = _args["mount_virtual_media"]
    boot_to_virtual_media = _args["boot_to_virtual_media"]
    check_remote_image = _args["check_remote_image"]
    boot_remote_image = _args["boot_remote_image"]
    detach_remote_image = _args["detach_remote_image"]
    get_sriov = _args["get_sriov"]
    enable_sriov = _args["enable_sriov"]
    disable_sriov = _args["disable_sriov"]
    set_bios_attribute = _args["set_bios_attribute"]
    get_bios_attribute = _args["get_bios_attribute"]
    attribute = _args["attribute"]
    value = _args["value"]
    set_bios_password = _args["set_bios_password"]
    remove_bios_password = _args["remove_bios_password"]
    new_password = _args["new_password"]
    old_password = _args["old_password"]
    screenshot = _args["screenshot"]
    retries = int(_args["retries"])
    output = _args["output"]
    get_scp_targets = _args["get_scp_targets"]
    scp_targets = _args["scp_targets"]
    scp_include_read_only = _args["scp_include_read_only"]
    export_scp = _args["export_scp"]
    import_scp = _args["import_scp"]
    get_nic_fqdds = _args["get_nic_fqdds"]
    get_nic_attribute = _args["get_nic_attribute"]
    set_nic_attribute = _args["set_nic_attribute"]
=======
async def execute_badfish(_host: str, _args: Dict[str, Any], logger, format_handler=None) -> tuple[str, bool]:
    """Execute Badfish operations on a single host."""
    config = BadfishConfig(_args)
>>>>>>> Stashed changes
    result = True
    badfish = None

    try:
        badfish = await badfish_factory(
            _host=_host,
            _username=config.username,
            _password=config.password,
            _logger=logger,
            _retries=config.retries,
        )

        if config.host_list and not config.output:
            logger.info("Executing actions on host: %s" % _host)

        # Use command pattern to execute operations
        executor = BadfishCommandExecutor(config)
        command_executed = await executor.execute(badfish)
        
        if not command_executed:
            # No command was executed, this might be an error or no-op
            logger.warning("No operation specified or no matching command found")

<<<<<<< Updated upstream
        if pxe and not host_type:
            await badfish.set_next_boot_pxe()

=======
>>>>>>> Stashed changes
    except BadfishException as ex:
        logger.error(ex)
        result = False
    finally:
        if badfish and badfish.session_id:
            try:
                await badfish.delete_session()
                logger.debug(f"Session closed for host: {_host}")
            except BadfishException as ex:
                logger.warning(f"Failed to close session for {_host}: {ex}")

    if config.host_list:
        logger.info("*" * 48)
        if config.output and result:
            format_handler.host = _host
            format_handler.parse()
    else:
        if config.output and result:
            format_handler.parse()

    return _host, result


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="badfish",
        description="Tool for managing server hardware via the Redfish API.",
        allow_abbrev=False,
    )
    
    # Core arguments
    parser.add_argument("-H", "--host", help="iDRAC host address")
    parser.add_argument("-u", help="iDRAC username", required=True)
    parser.add_argument("-p", help="iDRAC password", required=True)
    parser.add_argument("-i", help="Path to iDRAC interfaces yaml", default=None)
    parser.add_argument("-t", help="Type of host as defined on iDRAC interfaces yaml")
    parser.add_argument("-l", "--log", help="Optional argument for logging results to a file")
    parser.add_argument(
        "-o", "--output", choices=["json", "yaml"],
        help="Optional argument for choosing a special output format (json/yaml), otherwise our normal format is used.",
    )
    parser.add_argument(
        "-f", "--force", dest="force", action="store_true",
        help="Optional argument for forced clear-jobs",
    )
    parser.add_argument(
        "--host-list", help="Path to a plain text file with a list of hosts", default=None,
    )
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    parser.add_argument(
        "-r", "--retries", help="Number of retries for executing actions.", default=RETRIES,
    )
    
    # Boot operations
    parser.add_argument("--pxe", help="Set next boot to one-shot boot PXE", action="store_true")
    parser.add_argument("--boot-to", help="Set next boot to one-shot boot to a specific device")
    parser.add_argument(
        "--boot-to-type", help="Set next boot to one-shot boot to a specific type as defined on iDRAC interfaces yaml",
    )
    parser.add_argument(
        "--boot-to-mac", help="Set next boot to one-shot boot to a specific MAC address on the target",
    )
    parser.add_argument("--check-boot", help="Flag for checking the host boot order", action="store_true")
    parser.add_argument(
        "--toggle-boot-device", help="Change the enabled status of a boot device", default="",
    )
    
    # Power operations
    parser.add_argument("--reboot-only", help="Flag for only rebooting the host", action="store_true")
    parser.add_argument("--power-cycle", help="Flag for sending ForceOff instruction to the host", action="store_true")
    parser.add_argument("--power-state", help="Get power state", action="store_true")
    parser.add_argument("--power-on", help="Power on host", action="store_true")
    parser.add_argument("--power-off", help="Power off host", action="store_true")
    parser.add_argument("--get-power-consumed", help="Get current consumed watts on host(s)", action="store_true")
    
    # Reset operations
    parser.add_argument("--racreset", help="Flag for iDRAC reset", action="store_true")
    parser.add_argument("--bmc-reset", help="Flag for BMC reset", action="store_true")
    parser.add_argument("--factory-reset", help="Reset BIOS to default factory settings", action="store_true")
    
    # Job operations
    parser.add_argument("--clear-jobs", help="Clear any scheduled jobs from the queue", action="store_true")
    parser.add_argument("--check-job", help="Check a job status and details")
    parser.add_argument("--ls-jobs", help="List any scheduled jobs in queue", action="store_true")
    
    # Inventory operations
    parser.add_argument("--firmware-inventory", help="Get firmware inventory", action="store_true")
    parser.add_argument("--ls-interfaces", help="List Network interfaces", action="store_true")
    parser.add_argument("--ls-processors", help="List Processor Summary", action="store_true")
    parser.add_argument("--ls-gpu", help="List GPU's on host", action="store_true")
    parser.add_argument("--ls-memory", help="List Memory Summary", action="store_true")
    parser.add_argument("--ls-serial", help="List 'Serial Number'/'Service Tag'", action="store_true")
    
    # Virtual media operations
    parser.add_argument("--check-virtual-media", help="Check for mounted iso images", action="store_true")
    parser.add_argument(
        "--mount-virtual-media", help="Mount iso image to virtual CD. Arguments should be the address/path to the iso.",
        default="",
    )
    parser.add_argument("--unmount-virtual-media", help="Unmount any mounted iso images", action="store_true")
    parser.add_argument("--boot-to-virtual-media", help="Boot to virtual media (Cd).", action="store_true")
    
    # Remote image operations
    parser.add_argument("--check-remote-image", help="Check the attach status of network ISO.", action="store_true")
    parser.add_argument(
        "--boot-remote-image", help="Boot to network ISO, through NFS, takes two arguments 'hostname:path' and name of the ISO 'linux.iso'.",
        default="",
    )
    parser.add_argument("--detach-remote-image", help="Remove attached network ISO.", action="store_true")
    
    # SRIOV operations
    parser.add_argument("--get-sriov", help="Gets global SRIOV mode state", action="store_true")
    parser.add_argument("--enable-sriov", help="Enables global SRIOV mode", action="store_true")
    parser.add_argument("--disable-sriov", help="Disables global SRIOV mode", action="store_true")
    
    # BIOS operations
    parser.add_argument("--get-bios-attribute", help="Get a BIOS attribute value", action="store_true")
    parser.add_argument("--set-bios-attribute", help="Set a BIOS attribute value", action="store_true")
    parser.add_argument("--attribute", help="BIOS attribute name", default="")
    parser.add_argument("--value", help="BIOS attribute value", default="")
    parser.add_argument("--set-bios-password", help="Set the BIOS password", action="store_true")
    parser.add_argument("--remove-bios-password", help="Removes BIOS password", action="store_true")
    parser.add_argument("--new-password", help="The new password value", default="")
    parser.add_argument("--old-password", help="The old password value", default="")
    
    # Screenshot
    parser.add_argument("--screenshot", help="Take a screenshot of the system an store it in jpg format", action="store_true")
    
    # SCP operations
    parser.add_argument(
        "--get-scp-targets", help="Get allowable target values to export or import with iDRAC SCP. Choices=['Export', 'Import']",
        choices=["Export", "Import"], default="",
    )
    parser.add_argument(
        "--scp-targets", help="Comma separated targets which configs should be exported with iDRAC SCP.", default="ALL",
    )
    parser.add_argument("--scp-include-read-only", help="Flag for including read only attributes in SCP export.", action="store_true")
    parser.add_argument(
        "--export-scp", help="Export system config using iDRAC SCP, argument specifies where file should be saved.", default="",
    )
    parser.add_argument(
        "--import-scp", help="Import system config using iDRAC SCP, argument specifies which JSON file contains config that should be imported.",
        default="",
    )
    
    # NIC operations
    parser.add_argument("--get-nic-fqdds", help="List FQDDs for all NICs.", action="store_true")
    parser.add_argument("--get-nic-attribute", help="Get a NIC attribute values, specify a NIC FQDD.", default="")
    parser.add_argument("--set-nic-attribute", help="Set a NIC attribute value", default="")
    
    # Host identification
    parser.add_argument("--rack", help="Rack identifier", default="")
    parser.add_argument("--uloc", help="U-location identifier", default="")
    parser.add_argument("--blade", help="Blade identifier", default="")
    
    # Delta comparison
    parser.add_argument("--delta", help="Address of the other host between which the delta should be made", default="")
    
    return parser


def process_delta_argument(_args: Dict[str, Any]) -> None:
    """Process delta argument for firmware inventory comparison."""
    delta = _args["delta"]
    if _args["firmware_inventory"] and delta:
        tp = tempfile.NamedTemporaryFile()
        tp.write(f"{_args['host']}\n{delta}".encode())
        tp.flush()
        _args["host_list"] = tp.name
        if not _args["output"]:
            _args["output"] = "json"


def setup_logging(_args: Dict[str, Any]) -> tuple[BadfishLogger, int]:
    """Setup logging configuration."""
    log_level = DEBUG if _args["verbose"] else INFO
    host_list = _args["host_list"]
    multi_host = bool(host_list)
    output = _args["output"]
    bfl = BadfishLogger(_args["verbose"], multi_host, _args["log"], output)
    return bfl, log_level


def process_host_list(host_list: str, _args: Dict[str, Any], bfl: BadfishLogger, log_level: int) -> tuple[list, dict]:
    """Process host list file and create tasks."""
    tasks = []
    host_order = {}
    
    try:
        with open(host_list, "r") as _file:
            for i, _host in enumerate(_file.readlines()):
                if _host.isspace():
                    continue

                host_name = _host.strip().split(".")[0]
                host_order.update({host_name: i})
                logger = getLogger(host_name)
                logger.addHandler(bfl.queue_handler)
                logger.setLevel(log_level)
                bfl.badfish_handler.host = _host if _args["output"] else None
                fn = functools.partial(
                    execute_badfish,
                    _host.strip(),
                    _args,
                    logger,
                    bfl.queue_listener.handlers[0] if _args["output"] else None,
                )
                tasks.append(fn)
    except IOError as ex:
        bfl.logger.debug(ex)
        bfl.logger.error("There was something wrong reading from %s" % host_list)
    
    return tasks, host_order


def run_tasks(tasks: list, bfl: BadfishLogger) -> tuple[list, bool]:
    """Run async tasks and handle exceptions."""
    results = []
    result = True
    
    try:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(asyncio.gather(*[task() for task in tasks], return_exceptions=True))
    except KeyboardInterrupt:
        bfl.logger.warning("Badfish terminated")
        result = False
    except (asyncio.CancelledError, BadfishException) as ex:
        bfl.logger.warning("There was something wrong executing Badfish")
        bfl.logger.debug(ex)
        result = False
    
    return results, result


def display_results(results: list, bfl: BadfishLogger, output: Optional[str]) -> bool:
    """Display results for multi-host operations."""
    if results and not output:
        result = True
        bfl.logger.info("RESULTS:")
        for res in results:
            if len(res) > 1 and res[1]:
                bfl.logger.info(f"{res[0]}: SUCCESSFUL")
            else:
                bfl.logger.info(f"{res[0]}: FAILED")
                result = False
        return result
    return True


def main(argv=None) -> int:
    """Main entry point for Badfish CLI."""
    parser = create_argument_parser()
    _args = vars(parser.parse_args(argv))
    
    # Process delta argument
    process_delta_argument(_args)
    
    # Setup logging
    bfl, log_level = setup_logging(_args)
    
    host = _args["host"]
    host_list = _args["host_list"]
    output = _args["output"]
    result = True
    
    try:
        if host_list:
            # Multi-host operation
            tasks, host_order = process_host_list(host_list, _args, bfl, log_level)
            results, result = run_tasks(tasks, bfl)
            result = display_results(results, bfl, output)
            
        elif not host:
            bfl.logger.error("You must specify at least either a host (-H) or a host list (--host-list).")
            return 1
            
        else:
            # Single host operation
            try:
                loop = asyncio.get_event_loop()
                _host, result = loop.run_until_complete(
                    execute_badfish(host, _args, bfl.logger, bfl.queue_listener.handlers[0])
                )
            except KeyboardInterrupt:
                bfl.logger.warning("Badfish terminated")
                return 1
            except BadfishException as ex:
                bfl.logger.warning("There was something wrong executing Badfish")
                bfl.logger.debug(ex)
                return 1
                
    finally:
        bfl.queue_listener.stop()
    
    # Handle output
    if _args["delta"]:
        bfh_output = bfl.badfish_handler.diff()
    else:
        bfh_output = bfl.badfish_handler.output(output if output else "normal", host_order if host_list else {})
    
    if _args["log"]:
        with open(_args["log"], "w") as f:
            print(bfh_output, file=f)
    elif bfh_output:
        print(bfh_output, file=sys.stderr)

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
