# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import getpass
import os

import pytest

from pyaviso import logger, SYSTEM_FOLDER
from pyaviso.authentication import AuthType
from pyaviso.engine import EngineType
from pyaviso.event_listeners.listener_schema_parser import ListenerSchemaParserType
from pyaviso.user_config import UserConfig, KEY_FILE

test_config_folder = "tests/unit/fixtures/"


@pytest.fixture(autouse=True)
def clear_environment():
    yield
    try:
        os.environ.pop("AVISO_NOTIFICATION_HOST")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_NOTIFICATION_PORT")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_NOTIFICATION_HTTPS")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_NOTIFICATION_CATCHUP")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_NOTIFICATION_SERVICE")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_CONFIGURATION_HOST")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_CONFIGURATION_PORT")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_CONFIGURATION_HTTPS")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_DEBUG")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_NOTIFICATION_ENGINE")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_CONFIGURATION_ENGINE")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_USERNAME")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_KEY_FILE")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_USERNAME_FILE")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_CONFIG")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_QUIET")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_NO_FAIL")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_POLLING_INTERVAL")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_MAX_FILE_SIZE")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_TIMEOUT")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_AUTH_TYPE")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_KEY_TTL")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_REMOTE_SCHEMA")
    except KeyError:
        pass
    try:
        os.environ.pop("AVISO_SCHEMA_PARSER")
    except KeyError:
        pass


def test_default():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    c = UserConfig._create_default_config()
    assert not c["debug"]
    assert c["notification_engine"]["timeout"] == 60
    assert c["notification_engine"]["polling_interval"] == 30
    assert c["notification_engine"]["type"] == "etcd_rest"
    assert c["notification_engine"]["port"] == 2379
    assert c["notification_engine"]["host"] == "localhost"
    assert c["notification_engine"]["service"] == "aviso/v1"
    assert not c["notification_engine"]["https"]
    assert c["notification_engine"]["catchup"]
    assert c["configuration_engine"]["timeout"] == 60
    assert c["configuration_engine"]["port"] == 2379
    assert c["configuration_engine"]["host"] == "localhost"
    assert not c["configuration_engine"]["https"]
    assert c["configuration_engine"]["max_file_size"] == 500
    assert c["configuration_engine"]["type"] == "etcd_rest"
    assert not c["quiet"]
    assert not c["no_fail"]
    assert c["key_file"] == os.path.join(SYSTEM_FOLDER, KEY_FILE)
    assert c["username_file"] is None
    assert c["username"] is None
    assert c["auth_type"] == "none"
    assert c["key_ttl"] == -1
    assert c["schema_parser"] == "generic"
    assert not c["remote_schema"]


def test_config_file():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    c = UserConfig(conf_path=test_config_folder + "config.yaml")
    assert c.debug
    assert c.notification_engine.polling_interval == 1
    assert c.notification_engine.type == EngineType.ETCD_GRPC
    assert c.configuration_engine.type == EngineType.ETCD_GRPC
    assert c.auth_type == AuthType.ETCD
    assert c.username == "root"
    assert c.username_file is None
    assert c.notification_engine.port == 8080
    assert c.notification_engine.host == "test"
    assert c.notification_engine.https
    assert c.notification_engine.catchup
    assert c.notification_engine.service == "aviso/v2"
    assert c.configuration_engine.https
    assert c.notification_engine.timeout == 30
    assert c.configuration_engine.port == 8080
    assert c.configuration_engine.host == "test"
    assert c.configuration_engine.max_file_size == 500
    assert c.configuration_engine.timeout is None
    assert c.quiet
    assert c.no_fail
    assert c.key_ttl == 10
    assert c.remote_schema
    assert c.schema_parser == ListenerSchemaParserType.ECMWF


def test_config_file_with_ev():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    os.environ["AVISO_CONFIG"] = test_config_folder + "config.yaml"
    c = UserConfig()
    assert c.debug
    assert c.notification_engine.polling_interval == 1
    assert c.notification_engine.type == EngineType.ETCD_GRPC
    assert c.configuration_engine.type == EngineType.ETCD_GRPC
    assert c.auth_type == AuthType.ETCD
    assert c.username == "root"
    assert c.username_file is None
    assert c.notification_engine.port == 8080
    assert c.notification_engine.host == "test"
    assert c.notification_engine.timeout == 30
    assert c.notification_engine.https
    assert c.notification_engine.catchup
    assert c.notification_engine.service == "aviso/v2"
    assert c.configuration_engine.https
    assert c.configuration_engine.port == 8080
    assert c.configuration_engine.host == "test"
    assert c.configuration_engine.max_file_size == 500
    assert c.configuration_engine.timeout is None
    assert c.quiet
    assert c.no_fail
    assert c.key_ttl == 10
    assert c.remote_schema
    assert c.schema_parser == ListenerSchemaParserType.ECMWF


def test_env_variables():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    os.environ["AVISO_NOTIFICATION_HOST"] = "test_env"
    os.environ["AVISO_NOTIFICATION_PORT"] = "3"
    os.environ["AVISO_NOTIFICATION_HTTPS"] = "True"
    os.environ["AVISO_NOTIFICATION_CATCHUP"] = "False"
    os.environ["AVISO_NOTIFICATION_ENGINE"] = "ETCD_GRPC"
    os.environ["AVISO_NOTIFICATION_HTTPS"] = "True"
    os.environ["AVISO_NOTIFICATION_SERVICE"] = "aviso/v3"
    os.environ["AVISO_CONFIGURATION_HTTPS"] = "True"
    os.environ["AVISO_CONFIGURATION_ENGINE"] = "ETCD_GRPC"
    os.environ["AVISO_CONFIGURATION_HOST"] = "test_env"
    os.environ["AVISO_CONFIGURATION_PORT"] = "3"
    os.environ["AVISO_DEBUG"] = "True"
    os.environ["AVISO_QUIET"] = "True"
    os.environ["AVISO_NO_FAIL"] = "True"
    os.environ["AVISO_USERNAME"] = "test_env"
    os.environ["AVISO_KEY_FILE"] = "tests/unit/fixtures/bad/key"
    os.environ["AVISO_POLLING_INTERVAL"] = "3"
    os.environ["AVISO_MAX_FILE_SIZE"] = "300"
    os.environ["AVISO_TIMEOUT"] = "null"
    os.environ["AVISO_AUTH_TYPE"] = "etcd"
    os.environ["AVISO_KEY_TTL"] = "20"
    os.environ["AVISO_USERNAME_FILE"] = "tests/unit/fixtures/username"
    os.environ["AVISO_REMOTE_SCHEMA"] = "true"
    os.environ["AVISO_SCHEMA_PARSER"] = "ecmwf"

    # create a config with the configuration file but the environment variables take priority
    c = UserConfig()
    assert c.debug
    assert c.notification_engine.polling_interval == 3
    assert c.notification_engine.type == EngineType.ETCD_GRPC
    assert c.configuration_engine.type == EngineType.ETCD_GRPC
    assert c.auth_type == AuthType.ETCD
    assert c.username == "test_user"
    assert c.username_file == "tests/unit/fixtures/username"
    assert c.notification_engine.port == 3
    assert c.notification_engine.host == "test_env"
    assert c.notification_engine.timeout is None
    assert c.notification_engine.https
    assert not c.notification_engine.catchup
    assert c.notification_engine.service == "aviso/v3"
    assert c.configuration_engine.https
    assert c.configuration_engine.port == 3
    assert c.configuration_engine.host == "test_env"
    assert c.configuration_engine.max_file_size == 300
    assert c.configuration_engine.timeout is None
    assert c.quiet
    assert c.no_fail
    assert c.key_ttl == 20
    assert c.remote_schema
    assert c.schema_parser == ListenerSchemaParserType.ECMWF


def test_env_variables_with_config_file():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    os.environ["AVISO_NOTIFICATION_HOST"] = "test_env"
    os.environ["AVISO_NOTIFICATION_PORT"] = "3"
    os.environ["AVISO_NOTIFICATION_HTTPS"] = "False"
    os.environ["AVISO_NOTIFICATION_CATCHUP"] = "False"
    os.environ["AVISO_NOTIFICATION_SERVICE"] = "aviso/v3"
    os.environ["AVISO_CONFIGURATION_HTTPS"] = "False"
    os.environ["AVISO_CONFIGURATION_HOST"] = "test_env"
    os.environ["AVISO_CONFIGURATION_PORT"] = "3"
    os.environ["AVISO_DEBUG"] = "False"
    os.environ["AVISO_QUIET"] = "False"
    os.environ["AVISO_NO_FAIL"] = "False"
    os.environ["AVISO_USERNAME"] = "test_env"
    os.environ["AVISO_KEY_FILE"] = "tests/unit/fixtures/bad/key"
    os.environ["AVISO_NOTIFICATION_ENGINE"] = "ETCD_GRPC"
    os.environ["AVISO_CONFIGURATION_ENGINE"] = "ETCD_GRPC"
    os.environ["AVISO_POLLING_INTERVAL"] = "3"
    os.environ["AVISO_MAX_FILE_SIZE"] = "300"
    os.environ["AVISO_TIMEOUT"] = "20"
    os.environ["AVISO_AUTH_TYPE"] = "ecmwf"
    os.environ["AVISO_KEY_TTL"] = "20"
    os.environ["AVISO_REMOTE_SCHEMA"] = "false"
    os.environ["AVISO_SCHEMA_PARSER"] = "generic"

    # create a config with the configuration file but the environment variables take priority
    c = UserConfig(conf_path=test_config_folder + "config.yaml")

    assert not c.debug
    assert c.notification_engine.polling_interval == 3
    assert c.notification_engine.type == EngineType.ETCD_GRPC
    assert c.configuration_engine.type == EngineType.ETCD_GRPC
    assert c.auth_type == AuthType.ECMWF
    assert c.username == "test_env"
    assert c.username_file is None
    assert c.notification_engine.port == 3
    assert c.notification_engine.host == "test_env"
    assert c.notification_engine.timeout == 20
    assert c.notification_engine.service == "aviso/v3"
    assert not c.notification_engine.https
    assert not c.notification_engine.catchup
    assert not c.configuration_engine.https
    assert c.configuration_engine.port == 3
    assert c.configuration_engine.host == "test_env"
    assert c.configuration_engine.max_file_size == 300
    assert c.configuration_engine.timeout == 20
    assert not c.quiet
    assert not c.no_fail
    assert c.key_ttl == 20
    assert not c.remote_schema
    assert c.schema_parser == ListenerSchemaParserType.GENERIC


def test_constructor():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    # create a config with passing the configuration file as well as the parameters. The parameters will take priority
    notification_engine = {"host": "localhost", "port": 2379, "type": "ETCD_REST", "polling_interval": 60,
                           "timeout": 10, "https": False, "service": "aviso/v4", "catchup": False}
    configuration_engine = {"host": "localhost", "port": 2379, "type": "ETCD_REST", "max_file_size": 200, "timeout": 10,
                            "https": False}

    c = UserConfig(
        conf_path=test_config_folder + "config.yaml",
        notification_engine=notification_engine,
        configuration_engine=configuration_engine,
        debug=False,
        no_fail=False,
        quiet=False,
        username="test2",
        key_file="tests/unit/fixtures/bad/key",
        auth_type="ecmwf",
        key_ttl=30,
        remote_schema=True,
        schema_parser="ecmwf"

    )
    assert not c.debug
    assert c.notification_engine.polling_interval == 60
    assert c.notification_engine.type == EngineType.ETCD_REST
    assert c.configuration_engine.type == EngineType.ETCD_REST
    assert c.auth_type == AuthType.ECMWF
    assert c.username == "test2"
    assert c.username_file is None
    assert c.notification_engine.port == 2379
    assert c.notification_engine.host == "localhost"
    assert c.notification_engine.timeout == 10
    assert c.notification_engine.service == "aviso/v4"
    assert not c.notification_engine.https
    assert not c.notification_engine.catchup
    assert not c.configuration_engine.https
    assert c.configuration_engine.port == 2379
    assert c.configuration_engine.host == "localhost"
    assert c.configuration_engine.max_file_size == 200
    assert c.configuration_engine.timeout == 10
    assert not c.quiet
    assert not c.no_fail
    assert c.key_ttl == 30
    assert c.remote_schema
    assert c.schema_parser == ListenerSchemaParserType.ECMWF


def test_constructor_with_env_var():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    os.environ["AVISO_NOTIFICATION_HOST"] = "test_env"
    os.environ["AVISO_NOTIFICATION_PORT"] = "3"
    os.environ["AVISO_NOTIFICATION_HTTPS"] = "True"
    os.environ["AVISO_NOTIFICATION_CATCHUP"] = "True"
    os.environ["AVISO_NOTIFICATION_SERVICE"] = "aviso/v3"
    os.environ["AVISO_CONFIGURATION_HTTPS"] = "True"
    os.environ["AVISO_CONFIGURATION_HOST"] = "test_env"
    os.environ["AVISO_CONFIGURATION_PORT"] = "3"
    os.environ["AVISO_DEBUG"] = "True"
    os.environ["AVISO_QUIET"] = "True"
    os.environ["AVISO_NO_FAIL"] = "True"
    os.environ["AVISO_USERNAME"] = "test_env"
    os.environ["AVISO_KEY_FILE"] = "tests/unit/fixtures/bad/key"
    os.environ["AVISO_NOTIFICATION_ENGINE"] = "ETCD_GRPC"
    os.environ["AVISO_CONFIGURATION_ENGINE"] = "ETCD_GRPC"
    os.environ["AVISO_POLLING_INTERVAL"] = "3"
    os.environ["AVISO_MAX_FILE_SIZE"] = "300"
    os.environ["AVISO_TIMEOUT"] = "20"
    os.environ["AVISO_AUTH_TYPE"] = "etcd"
    os.environ["AVISO_KEY_TTL"] = "20"
    os.environ["AVISO_USERNAME_FILE"] = "tests/unit/fixtures/username"
    os.environ["AVISO_REMOTE_SCHEMA"] = "false"
    os.environ["AVISO_SCHEMA_PARSER"] = "generic"

    # create a config with passing the configuration file as well as the parameters. The parameters will take priority
    notification_engine = {"host": "localhost", "port": 2379, "type": "ETCD_REST", "polling_interval": 60,
                           "timeout": 10, "https": False, "service": "aviso/v4", "catchup": False}
    configuration_engine = {"host": "localhost", "port": 2379, "type": "ETCD_REST", "max_file_size": 200, "timeout": 10,
                            "https": False}

    c = UserConfig(
        conf_path=test_config_folder + "config.yaml",
        notification_engine=notification_engine,
        configuration_engine=configuration_engine,
        debug=False,
        quiet=False,
        no_fail=False,
        username="test2",
        key_file="tests/unit/fixtures/key",
        auth_type="ecmwf",
        key_ttl=30,
        remote_schema=True,
        schema_parser="ecmwf"
    )
    assert not c.debug
    assert c.notification_engine.polling_interval == 60
    assert c.notification_engine.type == EngineType.ETCD_REST
    assert c.configuration_engine.type == EngineType.ETCD_REST
    assert c.auth_type == AuthType.ECMWF
    assert c.username == "test_user"
    assert c.username_file == "tests/unit/fixtures/username"
    assert c.notification_engine.port == 2379
    assert c.notification_engine.host == "localhost"
    assert c.notification_engine.timeout == 10
    assert c.notification_engine.service == "aviso/v4"
    assert not c.notification_engine.https
    assert not c.notification_engine.catchup
    assert not c.configuration_engine.https
    assert c.configuration_engine.port == 2379
    assert c.configuration_engine.host == "localhost"
    assert c.configuration_engine.max_file_size == 200
    assert c.configuration_engine.timeout == 10
    assert not c.quiet
    assert not c.no_fail
    assert c.key_ttl == 30
    assert c.remote_schema
    assert c.schema_parser == ListenerSchemaParserType.ECMWF
