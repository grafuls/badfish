import pytest

from tests import config
from tests.test_aiohttp_base import TestBase


class TestBootTo(TestBase):
    option_arg = "--boot-to"

    @pytest.mark.skip(reason="Needs to be transformed to async")
    def test_boot_to(self):
        self.boot_seq = config.BOOT_SEQ_RESPONSE_DIRECTOR
        self.args = [self.option_arg, config.DEVICE_NIC_2['name']]
        _, err = self.badfish_call()
        assert config.RESPONSE_BOOT_TO == err

    @pytest.mark.skip(reason="Needs to be transformed to async")
    def test_boot_to_no_match(self):
        self.expect_fail = True
        self.boot_seq = config.BOOT_SEQ_RESPONSE_DIRECTOR
        self.args = [self.option_arg, config.BAD_DEVICE_NAME]
        with pytest.raises(SystemExit):
            _, err = self.badfish_call()
            assert config.ERROR_DEV_NO_MATCH == err
