import os
import random
import subprocess

import yaml
from aviso_auth import config, logger
from aviso_auth.authorisation import Authoriser
from aviso_auth.custom_exceptions import (
    AuthorisationUnavailableException,
    InternalSystemError,
    UserNotFoundException,
)


def conf() -> config.Config:  # this automatically configure the logging
    return config.Config(conf_path=os.path.expanduser("~/.aviso-auth/testing/config.yaml"))


def valid_user() -> str:
    with open(os.path.expanduser("~/.aviso-auth/testing/credentials.yaml"), "r") as f:
        c = yaml.load(f.read(), Loader=yaml.Loader)
        return c["user"]


def test_allowed_destinations():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authoriser(conf())
    destinations = auth._allowed_destinations(valid_user())
    print(destinations)
    assert len(destinations) > 0


def test_not_allowed_destinations():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authoriser(conf())
    try:
        auth._allowed_destinations("fake_user")
    except Exception as e:
        assert isinstance(e, UserNotFoundException)
        assert "fake_user not found" in str(e)


def test_bad_url():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    c = conf()
    c.authorisation_server["url"] = "https://fake_url.ecmwf.int"
    auth = Authoriser(c)
    try:
        auth._allowed_destinations(valid_user())
    except Exception as e:
        assert isinstance(e, AuthorisationUnavailableException)


def test_timeout():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    port = random.randint(10000, 20000)
    # create a process listening to a port
    subprocess.Popen(f"nc -l {port}", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    c = conf()
    c.authorisation_server["url"] = f"https://127.0.0.1:{port}"
    c.authorisation_server["req_timeout"] = 1
    auth = Authoriser(c)
    try:
        auth._allowed_destinations(valid_user())
    except Exception as e:
        assert isinstance(e, AuthorisationUnavailableException)


def test_bad_credentials():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    c = conf()
    c.authorisation_server["username"] = "fake_user"
    auth = Authoriser(c)
    try:
        auth._allowed_destinations(valid_user())
    except Exception as e:
        assert isinstance(e, InternalSystemError)


def test_is_backend_key_allowed_diss():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authoriser(conf())
    assert auth._is_backend_key_allowed(valid_user(), "/ec/diss/SCL/any")


def test_is_backend_key_allowed_diss_fail():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authoriser(conf())
    assert not auth._is_backend_key_allowed(valid_user(), "/ec/diss/fake_dest")


def test_is_backend_key_allowed_mars():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authoriser(conf())
    assert auth._is_backend_key_allowed(valid_user(), "/ec/mars/any")


def test_is_backend_key_allowed_other_fail():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authoriser(conf())
    assert not auth._is_backend_key_allowed(valid_user(), "/ec/any")
