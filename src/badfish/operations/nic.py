import asyncio
import json

from badfish.core.exceptions import BadfishException


class NicOperations:
    """NIC management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
        
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

    async def get_interfaces_endpoints(self):
        _uri = "%s%s/EthernetInterfaces" % (self.host_uri, self.system_resource)
        _response = await self.get_request(_uri)

        raw = await _response.text("utf-8", "ignore")
        data = json.loads(raw.strip())

        if _response.status == 404:
            self.logger.debug(raw)
            raise BadfishException("EthernetInterfaces entry point not supported by this host.")

        endpoints = []
        if data.get("Members"):
            for member in data["Members"]:
                endpoints.append(member["@odata.id"])
        else:
            raise BadfishException("EthernetInterfaces's Members array is either empty or missing")

        return endpoints

    async def get_interface(self, endpoint):
        _uri = "%s%s" % (self.host_uri, endpoint)
        _response = await self.get_request(_uri)

        raw = await _response.text("utf-8", "ignore")

        if _response.status == 404:
            self.logger.debug(raw)
            raise BadfishException("EthernetInterface entry point not supported by this host.")

        data = json.loads(raw.strip())

        return data

    async def check_supported_network_interfaces(self, endpoint):
        _url = "%s%s/%s" % (self.host_uri, self.system_resource, endpoint)
        _response = await self.get_request(_url)
        if _response.status != 200:
            return False

        return True

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
