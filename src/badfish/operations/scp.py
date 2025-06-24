import asyncio
import json
from badfish.core.exceptions import BadfishException
from badfish.helpers import get_now


class ScpOperations:
    """SCP management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
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

        