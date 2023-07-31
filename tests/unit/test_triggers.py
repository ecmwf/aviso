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
from threading import Thread

import pytest
import yaml
from flask import Flask, request

from pyaviso import logger, user_config
from pyaviso.authentication import auth
from pyaviso.engine import engine_factory as ef
from pyaviso.event_listeners import event_listener_factory as elf
from pyaviso.event_listeners.listener_schema_parser import ListenerSchemaParser


@pytest.fixture()
def conf() -> user_config.UserConfig:  # this automatically configure the logging
    c = user_config.UserConfig(conf_path="tests/config.yaml")
    return c


@pytest.fixture()
def listener_factory(conf):
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    # Load the schema
    listener_schema = ListenerSchemaParser().load(conf)
    listener_factory = elf.EventListenerFactory(engine_factory, listener_schema)
    return listener_factory


@contextlib.contextmanager
def caplog_for_logger(caplog):  # this is needed to assert over the logging output
    caplog.clear()
    lo = logging.getLogger()
    lo.addHandler(caplog.handler)
    caplog.handler.setLevel(logging.DEBUG)
    yield
    lo.removeHandler(caplog.handler)


def test_echo_trigger(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/echo_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        # check  the trigger has logged the notification on the system log
        assert (
            "{'date': '20210101', 'country': 'italy', 'airport': 'FCO', 'number': 'AZ203'}, 'payload': 'Landed'}"
            in caplog.text
        )
        assert "Echo Trigger completed" in caplog.text


def test_function_trigger(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    # create a list that increments every time there is a new event
    trigger_list = []

    def trigger_function(notification):
        trigger_list.append(notification["payload"])

    trigger = {"type": "function", "function": trigger_function}

    # create a listener that uses that trigger
    request = {"country": "Italy"}
    listener = {"event": "flight", "request": request, "triggers": [trigger]}
    listeners = {"listeners": [listener]}

    # parse it
    listeners: list = listener_factory.create_listeners(listeners)
    assert listeners.__len__() == 1
    listener = listeners.pop()

    # create independent client to trigger the notification
    listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
    time.sleep(1)
    assert trigger_list.__len__() == 1


def test_logger_listener(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/log_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        # check  the trigger has logged the notification on the system log
        assert "Log Trigger completed" in caplog.text
        # check  the trigger has logged the notification on the log specified
        with open(listener.triggers[0].get("path"), "r") as f:
            assert "Notification received" in f.read()

        # clean up
        if os.path.exists("testLog.log"):
            os.remove("testLog.log")


def test_command_listener(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/command_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Command Trigger completed" in caplog.text


def test_command_json_listener(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/command_json_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Command Trigger completed" in caplog.text


def test_command_json_path_listener(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/command_json_path_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Command Trigger completed" in caplog.text


# test frontend
test_frontend = Flask("Test_Frontend")


@test_frontend.route("/test", methods=["POST"])
def received():
    return f"Received {request.json}"


# test_frontend.run(host="127.0.0.1", port=8001)


def test_post_cloudEventshttp_listener(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/post_cloudEventsHttp_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # start a test frontend to send the notification to
        server = Thread(target=test_frontend.run, daemon=True, kwargs={"host": "127.0.0.1", "port": 8051})
        server.start()
        time.sleep(1)

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Post Trigger completed" in caplog.text
        assert "CloudEvents notification sent successfully" in caplog.text


@pytest.mark.skip  # we don't have a AWS topic available for testing
def test_post_cloudeventsaws_listener(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/post_cloudEventsAws_fifo_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # start a test frontend to send the notification to
        server = Thread(target=test_frontend.run, daemon=True, kwargs={"host": "127.0.0.1", "port": 8051})
        server.start()
        time.sleep(1)

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert "Post Trigger completed" in caplog.text
        assert "AWS topic notification sent successfully" in caplog.text


def test_multiple_nots_echo(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/echo_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # simulate a stream of notifications
        n_nots = 10
        for i in range(0, n_nots):
            listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged twice as there are n_puts notifications
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert caplog.text.count("Echo Trigger completed") == n_nots


def test_multiple_nots_cmd(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/command_listener.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()

        # simulate a stream of notifications
        n_nots = 10
        for i in range(0, n_nots):
            listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the change has been logged twice as there are n_puts notifications
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert caplog.text.count("Command Trigger completed") == n_nots


def test_multiple_listeners(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/multiple_listeners.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 3

        # simulate a notification for all listeners
        for listener in listeners:
            listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

        # check if the changes has been logged
        for record in caplog.records:
            assert record.levelname != "ERROR"
        assert caplog.text.count("Echo Trigger completed") == 3


def test_multiple_triggers(conf, listener_factory, caplog):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    with caplog_for_logger(caplog):  # this allows to assert over the logging output
        # open the listener yaml file
        with open("tests/unit/fixtures/good_listeners/multiple_triggers.yaml", "r") as f:
            listeners_dict = yaml.safe_load(f.read())
        # parse it
        listeners: list = listener_factory.create_listeners(listeners_dict)
        assert listeners.__len__() == 1
        listener = listeners.pop()
        assert listener.triggers.__len__() == 3

        # simulate a notification
        listener.callback("/tmp/aviso/flight/20210101/italy/FCO/AZ203", "Landed")
        time.sleep(1)

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
