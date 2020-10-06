# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

import pytest
import yaml

from pyaviso import user_config, logger
from pyaviso.authentication import auth
from pyaviso.engine import engine_factory as ef
from pyaviso.event_listeners import event_listener_factory as elf
from pyaviso.notification_manager import NotificationManager


@pytest.fixture()
def conf() -> user_config.UserConfig:  # this automatically configure the logging
    c = user_config.UserConfig(conf_path="tests/config.yaml")
    return c


@pytest.fixture()
def schema(conf):
    # Load the schema
    aviso = NotificationManager()
    listener_schema = aviso._latest_listener_schema(conf)
    return listener_schema


def test_empty_file(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/empty.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners = listener_factory.create_listeners(listeners_dict)
    except AssertionError as e:
        assert e.args[0] == "Event listeners definition cannot be empty"


def test_no_listeners(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/noListeners.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except AssertionError as e:
        assert e.args[0] == "Event listeners definition must start with the keyword 'listeners'"


def test_no_destination(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/noDestination.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except KeyError as e:
        assert e.args[0] == "Wrong listener file: destination required"


def test_bad_tree_structure(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/badTree.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except AssertionError as e:
        assert e.args[0] == "Wrong file structure"


def test_bad_attribute(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/badAttribute.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except AssertionError as e:
        assert e.args[0] == "Key day is not allowed"


def test_bad_format(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/badFormat.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except ValueError as e:
        assert e.args[0] == "Value one is not valid for key step"


def test_no_trigger(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/noTrigger.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except AssertionError as e:
        assert e.args[0] == "At least one trigger must be defined"


def test_bad_trigger_type(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/badTriggerType.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except KeyError as e:
        assert e.args[0] == "Trigger type logger not recognised"


def test_bad_trigger(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/bad/badTrigger.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    try:
        listeners: list = listener_factory.create_listeners(listeners_dict)
    except AssertionError as e:
        assert e.args[0] == "'type' is a mandatory field in trigger"


def test_single_listener_complete(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/completeDisseminationListener.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    listeners: list = listener_factory.create_listeners(listeners_dict)
    assert listeners.__len__() == 1
    listener = listeners.pop()
    assert listener.keys is not None
    assert listener.keys[0]  # this will fail if the path was an empty string


def test_single_listener_dissemination(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/disseminationListener.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    listeners: list = listener_factory.create_listeners(listeners_dict)
    assert listeners.__len__() == 1
    listener = listeners.pop()
    assert listener.keys is not None
    assert listener.keys[0]  # this will fail if the path was an empty string


def test_multiple_listener(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/multipleListeners.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    listeners: list = listener_factory.create_listeners(listeners_dict)
    assert listeners.__len__() == 3
    for listener in listeners:
        assert listener.keys is not None
        assert listener.keys[0]  # this will fail if the path was an empty string


def test_mars_listener(conf: user_config.UserConfig, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create the notification listener factory
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)
    listener_factory = elf.EventListenerFactory(engine_factory, schema)
    # open the listener yaml file
    with open("tests/unit/fixtures/marsListener.yaml", "r") as f:
        listeners_dict = yaml.safe_load(f.read())
    # parse it
    listeners: list = listener_factory.create_listeners(listeners_dict)
    assert listeners.__len__() == 1
    listener = listeners.pop()
    assert listener.keys is not None
    assert listener.keys[0]
