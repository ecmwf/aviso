# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
from pathlib import Path

import pytest

from pyaviso import logger, user_config
from pyaviso.authentication import auth, ecmwf_auth, etcd_auth, none_auth
from pyaviso.engine import engine_factory


def conf() -> user_config.UserConfig:  # this automatically configure the logging
    tests_path = Path(__file__).parent.parent
    c = user_config.UserConfig(conf_path=Path(tests_path / "config.yaml"))
    return c


# set parameter array
confs = [conf()]


@pytest.fixture(autouse=True)  # this runs before and after every test
def pre_post_test():
    # do nothing before each test
    yield


@pytest.mark.parametrize("conf", [conf()])
def test_auth_type(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    auth1 = auth.Auth.get_auth(conf)
    conf.auth_type = "etcd"
    conf.password = "tests"
    auth2 = auth.Auth.get_auth(conf)
    conf.auth_type = "ecmwf"
    auth3 = auth.Auth.get_auth(conf)
    assert isinstance(auth1, none_auth.NoneAuth)
    assert isinstance(auth2, etcd_auth.EtcdAuth)
    assert isinstance(auth3, ecmwf_auth.EcmwfAuth)


@pytest.mark.skip  # we cannot authenticate in this test setup
@pytest.mark.parametrize("conf", confs)
def test_etcd_auth_fail(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # test with wrong password
    conf.auth_type = "etcd"
    auth1 = auth.Auth.get_auth(conf)
    auth1._password = "wrong"
    eng_fact = engine_factory.EngineFactory(conf.notification_engine, auth1)
    eng = eng_fact.create_engine()
    assert auth1.token is None
    try:
        eng._authenticate()
        assert False
    except Exception:
        pass
    assert auth1.token is None
