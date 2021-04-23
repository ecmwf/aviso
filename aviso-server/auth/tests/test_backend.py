import json
import os

import pytest
from aviso_auth import config, logger
from aviso_auth.authorisation import Authoriser
from aviso_auth.backend_adapter import BackendAdapter
from aviso_auth.custom_exceptions import InternalSystemError, InvalidInputError


def conf() -> config.Config:  # this automatically configure the logging
    return config.Config(conf_path=os.path.expanduser("~/.aviso-auth/testing/config.yaml"))


class RequestDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


def test_backend():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # prepare request
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": None,
        "max_mod_revision": None,
    }
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    resp = backend.forward_impl(request)
    assert resp


def test_not_existing_dest():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL/not_existing"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": None,
        "max_mod_revision": None,
    }
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    resp = backend.forward_impl(request)
    assert resp
    assert json.loads(resp.decode()) != {}
    assert json.loads(resp.decode()).get("kvs") is None


def test_bad_etcd_format_request():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": "aa",  # this returns a 400 as it's expecting a number
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": None,
        "max_mod_revision": None,
    }
    # make the call
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    try:
        backend.forward_impl(request)
    except Exception as e:
        assert isinstance(e, InternalSystemError)


def test_bad_etcd_request_value():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEYY",  # this returns a 400 as it's an unknown value
        "keys_only": False,
        "revision": None,
        "min_mod_revision": None,
        "max_mod_revision": None,
    }
    # make the call
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    try:
        backend.forward_impl(request)
    except Exception as e:
        assert isinstance(e, InternalSystemError)


def test_future_rev():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": 10000000000,  # this returns a 400 as it's a future revision
        "min_mod_revision": None,
        "max_mod_revision": None,
    }
    # make the call
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    try:
        backend.forward_impl(request)
    except Exception as e:
        assert isinstance(e, InternalSystemError)


@pytest.mark.skip()
def test_compacted_rev():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": 72484,  # this returns a 400 as it's a compacted revision
        "min_mod_revision": None,
        "max_mod_revision": None,
    }
    # make the call
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    try:
        backend.forward_impl(request)
    except Exception as e:
        assert isinstance(e, InvalidInputError)


def test_range_rev():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": 10,  # this is a compacted revision
        "max_mod_revision": 100000000000,  # this is a future revision
    }
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    resp = backend.forward_impl(request)
    assert resp
    assert json.loads(resp.decode()) != {}


def test_range_compacted():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": 10,  # this is a compacted revision
        "max_mod_revision": 90,  # this is a compacted revision
    }
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    resp = backend.forward_impl(request)
    assert resp
    assert json.loads(resp.decode()) != {}


def test_range_future():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": 1000000000,  # this is a future revision
        "max_mod_revision": 100000000000,  # this is a future revision
    }
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    resp = backend.forward_impl(request)
    assert resp
    assert json.loads(resp.decode()) != {}


def test_from_compacted_rev():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": 10,  # this is a compacted revision
        "max_mod_revision": None,
    }
    request = RequestDict(data=json.dumps(body))

    # make the call
    backend = BackendAdapter(conf())
    resp = backend.forward_impl(request)
    assert resp
    assert json.loads(resp.decode()) != {}


def test_no_body():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # make the call
    request = RequestDict(data=None)

    # make the call
    backend = BackendAdapter(conf())
    try:
        backend.forward_impl(request)
    except Exception as e:
        assert isinstance(e, InvalidInputError)
