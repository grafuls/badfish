import yaml
from badfish.core.exceptions import BadfishException


async def read_yaml(_yaml_file, logger):
    """Read and parse a YAML file."""
    with open(_yaml_file, "r") as f:
        try:
            definitions = yaml.safe_load(f)
        except yaml.YAMLError as ex:
            logger.debug(ex)
            raise BadfishException("Couldn't read file: %s" % _yaml_file)
    return definitions


async def get_host_types_from_yaml(_interfaces_path, logger):
    """Extract host types from a YAML interfaces file."""
    definitions = await read_yaml(_interfaces_path, logger)
    host_types = set()
    for line in definitions:
        _split = line.split("_")
        host_types.add(_split[0])

    ordered_types = sorted(list(host_types))
    return ordered_types


async def get_interfaces_by_type(host_type, _interfaces_path, host, logger):
    """Get interfaces for a specific host type from YAML configuration."""
    definitions = await read_yaml(_interfaces_path, logger)

    host_name_split = host.split(".")[0].split("-")
    host_model = host_name_split[-1]
    rack = host_name_split[1]
    uloc = host_name_split[2]

    host_blade = "000"
    if len(host_name_split) > 4:
        host_blade = host_name_split[3]

    prefix = [host_type, rack, uloc, host_blade]

    key = f"{host_type}_{host_blade}_{host_model}_interfaces"
    interfaces_string = definitions.get(key)
    if interfaces_string:
        return interfaces_string.split(",")

    len_prefix = len(prefix)
    key = "None"
    for _ in range(len_prefix):
        prefix_string = "_".join(prefix)
        key = "%s_%s_interfaces" % (prefix_string, host_model)
        interfaces_string = definitions.get(key)
        if interfaces_string:
            return interfaces_string.split(",")
        else:
            prefix.pop()

    raise BadfishException(f"Couldn't find a valid key defined on the interfaces yaml: {key}") 