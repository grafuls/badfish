import asyncio
import json
import re

from badfish.core.exceptions import BadfishException


class JobsOperations:
    """Job management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
    async def get_job_queue(self):
        self.logger.debug("Getting job queue.")
        _url = "%s%s/Jobs" % (self.host_uri, self.manager_resource)
        _response = await self.get_request(_url)

        data = await _response.text("utf-8", "ignore")
        job_queue = re.findall(r"[JR]ID_.+?\d+", data)
        jobs = [job.strip("}").strip('"').strip("'") for job in job_queue]
        return jobs

    async def delete_job_queue_dell(self, force):
        _url = "%s/Dell/Managers/iDRAC.Embedded.1/DellJobService/Actions/DellJobService.DeleteJobQueue" % self.root_uri
        job_id = "JID_CLEARALL"
        if force:
            job_id = f"{job_id}_FORCE"
        _payload = {"JobID": job_id}
        _headers = {"content-type": "application/json"}
        response = await self.post_request(_url, _payload, _headers)
        if response.status == 200:
            self.logger.info("Job queue for iDRAC %s successfully cleared." % self.host)
        else:
            await self.error_handler(
                response,
                message="Job queue not cleared, there was something wrong with your request.",
            )

    async def delete_job_queue_force(self):
        _url = "%s%s/Jobs" % (self.host_uri, self.manager_resource)
        _headers = {"content-type": "application/json"}
        url = "%s/JID_CLEARALL_FORCE" % _url
        try:
            _response = await self.delete_request(url, _headers)
            if _response.status in [200, 204]:
                self.logger.info("Job queue for iDRAC %s successfully cleared." % self.host)
        except BadfishException as ex:
            self.logger.debug(ex)
            raise BadfishException("There was something wrong clearing the job queue.")
        return _response

    async def clear_job_list(self, _job_queue):
        _url = "%s%s/Jobs" % (self.host_uri, self.manager_resource)
        _headers = {"content-type": "application/json"}
        self.logger.warning("Clearing job queue for job IDs: %s." % _job_queue)
        for _job in _job_queue:
            job = _job.strip("'")
            url = "/".join([_url, job])
            response = await self.delete_request(url, _headers)
            if response.status != 200:
                raise BadfishException("Job queue not cleared, there was something wrong with your request.")

        self.logger.info("Job queue for iDRAC %s successfully cleared." % self.host)
        return True

    async def clear_job_queue(self, force=False):
        _job_queue = await self.get_job_queue()
        if _job_queue or force:
            supported = await self.check_supported_idrac_version()
            if supported:
                await self.delete_job_queue_dell(force)
            else:
                try:
                    _response = await self.delete_job_queue_force()
                    if _response.status == 400:
                        await self.clear_job_list(_job_queue)
                except BadfishException:
                    self.logger.info("Attempting to clear job list instead.")
                    await self.clear_job_list(_job_queue)
        else:
            self.logger.warning("Job queue already cleared for iDRAC %s, DELETE command will not execute." % self.host)

    async def list_job_queue(self):
        _job_queue = await self.get_job_queue()
        if _job_queue:
            self.logger.info("Found active jobs:")
            for job in _job_queue:
                self.logger.info("    JobID: " + job)
        else:
            self.logger.info("Found active jobs: None")

    async def create_job(self, _url, _payload, _headers, expected=None):
        if not expected:
            expected = [200, 204]
        _response = await self.post_request(_url, _payload, _headers)

        status_code = _response.status
        if status_code in expected:
            self.logger.debug("POST command passed to create target config job.")
        else:
            self.logger.error("POST command failed to create BIOS config job, status code is %s." % status_code)

            await self.error_handler(_response)

        raw = await _response.text("utf-8", "ignore")
        result = re.search("JID_.+?", raw)
        res_group = ""
        if result:
            res_group = result.group()
        job_id = re.sub("[,']", "", res_group)
        if job_id:
            self.logger.debug("%s job ID successfully created" % job_id)
        return job_id

    async def create_bios_config_job(self, uri):
        _url = "%s%s/Jobs" % (self.host_uri, self.manager_resource)
        _payload = {"TargetSettingsURI": "%s%s" % (self.redfish_uri, uri)}
        _headers = {"content-type": "application/json"}
        return await self.create_job(_url, _payload, _headers)

    async def check_schedule_job_status(self, job_id):
        _url = f"{self.host_uri}{self.manager_resource}/Jobs/{job_id}"
        _response = await self.get_request(_url)

        if _response:
            status_code = _response.status
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())

            if status_code == 200:
                await asyncio.sleep(10)
            else:
                self.logger.error(f"Command failed to check job status, return code is {status_code}")
                self.logger.debug(f"Extended Info Message: {data}")
                return False

            self.logger.info(f"JobID: {data[u'Id']}")
            self.logger.info(f"Name: {data[u'Name']}")
            self.logger.info(f"Message: {data[u'Message']}")
            self.logger.info(f"PercentComplete: {str(data[u'PercentComplete'])}")
        else:
            self.logger.error("Command failed to check job status")
            return False

    async def check_job_status(self, job_id):
        for count in range(self.retries):
            _url = f"{self.host_uri}{self.manager_resource}/Jobs/{job_id}"
            self.get_request.cache_clear()
            _response = await self.get_request(_url)

            status_code = _response.status
            raw = await _response.text("utf-8", "ignore")
            data = json.loads(raw.strip())
            if status_code == 200:
                pass
            else:
                self.logger.error(f"Command failed to check job status, return code is {status_code}")
                self.logger.debug(f"Extended Info Message: {data}")
                return False
            if "Fail" in data["Message"] or "fail" in data["Message"]:
                self.logger.debug(f"\n{job_id} job failed.")
                return False
            elif data["Message"] == "Job completed successfully.":
                self.logger.info(f"JobID: {data[u'Id']}")
                self.logger.info(f"Name: {data[u'Name']}")
                self.logger.info(f"Message: {data[u'Message']}")
                self.logger.info(f"PercentComplete: {str(data[u'PercentComplete'])}")
                break
            else:
                self.progress_bar(count, self.retries, data["Message"], prompt="Status")
                await asyncio.sleep(30)
