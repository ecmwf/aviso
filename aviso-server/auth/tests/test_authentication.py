# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import random
import subprocess

import yaml
from aviso_auth import config, logger
from aviso_auth.authentication import Authenticator
from aviso_auth.custom_exceptions import (
    AuthenticationUnavailableException,
    TokenNotValidException,
)


def conf() -> config.Config:  # this automatically configure the logging
    return config.Config(conf_path=os.path.expanduser("~/.aviso-auth/testing/config.yaml"))


def valid_token() -> str:
    with open(os.path.expanduser("~/.aviso-auth/testing/credentials.yaml"), "r") as f:
        c = yaml.load(f.read(), Loader=yaml.Loader)
        return c["token"]


def valid_user() -> str:
    with open(os.path.expanduser("~/.aviso-auth/testing/credentials.yaml"), "r") as f:
        c = yaml.load(f.read(), Loader=yaml.Loader)
        return c["user"]


def valid_email() -> str:
    with open(os.path.expanduser("~/.aviso-auth/testing/credentials.yaml"), "r") as f:
        c = yaml.load(f.read(), Loader=yaml.Loader)
        return c["email"]


def test_token_to_username():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authenticator(conf())
    username, email = auth._token_to_username(valid_token())
    assert username == valid_user()
    assert email.lower() == valid_email().lower()


def test_bad_token():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth = Authenticator(conf())
    try:
        auth._token_to_username("111111111111112222222222333333")
    except Exception as e:
        assert isinstance(e, TokenNotValidException)


def test_bad_url():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    c = conf()
    c.authentication_server["url"] = "https://fake-url.ecmwf.int"
    auth = Authenticator(c)
    try:
        auth._token_to_username(valid_token())
    except Exception as e:
        assert isinstance(e, AuthenticationUnavailableException)


def test_timeout():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    port = random.randint(10000, 20000)
    # create a process listening to a port
    subprocess.Popen(f"nc -l {port}", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    c = conf()
    c.authentication_server["url"] = f"https://127.0.0.1:{port}"
    c.authentication_server["req_timeout"] = 1
    auth = Authenticator(c)
    try:
        auth._token_to_username(valid_token())
    except Exception as e:
        assert isinstance(e, AuthenticationUnavailableException)
