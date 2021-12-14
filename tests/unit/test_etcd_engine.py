# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import contextlib
import datetime
import json
import logging
import os
import subprocess
import time
from shutil import rmtree
from threading import Thread

import pytest

from pyaviso import HOME_FOLDER, logger, user_config
from pyaviso.authentication import auth
from pyaviso.engine.etcd_engine import LOCAL_STATE_FOLDER
from pyaviso.engine.etcd_grpc_engine import EtcdGrpcEngine
from pyaviso.engine.etcd_rest_engine import EtcdRestEngine


def rest_engine():  # this automatically configure the logging
    c = user_config.UserConfig(conf_path="tests/config.yaml")
    authenticator = auth.Auth.get_auth(c)
    engine = EtcdRestEngine(c.notification_engine, authenticator)
    return engine


def grpc_engine():  # this automatically configure the logging
    c = user_config.UserConfig(conf_path="tests/config.yaml")
    authenticator = auth.Auth.get_auth(c)
    engine = EtcdGrpcEngine(c.notification_engine, authenticator)
    return engine


# setting up multiple engines to test
engines = [rest_engine(), grpc_engine()]


@pytest.mark.parametrize("engine", engines)
@pytest.fixture(autouse=True)
def pre_post_test(engine):
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
    try:
        engine.delete("test")
        engine.stop()
    except Exception:
        pass


@pytest.mark.parametrize("engine", [rest_engine()])
def test_authenticate(engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    assert engine._authenticate()


@pytest.mark.parametrize("engine", [grpc_engine()])
def test_locks(engine):
    # acquire lock
    test_lock = engine.lock("test-lock")
    assert test_lock

    # acquire second lock with different id and release it
    test_lock2 = engine.lock("test-lock2")
    assert test_lock2
    assert engine.unlock(test_lock2)

    # acquire second lock with same id
    try:
        engine.lock("test-lock")
    except Exception as e:
        assert "Not able to acquire lock" in e.args[0]

    # release the lock and try again
    assert engine.unlock(test_lock)
    test_lock = engine.lock("test-lock")
    assert test_lock

    # release it to before return
    assert engine.unlock(test_lock)


@pytest.mark.parametrize("engine", engines)
def test_pull(engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # first create 2 keys
    kv1 = {"key": "test1", "value": "1"}
    kv2 = {"key": "test11", "value": "2"}
    kvs = [kv1, kv2]
    assert engine.push(kvs)

    # test basic pull - prefix = true by default
    resp = engine.pull(key="test1")
    assert len(resp) > 1

    # test pull prefix = false -> only this key
    resp0 = engine.pull(key="test1", prefix=False)
    assert len(resp0) == 1

    # test with not existing key
    resp = engine.pull(key="test2", prefix=False)
    assert len(resp) == 0

    # test to pull only keys
    resp = engine.pull(key="test1", prefix=False, key_only=True)
    assert len(resp) == 1
    assert "value" not in resp[0]

    # test to retrieve creation rev
    rev0 = int(resp0[0]["create_rev"])
    resp = engine.pull(key="test1", prefix=False, rev=rev0)
    assert len(resp) == 1
    # test to retrieve non-existing rev
    resp = engine.pull(key="test1", prefix=False, rev=rev0 - 1)
    assert len(resp) == 0


@pytest.mark.parametrize("engine", engines)
def test_push_delete(engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # create 2 kvs and pushed them
    kv1 = {"key": "test1", "value": "1"}
    kv2 = {"key": "test2", "value": "2"}
    kvs = [kv1, kv2]
    resp = engine.push(kvs)
    assert resp

    # verify they exist
    resp = engine.pull(key="test")
    assert len(resp) == 2

    # modify one and delete the other
    kv1 = {"key": "test1", "value": "3"}
    kvs = [kv1]
    kvs_delete = ["test2"]
    resp = engine.push(kvs, kvs_delete)
    assert resp

    # verify there is only one now
    resp = engine.pull(key="test")
    assert len(resp) == 1


@pytest.mark.parametrize("engine", engines)
def test_revisions(engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # first create some keys
    kvs = [{"key": "test0", "value": "0"}]
    assert engine.push(kvs)

    kvs = [{"key": "test1", "value": "1"}]
    assert engine.push(kvs)

    # on the last revision add one key and modify an old one
    kvs = [{"key": "test2", "value": "2"}, {"key": "test1", "value": "2"}]
    assert engine.push(kvs)

    # retrieve this last revision
    last_revision = engine._latest_revision("test/")
    assert last_revision > 0

    # add another key
    kvs = [{"key": "test3", "value": "3"}]
    assert engine.push(kvs)

    # now check we get 3 keys: test1, test2, test3
    resp = engine.pull(key="test", min_rev=last_revision)
    assert len(resp) == 3

    latest_revision = engine._latest_revision("test/")
    # now check we get 2 keys: test1, test2
    resp = engine.pull(key="test", min_rev=last_revision, max_rev=latest_revision - 1)
    assert len(resp) == 2


@pytest.mark.parametrize("engine", engines)
def test_listen(engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    callback_list = []

    def callback(key, value):
        callback_list.append(1)

    # listen to a test key
    assert engine.listen(["test"], callback)
    # wait a fraction and check the function has been triggered
    time.sleep(0.5)

    # create independent change to the test key to trigger the notification
    kvs = [{"key": "test1", "value": "1"}]
    assert engine.push(kvs)
    # wait a fraction and check the function has been triggered
    time.sleep(2)
    assert len(callback_list) == 1

    # repeat the push operation
    kvs = [{"key": "test1", "value": "2"}]
    assert engine.push(kvs)
    # wait a fraction and check the function has been triggered
    time.sleep(2)
    assert len(callback_list) == 2

    # stop listening
    resp = engine.stop()
    assert resp

    # repeat the push operation
    kvs = [{"key": "test1", "value": "2"}]
    assert engine.push(kvs)

    # wait a fraction and check the function has NOT been triggered
    time.sleep(2)
    assert len(callback_list) == 2


@pytest.mark.parametrize("engine", engines)
def test_listen_old_state(engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    callback_list = []

    def callback(key, value):
        callback_list.append(1)

    # listen to a test key from no state
    assert engine.listen(["test"], callback)
    # wait a fraction and check the function has been triggered
    time.sleep(0.5)
    assert len(callback_list) == 0

    # create independent change to the test key to trigger the notification
    kvs = [{"key": "test1", "value": "1"}]
    assert engine.push(kvs)
    # wait a fraction and check the function has been triggered
    time.sleep(2)
    assert len(callback_list) == 1

    # stop listening
    resp = engine.stop()
    assert resp

    # repeat the push operation
    kvs = [{"key": "test1", "value": "2"}]
    assert engine.push(kvs)
    kvs = [{"key": "test2", "value": "2"}]
    assert engine.push(kvs)
    # wait a fraction and check the function has NOT been triggered
    time.sleep(2)
    assert len(callback_list) == 1

    # listen again
    assert engine.listen(["test"], callback)
    # wait a fraction and check the function has been triggered
    time.sleep(2)
    # check the state has been used to retrieved the key updates while we were not listening
    assert len(callback_list) == 3


@pytest.mark.parametrize("engine", engines)
def test_find_revisions(engine):
    kvs = [{"key": "test/test", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")

    time.sleep(0.1)
    from_date = datetime.datetime.utcnow()
    time.sleep(0.1)

    kvs = [{"key": "test/test0", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")
    first_revision = engine._latest_revision("test/")

    kvs = [{"key": "test/test1", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test1")
    assert engine.push(kvs)
    second_revision = engine._latest_revision("test/")

    # send something to a different destination
    kvs = [{"key": "test2/test1", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test2/", message="test2/test1")
    assert engine.push(kvs)

    time.sleep(0.1)
    to_date = datetime.datetime.utcnow()
    time.sleep(0.1)

    kvs = [{"key": "test/test2", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test2")
    assert engine.push(kvs)

    # send something to a different destination
    kvs = [{"key": "test2/test2", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test2/", message="test2/test2")
    assert engine.push(kvs)

    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=from_date, to_date=to_date)
    assert from_rev_found == first_revision
    assert to_rev_found == second_revision


@pytest.mark.parametrize("engine", engines)
def test_find_revisions_limits_from(engine):
    time1 = datetime.datetime.utcnow()
    time.sleep(0.1)

    # search for revisions when no point is present
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time1)
    assert from_rev_found is None

    kvs = [{"key": "test/test", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")
    revision = engine._latest_revision("test/")

    # search for revisions with one point after from
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time1)
    assert from_rev_found == revision
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 2

    time.sleep(0.1)
    time2 = datetime.datetime.utcnow()
    time.sleep(0.1)

    # search for revisions with one point before from
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time2)
    assert from_rev_found == revision + 1
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 0

    kvs = [{"key": "test/test0", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")
    revision = engine._latest_revision("test/")

    # search for revisions with from between points
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time2)
    assert from_rev_found == revision
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 2


@pytest.mark.parametrize("engine", engines)
def test_find_revisions_limits_from_to(engine):
    time1 = datetime.datetime.utcnow()
    time.sleep(0.1)

    # search for revisions when no point is present
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time1, to_date=time1)
    assert from_rev_found is None
    assert to_rev_found is None

    kvs = [{"key": "test/test", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")
    revision = engine._latest_revision("test/")

    # search for revisions with one point after the interval
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time1, to_date=time1)
    assert from_rev_found == revision - 1
    assert to_rev_found == revision - 1
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 0

    time.sleep(0.1)
    time2 = datetime.datetime.utcnow()
    time.sleep(0.1)

    # search for revisions with one point before the interval
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time2, to_date=time2)
    assert from_rev_found == revision + 1
    assert to_rev_found == revision + 1
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 0

    # search for revisions with one point in the interval
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time1, to_date=time2)
    assert from_rev_found == revision
    assert to_rev_found == revision
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 2  # one is the status

    kvs = [{"key": "test/test0", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")
    revision = engine._latest_revision("test/")

    # search for revisions with the interval between points
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time2, to_date=time2)
    assert from_rev_found == revision
    assert to_rev_found == revision - 1
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 0


@pytest.mark.parametrize("engine", engines)
def test_find_compacted_revision(engine):
    time0 = datetime.datetime.utcnow()
    time.sleep(0.1)

    kvs = [{"key": "test/test0", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")
    engine._latest_revision("test/")

    time.sleep(0.1)

    kvs = [{"key": "test/test1", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0")
    revision1 = engine._latest_revision("test/")

    # compact revision 1 so revision 0 is no longer accessible
    import etcd3

    etcd = etcd3.client(host=engine.host, port=engine.port)
    etcd.compact(revision1)

    time.sleep(0.1)
    time2 = datetime.datetime.utcnow()
    time.sleep(0.1)

    # search for revisions with one point after the interval
    from_rev_found, to_rev_found = engine._from_to_revisions("test/", from_date=time0, to_date=time2)
    assert from_rev_found == revision1
    assert to_rev_found == revision1
    assert len(engine.pull("test/", min_rev=from_rev_found, max_rev=to_rev_found)) == 2


@pytest.mark.parametrize("engine", engines)
def test_push_with_lease(engine):

    # submit a key expiring
    kvs = [{"key": "test/test0", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test0", ttl=1)
    assert len(engine.pull("test/")) == 2

    # submit a key not expiring
    kvs = [{"key": "test/test1", "value": "0"}]
    assert engine.push_with_status(kvs, base_key="test/", message="test/test1")
    assert len(engine.pull("test/")) == 3

    time.sleep(3)

    # check that the expiring key has gone but not the status
    assert len(engine.pull("test/")) == 2


@pytest.mark.parametrize("engine", engines)
def test_status_as_linked_list(engine):

    status0 = {"date_time": "2020-08-28T10:58:17.829Z"}
    kv0 = {"mod_rev": "100", "value": json.dumps(status0).encode()}

    status1 = {"date_time": "2020-08-28T15:58:17.829Z"}  # same day, a bit later
    engine._status_as_linked_list(status1, [kv0])
    assert status1.get("prev_rev") == "100"
    assert status1.get("last_prev_day_rev") is None
    kv1 = {"mod_rev": "101", "value": json.dumps(status1).encode()}

    status2 = {"date_time": "2020-08-28T20:58:17.829Z"}  # same day, a bit later
    engine._status_as_linked_list(status2, [kv1])
    assert status2.get("prev_rev") == "101"
    assert status2.get("last_prev_day_rev") is None
    kv2 = {"mod_rev": "102", "value": json.dumps(status2).encode()}

    status3 = {"date_time": "2020-08-29T10:58:17.829Z"}  # day after -> first_of_day
    engine._status_as_linked_list(status3, [kv2])
    assert status3.get("prev_rev") == "102"
    assert status3.get("last_prev_day_rev") == "102"
    kv3 = {"mod_rev": "103", "value": json.dumps(status3).encode()}

    status4 = {"date_time": "2020-08-29T15:58:17.829Z"}  # same day, a bit later
    engine._status_as_linked_list(status4, [kv3])
    assert status4.get("prev_rev") == "103"
    assert status4.get("last_prev_day_rev") == "102"


@pytest.mark.parametrize("engine", engines)
def test_save_delete_state(engine):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # first save state revision
    last_rev = 10
    assert engine._save_last_revision(last_rev)
    assert engine._last_saved_revision() == last_rev

    # delete it
    engine._delete_saved_revision()
    assert engine._last_saved_revision() == -1


@contextlib.contextmanager
def caplog_for_logger(caplog):  # this is needed to assert over the logging output
    caplog.clear()
    lo = logging.getLogger()
    lo.addHandler(caplog.handler)
    caplog.handler.setLevel(logging.DEBUG)
    yield
    lo.removeHandler(caplog.handler)


@pytest.mark.parametrize("engine", [rest_engine()])
def test_automatic_retry(engine, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    # create a process listening to a port
    subprocess.Popen(
        f"nc -l {10001}", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # set timeout to 1s
    engine.timeout = 1
    engine._base_url = "http://127.0.0.1:10001/v3/"

    # run a basic pull as background thread and check the log
    server = Thread(target=engine.pull, daemon=True, kwargs={"key": "test1"})
    server.start()
    time.sleep(2)

    for record in caplog.records:
        assert record.levelname != "ERROR"
    # check that it's trying again in the system log
    assert "Unable to connect to http://127.0.0.1:10001/v3/kv/range, trying again in" in caplog.text
