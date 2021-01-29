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
import random
import subprocess
from datetime import datetime
from shutil import rmtree
from multiprocessing import Process
from flask import Flask
from flask import request

import pytest
from click.testing import CliRunner

from pyaviso import HOME_FOLDER
from pyaviso import user_config
from pyaviso.authentication import auth
from pyaviso.cli_aviso import *
from pyaviso.cli_aviso import _parse_inline_params
from pyaviso.engine.engine_factory import EngineType
from pyaviso.engine.etcd_engine import LOCAL_STATE_FOLDER
from pyaviso.engine.etcd_grpc_engine import EtcdGrpcEngine
from pyaviso.engine.etcd_rest_engine import EtcdRestEngine
from pyaviso.engine.file_based_engine import FileBasedEngine
from pyaviso.event_listeners.listener_schema_parser import ListenerSchemaParser

aviso = NotificationManager()


def schema():
    # Load the schema
    listener_schema = ListenerSchemaParser().load(conf)
    return listener_schema['flight']


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
    # noinspection PyUnboundLocalVariable
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
        "payload": "Landed"
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


@pytest.mark.parametrize("config", configs)
def test_function_trigger(config: user_config.UserConfig):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create a list that increments every time there is a new event
    trigger_list = []

    def trigger_function(notification):
        trigger_list.append(notification['payload'])

    trigger = {"type": "function", "function": trigger_function}

    # create a listener that uses that trigger
    request = {"country": "Italy"}
    listener = {"event": "flight", "request": request, "triggers": [trigger]}
    listeners = {"listeners": [listener]}

    # run it
    aviso._listen(config, listeners=listeners)
    time.sleep(1)
    # create independent client to trigger the notification
    send_notification_as_cli(config)
    time.sleep(2)
    assert trigger_list.__len__() == 1


@pytest.mark.parametrize("config", configs)
def test_echo_listener(config: user_config.UserConfig, caplog):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/echo_listener.yaml"])

        time.sleep(1)

        # trigger the notification as CLI
        send_notification_as_cli(config)
        time.sleep(2)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        # check  the trigger has logged the notification on the system log
        assert "Echo Trigger completed" in caplog.text

        # trigger the notification as dict
        send_notification_as_dict(config)
        time.sleep(2)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        # check  the trigger has logged the notification on the system log
        assert "Echo Trigger completed" in caplog.text


@pytest.mark.parametrize("config", configs)
def test_echo_listener_from_date(config: user_config.UserConfig, caplog):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        if config.notification_engine.type == EngineType.FILE_BASED:
            logger.debug("Test skipped - not implemented for TestEngine")
            return

        # push notification
        send_notification_as_cli(config, 0)

        time.sleep(0.5)
        now = datetime.utcnow()
        time.sleep(0.5)

        # push notification
        send_notification_as_cli(config, 1)

        aviso._listen(config, ["tests/integration/fixtures/listeners/echo_listener.yaml"], from_date=now)

        time.sleep(2)

        # push a new notification
        send_notification_as_cli(config, 2)
        time.sleep(2)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        # check  the trigger has logged the notifications
        assert caplog.text.count("Echo Trigger completed") == 2


@pytest.mark.parametrize("config", configs)
def test_echo_listener_with_dates(config: user_config.UserConfig, caplog):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        if config.notification_engine.type == EngineType.FILE_BASED:
            logger.debug("Test skipped - not implemented for TestEngine")
            return

        # push notification
        send_notification_as_cli(config, 1)

        time.sleep(0.5)
        from_date = datetime.utcnow()
        time.sleep(0.5)

        # push notification
        send_notification_as_cli(config, 2)

        # push notification
        send_notification_as_cli(config, 3)

        time.sleep(0.5)
        to_date = datetime.utcnow()
        time.sleep(0.5)

        aviso._listen(config, ["tests/integration/fixtures/listeners/echo_listener.yaml"],
                     from_date=from_date, to_date=to_date)

        time.sleep(1)

        # push a new notification
        send_notification_as_cli(config, 4)
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        # check  the trigger has logged the notifications
        assert caplog.text.count("Echo Trigger completed") == 2


@pytest.mark.parametrize("config", configs)
def test_logger_listener(config: user_config.UserConfig, caplog):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/log_listener.yaml"])

        time.sleep(1)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(2)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        # check  the trigger has logged the notification on the system log
        assert "Log Trigger completed" in caplog.text
        # check  the trigger has logged the notification on the log specified
        with open(aviso.listener_manager.listeners[0].triggers[0].get("path"), "r") as f:
            assert "Notification received" in f.read()

        # clean up
        if os.path.exists("testLog.log"):
            os.remove("testLog.log")


@pytest.mark.parametrize("config", configs)
def test_command_listener(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/command_listener.yaml"])

        time.sleep(1)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(3)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Command Trigger completed" in caplog.text


@pytest.mark.parametrize("config", configs)
def test_command_json_listener(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/command_json_listener.yaml"])

        time.sleep(1)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(3)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Command Trigger completed" in caplog.text

@pytest.mark.parametrize("config", configs)
def test_command_json_path_listener(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/command_json_path_listener.yaml"])

        time.sleep(1)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(3)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Command Trigger completed" in caplog.text


# test frontend
test_frontend = Flask("Test_Frontend")
@test_frontend.route('/test',  methods=['POST'])
def received():
    return f"Received {request.json}"
#test_frontend.run(host="127.0.0.1", port=8001)

@pytest.mark.parametrize("config", configs)
def test_post_basic_listener(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output

        # start a test frontend to send the notification to
        server = Process(target=test_frontend.run, kwargs={"host": "127.0.0.1", "port": 8001})
        server.start()
    
        aviso._listen(config, ["tests/integration/fixtures/listeners/post_basic_listener.yaml"])

        time.sleep(2)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(3)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Post Trigger completed" in caplog.text
        assert "CloudEvent notification sent successfully" in caplog.text

        # terminate frontend
        server.terminate()
        server.join()
        time.sleep(2)


@pytest.mark.parametrize("config", configs)
def test_post_complete_listener(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/post_complete_listener.yaml"])

        # start a test frontend to send the notification to
        server = Process(target=test_frontend.run, kwargs={"host": "127.0.0.1", "port": 8001})
        server.start()

        time.sleep(2)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(3)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Post Trigger completed" in caplog.text
        assert "CloudEvent notification sent successfully" in caplog.text

        # terminate frontend
        server.terminate()
        server.join()
        time.sleep(2)


@pytest.mark.parametrize("config", configs)
def test_multiple_nots_echo(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/echo_listener.yaml"])

        time.sleep(1)

        # create independent client to trigger the notification
        n_nots = 10
        for i in range(0, n_nots):
            send_notification_as_cli(config, i)
        time.sleep(2)

        # check if the change has been logged twice as there are n_puts notifications
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert caplog.text.count("Echo Trigger completed") == n_nots


@pytest.mark.parametrize("config", configs)
def test_multiple_nots_cmd(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/command_listener.yaml"])

        time.sleep(1)

        # create independent client to trigger the notification
        n_nots = 10
        for i in range(0, n_nots):
            send_notification_as_cli(config, i)
        time.sleep(2)

        # check if the change has been logged twice as there are n_puts notifications
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert caplog.text.count("Command Trigger completed") == n_nots


@pytest.mark.parametrize("config", configs)
def test_multiple_listeners(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/multiple_listeners.yaml"])
        assert aviso.listener_manager.listeners.__len__() == 3
        time.sleep(1)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(2)

        # check if the changes has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert caplog.text.count("Echo Trigger completed") == 3


@pytest.mark.parametrize("config", configs)
def test_multiple_triggers(config: user_config.UserConfig, caplog, capsys):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        aviso._listen(config, ["tests/integration/fixtures/listeners/multiple_triggers.yaml"])

        assert aviso.listener_manager.listeners[0].triggers.__len__() == 3
        time.sleep(1)

        # create independent client to trigger the notification
        send_notification_as_cli(config)
        time.sleep(2)

        # check if the changes has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Echo Trigger completed" in caplog.text
        assert "Log Trigger completed" in caplog.text
        assert "Command Trigger completed" in caplog.text

        # clean up
        if os.path.exists("testLog.log"):
            os.remove("testLog.log")
        if os.path.exists("test.txt"):
            os.remove("test.txt")


@pytest.mark.parametrize("config", configs)
def test_key(config):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    runner = CliRunner()
    result = runner.invoke(key, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])

    assert result.exit_code == 0
    assert "/tmp/aviso/flight/20210101/italy/FCO/AZ203" in result.output


@pytest.mark.parametrize("config", configs)
def test_notify_and_value(config):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    runner = CliRunner()
    # noinspection PyPep8
    result = runner.invoke(notify, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Departed"])

    assert result.exit_code == 0
    assert "Done" in result.output

    # now test the value command
    result = runner.invoke(value, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
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
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    runner = CliRunner()
    # noinspection PyPep8
    result = runner.invoke(notify, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])

    assert result.exit_code == 0
    assert "Done" in result.output

    # now test the value command
    result = runner.invoke(value, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
    assert result.exit_code == 0
    assert "None" in result.output


@pytest.mark.parametrize("config", configs)
def test_notify_test(config):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    runner = CliRunner()
    # noinspection PyPep8
    result = runner.invoke(notify, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Departed",
        "--test"])

    assert result.exit_code == 0
    assert "TEST MODE" in result.output
    assert "Done" in result.output


@pytest.mark.parametrize("config", configs)
def test_notify_no_fail(config):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # simulate an error -> removing the "number" parameter
    # noinspection PyPep8
    out = subprocess.Popen(
        "aviso notify event=flight,country=Italy,airport=fco,date=20210101",
        shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    stdout, stderr = out.communicate()
    assert out.returncode != 0

    # run the same with the no-fail option -> it should return the error code 0
    # noinspection PyPep8
    out = subprocess.Popen(
        "aviso notify event=flight,country=Italy,airport=fco,date=20210101 --no-fail",
        shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    stdout, stderr = out.communicate()
    assert out.returncode == 0


@pytest.mark.parametrize("config", [c1, c2])
def test_notify_timeout(config):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    port = random.randint(10000, 20000)
    # create a process listening to a port
    out1 = subprocess.Popen(
        f"nc -l {port}", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # set timeout to 2s
    os.environ["AVISO_TIMEOUT"] = "2"
    # run a notify command pointing on port 8099 -> the request will never return
    # noinspection PyPep8
    out2 = subprocess.Popen(
        f"aviso notify event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Departed --port={port}",
        shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    stdout, stderr = out2.communicate()
    if config.notification_engine.type == EngineType.ETCD_REST:
        assert "Read timed out. (read timeout=2)" in stderr.decode()
    elif config.notification_engine.type == EngineType.ETCD_GRPC:
        assert "Deadline Exceeded" in stderr.decode()
    # clean -> remove environment variable
    os.environ.pop("AVISO_TIMEOUT")


@pytest.mark.parametrize("config", [c1, c2])
def test_notify_ttl(config):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])

    runner = CliRunner()
    # noinspection PyPep8
    result = runner.invoke(notify, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Departed,ttl=1"])

    assert result.exit_code == 0
    assert "Done" in result.output

    # now retrieve it
    result = runner.invoke(value, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
    assert result.exit_code == 0
    assert "Departed" in result.output

    # wait for it to expire
    time.sleep(3)

    # now test the value command
    result = runner.invoke(value, [
        "event=flight,country=Italy,airport=fco,date=20210101,number=AZ203"])
    assert result.exit_code == 0
    assert "None" in result.output

