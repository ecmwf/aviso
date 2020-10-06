# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

import pytest

from pyaviso import user_config, logger
from pyaviso.authentication import auth
from pyaviso.engine import engine_factory as ef
from pyaviso.event_listeners import listener_manager
from pyaviso.event_listeners.dissemination_event_listener import DisseminationEventListener
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
    return listener_schema['dissemination']


def test_adding_listener(conf, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    aviso = listener_manager.ListenerManager()
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)

    # create a listener that uses that trigger
    eng = engine_factory.create_engine()
    request = {"destination": "FOO", "stream": "enfo", "date": "20190810", "time": 0}
    listener = DisseminationEventListener(eng, request, [{"type": "Log"}], schema)

    aviso._add_listener(listener)

    assert aviso.listeners.__len__() == 1


def test_deleting_new_listener(conf, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    aviso = listener_manager.ListenerManager()
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)

    # create a listener that uses that trigger
    eng = engine_factory.create_engine()
    request = {"destination": "FOO", "stream": "enfo", "date": "20190810", "time": 0}
    listener = DisseminationEventListener(eng, request, [{"type": "Log"}], schema)

    aviso._add_listener(listener)

    assert aviso.listeners.__len__() == 1

    aviso._cancel_listener(listener)
    assert aviso.listeners.__len__() == 0


def test_adding_listeners(conf, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    aviso = listener_manager.ListenerManager()
    authenticator = auth.Auth.get_auth(conf)
    engine_factory: ef.EngineFactory = ef.EngineFactory(conf.notification_engine, authenticator)

    # create a listener that uses that trigger
    eng = engine_factory.create_engine()
    request = {"destination": "FOO", "stream": "enfo", "date": "20190810", "time": 0}
    listener1 = DisseminationEventListener(eng, request, [{"type": "Log"}], schema)
    listener2 = DisseminationEventListener(eng, request, [{"type": "Log"}], schema)

    listeners: list = [listener1, listener2]

    aviso._add_listeners(listeners)

    assert aviso.listeners.__len__() == 2
    # now delete them
    aviso.cancel_listeners()
    assert aviso.listeners.__len__() == 0


def test_schema_mars_update(conf, schema):
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # check the enums are in it
    assert 'values' in schema['request']['class'][0]
    class_enums = schema['request']['class'][0]['values']
    assert len(class_enums) > 0
    assert 'austria' in class_enums
