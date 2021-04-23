# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

import pytest

from pyaviso import logger, user_config
from pyaviso.authentication import auth
from pyaviso.engine import engine_factory as ef
from pyaviso.event_listeners import listener_manager
from pyaviso.event_listeners.event_listener import EventListener
from pyaviso.event_listeners.listener_schema_parser import ListenerSchemaParser


@pytest.fixture()
def conf() -> user_config.UserConfig:  # this automatically configure the logging
    c = user_config.UserConfig(conf_path="tests/config.yaml")
    return c


@pytest.fixture()
def schema(conf):
    # Load the schema
    listener_schema = ListenerSchemaParser().load(conf)
    return listener_schema["flight"]


def test_adding_listener(conf, schema):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    aviso = listener_manager.ListenerManager()
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)

    # create a listener that uses that trigger
    eng = engine_factory.create_engine()
    request = {"country": "italy", "date": 20210101}
    listener = EventListener("flight", eng, request, [{"type": "Log"}], schema)

    aviso._add_listener(listener)

    assert aviso.listeners.__len__() == 1


def test_deleting_new_listener(conf, schema):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    aviso = listener_manager.ListenerManager()
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)

    # create a listener that uses that trigger
    eng = engine_factory.create_engine()
    request = {"country": "italy", "date": 20210101}
    listener = EventListener("flight", eng, request, [{"type": "Log"}], schema)

    aviso._add_listener(listener)

    assert aviso.listeners.__len__() == 1

    aviso._cancel_listener(listener)
    assert aviso.listeners.__len__() == 0


def test_adding_listeners(conf, schema):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    aviso = listener_manager.ListenerManager()
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)

    # create a listener that uses that trigger
    eng = engine_factory.create_engine()
    request = {"country": "italy", "date": 20210101}
    listener1 = EventListener("flight", eng, request, [{"type": "Log"}], schema)
    listener2 = EventListener("flight", eng, request, [{"type": "Log"}], schema)

    listeners: list = [listener1, listener2]

    aviso._add_listeners(listeners)

    assert aviso.listeners.__len__() == 2
    # now delete them
    aviso.cancel_listeners()
    assert aviso.listeners.__len__() == 0
