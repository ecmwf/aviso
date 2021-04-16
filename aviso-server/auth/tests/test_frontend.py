import pytest
import os
import requests
import yaml
import time
import threading

from aviso_auth import config, logger
from aviso_auth.authorisation import Authoriser
from aviso_auth.frontend import Frontend

def conf() -> config.Config:  # this automatically configure the logging
    return config.Config(conf_path=os.path.expanduser("~/.aviso-auth/testing/config.yaml"))

configuration = conf()
frontend_url = f"http://{configuration.frontend['host']}:{configuration.frontend['port']}{configuration.backend['route']}"

def valid_token() -> str: 
    with open(os.path.expanduser("~/.aviso-auth/testing/credentials.yaml"), "r") as f:
        c = yaml.load(f.read(), Loader=yaml.Loader)
        return c["token"]

def valid_email() -> str: 
    with open(os.path.expanduser("~/.aviso-auth/testing/credentials.yaml"), "r") as f:
        c = yaml.load(f.read(), Loader=yaml.Loader)
        return c["email"]


@pytest.fixture(scope="module", autouse=True)
def prepost_module():
    # Run the frontend at global level so it will be executed once and accessible to all tests
    frontend = Frontend(configuration)
    server = threading.Thread(target=frontend.run_server, daemon=True)
    server.start()
    time.sleep(1)
    yield


def test_successful_request():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, headers={"Authorization": f"EmailKey {valid_email()}:{valid_token()}"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 200


def test_bad_authorisation_header():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, headers={"Authorization": valid_token()},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 401


def test_bad_authorisation_format():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, headers={"Authorization": f"EmailKey {valid_email()}-{valid_token()}"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 401


def test_bad_token():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, headers={"Authorization": f"EmailKey {valid_email()}:1111112222233333"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 401


def test_bad_destination():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    key = "/ec/diss/SCL2"
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, headers={"Authorization": f"EmailKey {valid_email()}:{valid_token()}"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 403


def test_bad_backend_key():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    key = "/ec2/diss/SCL"
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, headers={"Authorization": f"EmailKey {valid_email()}:{valid_token()}"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 403


def test_no_token():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 401


def test_no_body():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # make the call
    resp = requests.post(frontend_url, headers={"Authorization": f"EmailKey {valid_email()}:{valid_token()}"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 400


def test_no_backend_key():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    key = "/ec/diss/SCL"
    # encode key
    encoded_key = Authoriser._encode_to_str_base64(key)
    range_end = Authoriser._encode_to_str_base64(str(Authoriser._incr_last_byte(key), "utf-8"))
    # create the body for the get range on the etcd sever
    body = {
        "keyyy": encoded_key,
        "range_end": range_end,
        "limit": 100,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "keys_only": False,
        "revision": None,
        "min_mod_revision": None,
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url, json=body, headers={"Authorization": f"EmailKey {valid_email()}:{valid_token()}"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 400

def test_bad_route():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
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
        "max_mod_revision": None
    }
    # make the call
    resp = requests.post(frontend_url[:-3], json=body, headers={"Authorization": f"EmailKey {valid_email()}:{valid_token()}"},
                         timeout=configuration.backend['req_timeout'])
    assert resp.status_code == 404
