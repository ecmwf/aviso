# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import contextlib
import logging
import os
import time
from datetime import datetime
from shutil import rmtree

import pytest
from click.testing import CliRunner

from pyaviso import HOME_FOLDER, NotificationManager, logger, user_config
from pyaviso.authentication import auth
from pyaviso.cli_aviso import _parse_inline_params, key, notify, value
from pyaviso.engine.engine_factory import EngineType
from pyaviso.engine.etcd_engine import LOCAL_STATE_FOLDER
from pyaviso.engine.etcd_grpc_engine import EtcdGrpcEngine
from pyaviso.engine.etcd_rest_engine import EtcdRestEngine
from pyaviso.engine.file_based_engine import FileBasedEngine

aviso = NotificationManager()


def create_conf() -> user_config.UserConfig:  # this automatically configure the logging
    c = user_config.UserConfig(conf_path="tests/config.yaml")
    return c


# setting up multiple configurations for running the tests multiple times
c1 = create_conf()
c1.notification_engine.type = EngineType.ETCD_REST
c2 = create_conf()
c2.notification_engine.type = EngineType.ETCD_GRPC
c3 = create_conf()
c3.notification_engine.type = EngineType.FILE_BASED
configs = [c1, c2, c3]


@pytest.fixture(scope="module", autouse=True)
def clear_environment():
    yield
    try:
        os.environ.pop("AVISO_CONFIG")
    except KeyError:  # ignore
        pass
    try:
        os.environ.pop("AVISO_NOTIFICATION_ENGINE")
    except KeyError:  # ignore
        pass
    try:
        os.environ.pop("AVISO_TIMEOUT")
    except KeyError:  # ignore
        pass


@pytest.mark.parametrize("config", configs)
@pytest.fixture(autouse=True)  # this runs before and after every test
def pre_post_test(config):
    # delete the revision state
    full_home_path = os.path.expanduser(HOME_FOLDER)
    full_state_path = os.path.join(full_home_path, LOCAL_STATE_FOLDER)
    if os.path.exists(full_state_path):
        try:
            rmtree(full_state_path)
        except Exception:
            pass

    # set environment
    os.environ["AVISO_CONFIG"] = "tests/config.yaml"
    os.environ["AVISO_NOTIFICATION_ENGINE"] = config.notification_engine.type.name
    yield
    # now delete the listener
    aviso.listener_manager.cancel_listeners()
    time.sleep(0.5)


def engine(config):
    authenticator = auth.Auth.get_auth(config)
    if config.notification_engine.type == EngineType.ETCD_REST:
        eng = EtcdRestEngine(config.notification_engine, authenticator)
    elif config.notification_engine.type == EngineType.ETCD_GRPC:
        eng = EtcdGrpcEngine(config.notification_engine, authenticator)
    elif config.notification_engine.type == EngineType.FILE_BASED:
        eng = FileBasedEngine(config.notification_engine, authenticator)
    return eng


def send_notification_as_cli(config, airport="fco"):
    params = f"event=flight,country=Italy,airport={airport},date=20210101,number=AZ203,payload=Landed"
    ps = _parse_inline_params(params)
    aviso.notify(ps, config=config)


def send_notification_as_dict(config):
    notification = {
        "event": "flight",
        "country": "italy",
        "date": "20210101",
        "airport": "FCO",
        "number": "AZ203",
        "payload": "Landed",
    }
    aviso.notify(notification=notification, config=config)


@contextlib.contextmanager
def caplog_for_logger(caplog):  # this is needed to assert over the logging output
    caplog.clear()
    lo = logging.getLogger()
    lo.addHandler(caplog.handler)
    caplog.handler.setLevel(logging.DEBUG)
    yield
    lo.removeHandler(caplog.handler)


def reset_previuous_run():
    file_path = "tests/system/fixtures/received.txt"
    full_path = os.path.join(os.getcwd(), file_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except Exception:
            pass
    return full_path


@pytest.mark.parametrize("config", [c1, c2])
def test_command_listener(config):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    # delete previous file of notification
    file_path = reset_previuous_run()

    aviso._listen(config, ["tests/system/fixtures/listeners/command_listener.yaml"])

    time.sleep(3)

    # create independent client to trigger the notification
    send_notification_as_cli(config)
    time.sleep(3)

    # check if the notification has been save to file
    received = False
    for i in range(30):
        if os.path.exists(file_path):
            received = True
            break
        else:
            time.sleep(1)
    assert received

    # delete result of notification
    file_path = reset_previuous_run()


@pytest.mark.parametrize("config", configs)
def test_key(config):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])

    assert result.exit_code == 0
    assert "/tmp/aviso/flight/20210101/italy/FCO/AZ203" in result.output


@pytest.mark.parametrize("config", configs)
def test_notify_and_value(config):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(
        notify, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Departed"]
    )

    assert result.exit_code == 0
    assert "Done" in result.output

    # now test the value command
    result = runner.invoke(value, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
    assert result.exit_code == 0
    assert "Departed" in result.output

    # now test the status has been updated
    eng = engine(config)
    kvs = eng.pull("/tmp/aviso/flight/", prefix=False)
    assert len(kvs) == 1
    status = kvs[0]["value"].decode()
    assert "notification to key /tmp/aviso/flight/20210101/italy/FCO/AZ203" in status


@pytest.mark.parametrize("config", configs)
def test_notify_no_payload(config):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(notify, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])

    assert result.exit_code == 0
    assert "Done" in result.output

    # now test the value command
    result = runner.invoke(value, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
    assert result.exit_code == 0
    assert "None" in result.output


@pytest.mark.parametrize("config", configs)
def test_notify_test(config):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(
        notify, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Departed", "--test"]
    )

    assert result.exit_code == 0
    assert "TEST MODE" in result.output
    assert "Done" in result.output


@pytest.mark.parametrize("config", [c1, c2])
def test_notify_ttl(config):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    runner = CliRunner()
    result = runner.invoke(
        notify, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Departed,ttl=1"]
    )

    assert result.exit_code == 0
    assert "Done" in result.output

    # now retrieve it
    result = runner.invoke(value, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
    assert result.exit_code == 0
    assert "Departed" in result.output

    # wait for it to expire
    time.sleep(3)

    # now test the value command
    result = runner.invoke(value, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
    assert result.exit_code == 0
    assert "None" in result.output


@pytest.mark.skip
@pytest.mark.parametrize("config", [c1])
def test_history_on_server(config: user_config.UserConfig, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        config.notification_engine.host = "aviso.ecmwf.int"
        config.notification_engine.port = 80
        config.configuration_engine.host = "aviso.ecmwf.int"
        config.configuration_engine.port = 80
        config.auth_type = "ecmwf"
        config.username = "xxxx"
        config.key_file = "xxxx"
        config.password = config._read_key()
        from_d = datetime.strptime("2020-09-02T10:12:50.0Z", "%Y-%m-%dT%H:%M:%S.%fZ")
        to_d = datetime.strptime("2020-09-02T10:12:51.0Z", "%Y-%m-%dT%H:%M:%S.%fZ")
        aviso._listen(config, ["tests/system/fixtures/listeners/echoListenerTest.yaml"], from_date=from_d, to_date=to_d)
        time.sleep(1000)
