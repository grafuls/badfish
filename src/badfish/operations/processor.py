import json
from badfish.core.exceptions import BadfishException


class ProcessorOperations:
    """Processor management operations for Redfish API."""
    
    def __init__(self, http_client, host_uri, system_resource, logger, retries):
        self.http_client = http_client
        self.host_uri = host_uri
        self.system_resource = system_resource
        self.logger = logger
        self.retries = retries
        
        
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
