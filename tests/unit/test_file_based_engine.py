# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import time
from pathlib import Path
from shutil import rmtree

import pytest

from pyaviso import HOME_FOLDER, logger, user_config
from pyaviso.authentication import auth
from pyaviso.engine.etcd_engine import LOCAL_STATE_FOLDER
from pyaviso.engine.file_based_engine import FileBasedEngine


@pytest.fixture()
def test_engine():  # this automatically configure the logging
    tests_path = Path(__file__).parent.parent
    c = user_config.UserConfig(conf_path=Path(tests_path / "config.yaml"))
    authenticator = auth.Auth.get_auth(c)
    engine = FileBasedEngine(c.notification_engine, authenticator)
    return engine


@pytest.fixture(autouse=True)
def pre_post_test(test_engine):
    # delete the revision state
    full_home_path = os.path.expanduser(HOME_FOLDER)
    full_state_path = os.path.join(full_home_path, LOCAL_STATE_FOLDER)
    if os.path.exists(full_state_path):
        try:
            rmtree(full_state_path)
        except Exception:
            pass
    yield
    # delete all the keys at the end of the test
    # test_engine.delete("/tmp/aviso/test")
    test_engine.stop()


def test_push_pull_delete(test_engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # create 2 kvs and pushed them
    kv1 = {"key": "/tmp/aviso/test/test1", "value": "1"}
    kv2 = {"key": "/tmp/aviso/test/test2", "value": "2"}
    kvs = [kv1, kv2]
    resp = test_engine.push(kvs)
    assert resp

    # verify they exist
    resp = test_engine.pull(key="/tmp/aviso/test")
    assert len(resp) == 2

    # modify one and delete the other
    kv1 = {"key": "/tmp/aviso/test/test1", "value": "3"}
    kvs = [kv1]
    kvs_delete = ["/tmp/aviso/test/test2"]
    resp = test_engine.push(kvs, kvs_delete)
    assert resp

    # verify there is only one now
    resp = test_engine.pull(key="/tmp/aviso/test/")
    assert len(resp) == 1


def test_listen(test_engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    callback_list = []

    def callback(key, value):
        logger.debug(f"Callback triggered for key: {key}")
        callback_list.append(1)

    # Listen to a test key
    assert test_engine.listen(["/tmp/aviso/test"], callback)
    time.sleep(0.5)  # Increased wait time

    # Create independent change to the test key to trigger the notification
    kvs = [{"key": "/tmp/aviso/test/test1", "value": "1"}]
    assert test_engine.push(kvs)
    time.sleep(1)  # Increased wait time
    assert len(callback_list) == 1

    # Repeat the push operation
    kvs = [{"key": "/tmp/aviso/test/test1", "value": "2"}]
    assert test_engine.push(kvs)
    time.sleep(1)  # Increased wait time
    assert len(callback_list) == 2

    # Stop listening
    resp = test_engine.stop()
    assert resp

    # Repeat the push operation
    kvs = [{"key": "/tmp/aviso/test/test1", "value": "3"}]
    assert test_engine.push(kvs)

    # Wait and check that the function has NOT been triggered
    time.sleep(1)
    assert len(callback_list) == 2