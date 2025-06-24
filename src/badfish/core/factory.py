from badfish.helpers.logger import BadfishLogger
from .badfish import Badfish

RETRIES = 15


async def badfish_factory(_host, _username, _password, _logger=None, _retries=RETRIES, _loop=None):
    """Factory function to create and initialize a Badfish instance."""
    if not _logger:
        bfl = BadfishLogger()
        _logger = bfl.logger

    badfish = Badfish(_host, _username, _password, _logger, _retries, _loop)
    await badfish.init()
    return badfish 