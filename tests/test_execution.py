import os
from unittest.mock import patch

from src.badfish.main import BadfishException
from tests.config import (HOST_LIST_EXTRAS, KEYBOARD_INTERRUPT,
                          KEYBOARD_INTERRUPT_HOST_LIST, MAN_RESP,
                          NO_HOST_ERROR, RESPONSE_INIT_CREDENTIALS_FAILED_COMS,
                          RESPONSE_INIT_CREDENTIALS_UNAUTHORIZED,
                          RESPONSE_INIT_SYSTEMS_RESOURCE_NOT_FOUND,
                          RESPONSE_INIT_SYSTEMS_RESOURCE_UNAUTHORIZED,
                          ROOT_RESP, SUCCESSFUL_HOST_LIST, SYS_RESP,
                          WRONG_BADFISH_EXECUTION,
                          WRONG_BADFISH_EXECUTION_HOST_LIST)
from tests.test_base import TestBase


def raise_keyb_interrupt_stub(ignore1, ignore2, ignore3, ignore4=None):
    raise KeyboardInterrupt


def raise_badfish_exception_stub(ignore1, ignore2, ignore3, ignore4=None):
    raise BadfishException


class TestSingleHostExecution(TestBase):
    args = ["--ls-jobs"]

    @patch("src.badfish.main.execute_badfish", raise_keyb_interrupt_stub)
    def test_single_host_keyb_interrupt(self):
        _, err = self.badfish_call()
        assert err == KEYBOARD_INTERRUPT

    @patch("src.badfish.main.execute_badfish", raise_badfish_exception_stub)
    def test_single_host_badfish_exception(self):
        _, err = self.badfish_call()
        assert err == WRONG_BADFISH_EXECUTION

    def test_no_host_error(self):
        _, err = self.badfish_call(mock_host=None)
        assert err == NO_HOST_ERROR


class TestHostListExecution(TestBase):
    args = [
        "--host-list",
        f"{os.path.dirname(__file__)}/fixtures/hosts_good.txt",
        "--ls-jobs",
    ]

    @patch("src.badfish.main.execute_badfish", raise_keyb_interrupt_stub)
    def test_host_list_keyb_interrupt(self):
        _, err = self.badfish_call(mock_host=None)
        assert err == KEYBOARD_INTERRUPT_HOST_LIST

    @patch("src.badfish.main.execute_badfish", raise_badfish_exception_stub)
    def test_host_list_badfish_exception(self):
        _, err = self.badfish_call(mock_host=None)
        assert err == WRONG_BADFISH_EXECUTION_HOST_LIST

    @patch("src.badfish.main.execute_badfish")
    def test_host_list_successful(self, mock_execute):
        mock_execute.return_value = "Successful."
        _, err = self.badfish_call(mock_host=None)
        assert err == SUCCESSFUL_HOST_LIST

    @patch("aiohttp.ClientSession.delete")
    @patch("aiohttp.ClientSession.post")
    @patch("aiohttp.ClientSession.get")
    def test_host_list_extras(self, mock_get, mock_post, mock_delete):
        self.set_mock_response(mock_get, 200, ROOT_RESP)
        self.set_mock_response(mock_post, 200, "OK")
        self.set_mock_response(mock_delete, 200, "OK")
        _, err = self.badfish_call(mock_host=None)
        assert err == HOST_LIST_EXTRAS


class TestInitialization(TestBase):
    args = ["--ls-jobs"]

    @patch("aiohttp.ClientSession.delete")
    @patch("aiohttp.ClientSession.post")
    @patch("aiohttp.ClientSession.get")
    def test_validate_credentials_unauthorized(self, mock_get, mock_post, mock_delete):
        self.set_mock_response(mock_get, 200, ROOT_RESP)
        self.set_mock_response(mock_post, 401, "Unauthorized")
        self.set_mock_response(mock_delete, 200, "OK")
        _, err = self.badfish_call()
        assert err == RESPONSE_INIT_CREDENTIALS_UNAUTHORIZED

    @patch("aiohttp.ClientSession.delete")
    @patch("aiohttp.ClientSession.post")
    @patch("aiohttp.ClientSession.get")
    def test_validate_credentials_failed_coms(self, mock_get, mock_post, mock_delete):
        self.set_mock_response(mock_get, 200, [ROOT_RESP])
        self.set_mock_response(mock_post, 400, "Bad Request")
        self.set_mock_response(mock_delete, 200, "OK")
        _, err = self.badfish_call()
        assert err == RESPONSE_INIT_CREDENTIALS_FAILED_COMS

    @patch("aiohttp.ClientSession.delete")
    @patch("aiohttp.ClientSession.post")
    @patch("aiohttp.ClientSession.get")
    def test_find_systems_resource_unauthorized(self, mock_get, mock_post, mock_delete):
        responses = [ROOT_RESP, ROOT_RESP, SYS_RESP, ROOT_RESP, MAN_RESP]
        self.set_mock_response(mock_get, [200, 200, 401, 200, 200], responses)
        self.set_mock_response(mock_post, 200, "OK")
        self.set_mock_response(mock_delete, 200, "OK")
        _, err = self.badfish_call()
        assert err == RESPONSE_INIT_SYSTEMS_RESOURCE_UNAUTHORIZED

    @patch("aiohttp.ClientSession.delete")
    @patch("aiohttp.ClientSession.post")
    @patch("aiohttp.ClientSession.get")
    def test_find_systems_resource_not_found(self, mock_get, mock_post, mock_delete):
        responses = [ROOT_RESP, "{}", MAN_RESP]
        self.set_mock_response(mock_get, 200, responses)
        self.set_mock_response(mock_post, 200, "OK")
        self.set_mock_response(mock_delete, 200, "OK")
        _, err = self.badfish_call()
        assert err == RESPONSE_INIT_SYSTEMS_RESOURCE_NOT_FOUND
