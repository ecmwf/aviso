import os
import threading
import time

import pytest
import requests
import yaml
from aviso_auth import config, logger
from aviso_auth.authorisation import Authoriser
from aviso_auth.frontend import Frontend
from flask import Flask
from werkzeug.exceptions import InternalServerError


def conf() -> config.Config:  # this automatically configure the logging
    c = config.Config(conf_path=os.path.expanduser("~/.aviso-auth/testing/config.yaml"))
    c.backend["url"] = "http://127.0.0.1:8022"
    c.frontend["port"] = 8083
    return c


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

# mock backend
mock_backend = Flask("Backend")
@mock_backend.route(configuration.backend["route"],  methods=['POST'])
def error():
    return InternalServerError("Test Error")

@pytest.fixture(scope="module", autouse=True)
def prepost_module():
    # Run the frontend at global level so it will be executed once and accessible to all tests
    frontend = Frontend(configuration)
    server = threading.Thread(target=frontend.run_server, daemon=True)
    server.start()
    time.sleep(1)
    # Run the mock backend
    backend = threading.Thread(target=mock_backend.run, daemon=True, kwargs={"host": "127.0.0.1", "port": 8022})
    backend.start()
    time.sleep(1)
    yield

def test_broken_aviso_server():
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
    assert resp.status_code == 503