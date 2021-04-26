# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import atexit
import collections.abc
import logging
import logging.config
import logging.handlers
import os
import re
import sys
from typing import Dict, Optional

import yaml

from . import HOME_FOLDER, SYSTEM_FOLDER, logger
from .authentication import AuthType
from .engine import EngineType
from .event_listeners.listener_schema_parser import ListenerSchemaParserType

# Default configuration location
CONF_FILE = "config.yaml"
KEY_FILE = "key"


class EngineConfig:
    def __init__(
        self,
        host: str,
        port: int,
        type: str,
        polling_interval: Optional[int] = None,
        max_file_size: Optional[int] = None,
        timeout: Optional[int] = None,
        service: Optional[str] = None,
        https: bool = False,
        catchup: Optional[bool] = None,
        automatic_retry_delay: Optional[int] = None,
    ):
        """
        :param host: endpoint host of the notification server
        :param port: endpoint port of the notification server
        :param type: interface to use to communicate to the notification and configuration servers
        :param polling_interval: interval between consecutive requests for new notifications, in seconds
        :param max_file_size: max file size allowed to push to the configuration server, in KiB
        :param timeout: number of seconds of waiting before timing-out the request to the server
        :param service: location in the configuration server associated to the notification service
        for the event listeners validation
        :param https: if True the connection will go through HTTPS
        :param catchup: if True the notification engine will first look for the missed notifications
        :param automatic_retry_delay: Number of seconds to wait before retrying to connect to the engine
        """
        self.host = host
        self.port = port
        self.type = EngineType[type.upper()]
        self.polling_interval = polling_interval
        self.max_file_size = max_file_size
        self.timeout = timeout
        self.https = https
        self.service = service
        self.catchup = catchup
        self.automatic_retry_delay = automatic_retry_delay

    def __str__(self):
        config_string = (
            f"host: {self.host}"
            + f", port: {self.port}"
            + f", https: {self.https}"
            + f", type: {self.type.name}"
            + f", polling_interval: {self.polling_interval}"
            + f", timeout: {self.timeout}"
            + f", max_file_size: {self.max_file_size}"
            + f", service: {self.service}"
            + f", catchup: {self.catchup}"
            + f", automatic_retry_delay: {self.automatic_retry_delay}"
        )
        return config_string


class UserConfig:
    """
    This class is in charge of holding the user configuration, which can be defined by command line options,
    environment variables, configuration files or defaults.
    """

    def __init__(
        self,
        conf_path: Optional[str] = None,
        conf_from_file: Optional[Dict[str, any]] = None,
        logging_path: Optional[str] = None,
        notification_engine: Optional[Dict[str, any]] = None,
        configuration_engine: Optional[Dict[str, any]] = None,
        debug: Optional[bool] = None,
        quiet: Optional[bool] = None,
        no_fail: Optional[bool] = None,
        username: Optional[str] = None,
        username_file: Optional[str] = None,
        key_file: Optional[str] = None,
        auth_type: Optional[str] = None,
        key_ttl: Optional[int] = None,
        schema_parser: Optional[str] = None,
        remote_schema: Optional[bool] = None,
        listeners: Optional[Dict[str, any]] = None,
    ):
        """
        :param conf_path: path to the system configuration file. If not provided,
        the default location is HOME_FOLDER/config.yaml.
        :param conf_from_file: system configuration dictionary. This will be treated as if read from file, in the same
        priority order.
        :param logging_path: path to the logging configuration file. If not provided,
        the default location is the logging section of the HOME_FOLDER/config.yaml.
        :param notification_engine: configuration object for the notification server
        :param configuration_engine: configuration object for the configuration server
        :param debug: flag to activate the debug log to the console output
        :param quiet: flag to activate only warning and error log to the console output
        :param no_fail: flag to suppress any error exit code
        :param username: username required to authenticate to the notification and configuration servers
        :param username_file: file path containing the username required to authenticate the user
        :param key_file: file path to the key required to authenticate to the notification and configuration servers
        :param auth_type: Authentication type
        :param key_ttl: Time to live of the keys submitted
        :param schema_parser: parser to use to build the listener schema
        :param remote_schema: flag to activate the dynamic retrieval of the listener schema from the configuration
        server
        :param listeners: listeners configuration
        """
        try:
            # we build the configuration in priority order from the lower to the higher
            # start from the defaults
            self._config = self._create_default_config()

            # add the configuration files
            if conf_from_file:  # only one method is allowed
                UserConfig.deep_update(self._config, conf_from_file)
            else:
                UserConfig.deep_update(self._config, self._parse_config_files(conf_path))

            # initialise logger, this needs to be done ASAP
            self.logging_setup(logging_path)

            # add environment variables
            UserConfig.deep_update(self._config, self._read_env_variables())

            # add constructor parameters
            self.notification_engine = notification_engine
            self.configuration_engine = configuration_engine
            self.debug = debug
            self.quiet = quiet
            self.no_fail = no_fail
            self.username = username
            self.username_file = username_file
            self.auth_type = auth_type
            if self.auth_type != AuthType.NONE:
                self.key_file = key_file
                self.password = self._read_key()
                if self.username_file:
                    self.username = self._read_username_file()
            self.key_ttl = key_ttl
            self.schema_parser = schema_parser
            self.remote_schema = remote_schema
            self.listeners = listeners

            logger.debug("Loading configuration completed")

        except Exception as e:
            logger.error(f"Error occurred while setting the configuration, {type(e)}, {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @staticmethod
    def _create_default_config() -> Dict[str, any]:
        # notification engine
        notification_engine = {}
        notification_engine["host"] = "localhost"
        notification_engine["port"] = 2379
        notification_engine["https"] = False
        notification_engine["type"] = "etcd_rest"
        notification_engine["polling_interval"] = 30  # seconds
        notification_engine["timeout"] = 60  # seconds
        notification_engine["service"] = "aviso/v1"
        notification_engine["catchup"] = True
        notification_engine["automatic_retry_delay"] = 15  # seconds

        # configuration engine
        configuration_engine = {}
        configuration_engine["host"] = "localhost"
        configuration_engine["port"] = 2379
        configuration_engine["https"] = False
        configuration_engine["type"] = "etcd_rest"
        configuration_engine["max_file_size"] = 500  # KiB
        configuration_engine["timeout"] = 60  # seconds
        configuration_engine["automatic_retry_delay"] = 15  # seconds

        # main config
        config = {}
        config["notification_engine"] = notification_engine
        config["configuration_engine"] = configuration_engine
        config["username"] = None
        config["username_file"] = None
        config["debug"] = False
        config["quiet"] = False
        config["no_fail"] = False
        config["key_file"] = os.path.join(SYSTEM_FOLDER, KEY_FILE)
        config["auth_type"] = "none"
        config["key_ttl"] = -1  # not expiring
        config["schema_parser"] = "generic"
        config["remote_schema"] = False
        return config

    def _read_key(self) -> str:
        assert self.key_file is not None, "Key file not found"
        full_key_path = os.path.expanduser(self.key_file)
        try:
            with open(full_key_path, "r") as k:
                return k.read().rstrip()
        except FileNotFoundError as e:
            logger.error(f"Not able to load the key file: {full_key_path},  {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    def _read_username_file(self) -> str:
        assert self.username_file is not None, "Username file not found"
        full_username_path = os.path.expanduser(self.username_file)
        try:
            with open(full_username_path, "r") as u:
                return u.read().rstrip()
        except FileNotFoundError as e:
            logger.error(f"Not able to load the username file: {full_username_path},  {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    def _parse_config_files(self, user_conf_path: str) -> Dict[str, any]:
        # build the configuration dictionary from system and user inputs
        current_config = {}

        def parse_config(file_path: str):
            try:
                with open(file_path, "r") as f:
                    config = yaml.load(f.read(), Loader=HomeFolderLoader)
                # merge with the current config
                UserConfig.deep_update(current_config, config)
            except Exception as e:
                logger.error(f"Not able to load the configuration in {file_path},  {e}")
                logger.debug("", exc_info=True)
                sys.exit(-1)

        # First the system config file
        system_path = os.path.join(SYSTEM_FOLDER, CONF_FILE)
        # Check the directory exist
        if os.path.exists(system_path):
            parse_config(system_path)
        else:
            logger.debug(f"Configuration in {system_path} not found")

        # Second the Home config file
        home_path = os.path.join(os.path.expanduser(HOME_FOLDER), CONF_FILE)
        # Check the directory exist
        if os.path.exists(home_path):
            parse_config(home_path)
        else:
            logger.debug(f"Configuration in {home_path} not found")

        # Third the env variable
        if "AVISO_CONFIG" in os.environ:
            env_path = os.environ["AVISO_CONFIG"]
            parse_config(env_path)

        # Finally the user config option
        if user_conf_path:
            parse_config(user_conf_path)

        return current_config

    def _read_env_variables(self) -> Dict[str, any]:
        config = {"notification_engine": {}, "configuration_engine": {}}
        if "AVISO_NOTIFICATION_HOST" in os.environ:
            config["notification_engine"]["host"] = os.environ["AVISO_NOTIFICATION_HOST"]
        if "AVISO_NOTIFICATION_PORT" in os.environ:
            config["notification_engine"]["port"] = int(os.environ["AVISO_NOTIFICATION_PORT"])
        if "AVISO_NOTIFICATION_HTTPS" in os.environ:
            config["notification_engine"]["https"] = os.environ["AVISO_NOTIFICATION_HTTPS"]
        if "AVISO_NOTIFICATION_ENGINE" in os.environ:
            config["notification_engine"]["type"] = os.environ["AVISO_NOTIFICATION_ENGINE"]
        if "AVISO_NOTIFICATION_SERVICE" in os.environ:
            config["notification_engine"]["service"] = os.environ["AVISO_NOTIFICATION_SERVICE"]
        if "AVISO_NOTIFICATION_CATCHUP" in os.environ:
            config["notification_engine"]["catchup"] = os.environ["AVISO_NOTIFICATION_CATCHUP"]
        if "AVISO_POLLING_INTERVAL" in os.environ:
            config["notification_engine"]["polling_interval"] = int(os.environ["AVISO_POLLING_INTERVAL"])
        if "AVISO_CONFIGURATION_HOST" in os.environ:
            config["configuration_engine"]["host"] = os.environ["AVISO_CONFIGURATION_HOST"]
        if "AVISO_CONFIGURATION_PORT" in os.environ:
            config["configuration_engine"]["port"] = int(os.environ["AVISO_CONFIGURATION_PORT"])
        if "AVISO_CONFIGURATION_HTTPS" in os.environ:
            config["configuration_engine"]["https"] = os.environ["AVISO_CONFIGURATION_HTTPS"]
        if "AVISO_CONFIGURATION_ENGINE" in os.environ:
            config["configuration_engine"]["type"] = os.environ["AVISO_CONFIGURATION_ENGINE"]
        if "AVISO_MAX_FILE_SIZE" in os.environ:
            config["configuration_engine"]["max_file_size"] = int(os.environ["AVISO_MAX_FILE_SIZE"])
        if "AVISO_USERNAME" in os.environ:
            config["username"] = os.environ["AVISO_USERNAME"]
        if "AVISO_USERNAME_FILE" in os.environ:
            config["username_file"] = os.environ["AVISO_USERNAME_FILE"]
        if "AVISO_DEBUG" in os.environ:
            config["debug"] = os.environ["AVISO_DEBUG"]
        if "AVISO_QUIET" in os.environ:
            config["quiet"] = os.environ["AVISO_QUIET"]
        if "AVISO_NO_FAIL" in os.environ:
            config["no_fail"] = os.environ["AVISO_NO_FAIL"]
        if "AVISO_KEY_FILE" in os.environ:
            config["key_file"] = os.environ["AVISO_KEY_FILE"]
        if "AVISO_KEY_TTL" in os.environ:
            config["key_ttl"] = int(os.environ["AVISO_KEY_TTL"])
        if "AVISO_AUTH_TYPE" in os.environ:
            config["auth_type"] = os.environ["AVISO_AUTH_TYPE"]
        if "AVISO_REMOTE_SCHEMA" in os.environ:
            config["remote_schema"] = os.environ["AVISO_REMOTE_SCHEMA"]
        if "AVISO_SCHEMA_PARSER" in os.environ:
            config["schema_parser"] = os.environ["AVISO_SCHEMA_PARSER"]
        if "AVISO_TIMEOUT" in os.environ:  # one variable for both engine
            timeout = None if os.environ["AVISO_TIMEOUT"] == "null" else int(os.environ["AVISO_TIMEOUT"])
            config["notification_engine"]["timeout"] = timeout
            config["configuration_engine"]["timeout"] = timeout
        if "AVISO_AUTOMATIC_RETRY_DELAY" in os.environ:  # one variable for both engine
            automatic_retry_delay = (
                None
                if os.environ["AVISO_AUTOMATIC_RETRY_DELAY"] == "null"
                else int(os.environ["AVISO_AUTOMATIC_RETRY_DELAY"])
            )
            config["notification_engine"]["automatic_retry_delay"] = automatic_retry_delay
            config["configuration_engine"]["automatic_retry_delay"] = automatic_retry_delay
        return config

    def logging_setup(self, logging_conf_path: str):

        if logging_conf_path is not None:
            try:
                with open(logging_conf_path, "r") as f:
                    log_config = yaml.safe_load(f.read())
            except Exception as e:
                logger.warning(f"Not able to load the logging configuration,  {e}")
                logger.debug("", exc_info=True)
                sys.exit(-1)
        elif "AVISO_LOG" in os.environ:
            try:
                with open(os.environ["AVISO_LOG"], "r") as f:
                    log_config = yaml.safe_load(f.read())
            except Exception as e:
                logger.warning(f"Not able to load the logging configuration,  {e}")
                logger.debug("", exc_info=True)
                sys.exit(-1)
        elif self._config is not None and self._config.get("logging") is not None:
            # Setting logging from user configuration file
            log_config = self._config.get("logging")
        else:  # Defaults
            # Configure the logging with the default configuration
            self._configure_default_log()
            return

        # initialise the logging with the user configuration
        try:
            logging.config.dictConfig(log_config)
        except Exception as e:
            logger.warning(f"Not able to load the logging configuration, {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @property
    def notification_engine(self) -> EngineConfig:
        return self._notification_engine

    @notification_engine.setter
    def notification_engine(self, notification_engine: Dict[str, any]):
        ne = self._config.get("notification_engine")
        if notification_engine is not None and ne is not None:
            UserConfig.deep_update(ne, notification_engine)
        elif notification_engine is not None:
            ne = notification_engine
        # verify is valid
        assert ne is not None, "notification_engine has not been configured"
        assert "host" in ne, "notification_engine host has not been configured"
        assert "port" in ne, "notification_engine port has not been configured"
        assert "type" in ne, "notification_engine type has not been configured"
        assert "https" in ne, "notification_engine https has not been configured"
        assert "service" in ne, "notification_engine service has not been configured"
        assert "catchup" in ne, "notification_engine catchup has not been configured"
        assert "automatic_retry_delay" in ne, "notification_engine automatic_retry_delay has not been configured"
        assert "polling_interval" in ne, "notification_engine polling_interval has not been configured"
        assert "timeout" in ne, "notification_engine timeout has not been configured"
        if type(ne["https"]) is str:
            ne["https"] = ne["https"].casefold() == "true".casefold()
        if type(ne["catchup"]) is str:
            ne["catchup"] = ne["catchup"].casefold() == "true".casefold()

        # translate the ne in a NotificationEngineConfig
        self._notification_engine = EngineConfig(
            ne["host"],
            ne["port"],
            ne["type"],
            polling_interval=ne["polling_interval"],
            timeout=ne["timeout"],
            https=ne["https"],
            service=ne["service"],
            catchup=ne["catchup"],
            automatic_retry_delay=ne["automatic_retry_delay"],
        )

    @property
    def configuration_engine(self) -> EngineConfig:
        return self._configuration_engine

    @configuration_engine.setter
    def configuration_engine(self, configuration_engine: Dict[str, any]):
        ce = self._config.get("configuration_engine")
        if configuration_engine is not None and ce is not None:
            UserConfig.deep_update(ce, configuration_engine)
        elif configuration_engine is not None:
            ce = configuration_engine
        # verify is valid
        assert ce is not None, "configuration_engine has not been configured"
        assert "host" in ce, "configuration_engine host has not been configured"
        assert "port" in ce, "configuration_engine port has not been configured"
        assert "type" in ce, "configuration_engine type has not been configured"
        assert "https" in ce, "configuration_engine https has not been configured"
        assert "max_file_size" in ce, "configuration_engine max_file_size has not been configured"
        assert "timeout" in ce, "configuration_engine timeout has not been configured"
        assert "automatic_retry_delay" in ce, "configuration_engine automatic_retry_delay has not been configured"
        if type(ce["https"]) is str:
            ce["https"] = ce["https"].casefold() == "true".casefold()

        # exclude file_based from the options for the configuration engine
        assert ce["type"].casefold() != "file_based", "File_based engine not available as configuration engine"
        # translate the ce in a ConfigurationEngineConfig
        self._configuration_engine = EngineConfig(
            ce["host"],
            ce["port"],
            ce["type"],
            max_file_size=ce["max_file_size"],
            timeout=ce["timeout"],
            https=ce["https"],
            automatic_retry_delay=ce["automatic_retry_delay"],
        )

    @property
    def schema_parser(self) -> ListenerSchemaParserType:
        return self._schema_parser

    @schema_parser.setter
    def schema_parser(self, schema_parser: str):
        self._schema_parser = ListenerSchemaParserType[self._configure_property(schema_parser, "schema_parser").upper()]

    @property
    def remote_schema(self) -> bool:
        return self._remote_schema

    @remote_schema.setter
    def remote_schema(self, remote_schema: str):
        self._remote_schema = self._configure_property(remote_schema, "remote_schema")
        if type(self._remote_schema) is str:
            self._remote_schema = self._remote_schema.casefold() == "true".casefold()

    @property
    def key_ttl(self):
        return self._key_ttl

    @key_ttl.setter
    def key_ttl(self, key_ttl: int):
        self._key_ttl = self._configure_property(key_ttl, "key_ttl")

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username: str):
        self._username = self._configure_property(username, "username", nullable=True)

    @property
    def username_file(self) -> str:
        return self._username_file

    @username_file.setter
    def username_file(self, username_file: str):
        self._username_file = self._configure_property(username_file, "username_file", nullable=True)

    @property
    def key_file(self) -> str:
        return self._key_file

    @key_file.setter
    def key_file(self, key_file: str):
        self._key_file = self._configure_property(key_file, "key_file")

    @property
    def auth_type(self) -> AuthType:
        return self._auth_type

    @auth_type.setter
    def auth_type(self, auth_type: str):
        self._auth_type = AuthType[self._configure_property(auth_type, "auth_type").upper()]

    @property
    def listeners(self) -> Dict:
        return self._listeners

    @listeners.setter
    def listeners(self, listeners: Dict):
        self._listeners = {"listeners": self._configure_property(listeners, "listeners", nullable=True)}

    @property
    def no_fail(self) -> bool:
        return self._no_fail

    @no_fail.setter
    def no_fail(self, no_fail: str):
        self._no_fail = self._configure_property(no_fail, "no_fail")
        if type(self._no_fail) is str:
            self._no_fail = self._no_fail.casefold() == "true".casefold()
        if self.no_fail:
            # define a function to run at exit
            def suppress_exit_code():
                # override any other exit code and exit
                os._exit(0)

            atexit.register(suppress_exit_code)

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, debug: any):
        self._debug = self._configure_property(debug, "debug")
        if type(self._debug) is str:
            self._debug = self._debug.casefold() == "true".casefold()
        if self._debug:
            logging_level = logging.DEBUG
            # set the root level
            logging.root.setLevel(logging_level)
            # Configuring console logging
            try:
                console = next(h for h in logging.getLogger().handlers if h.name == "console")
                console.setLevel(logging_level)
            except StopIteration:  # this is raised when the console logger could not be found
                # set the general logger - Note this will affect also the logging file
                logging.getLogger().setLevel(logging_level)

    @property
    def quiet(self) -> bool:
        return self._quiet

    @quiet.setter
    def quiet(self, quiet: any):
        self._quiet = self._configure_property(quiet, "quiet")
        if type(self._quiet) is str:
            self._quiet = self._quiet.casefold() == "true".casefold()
        if self._quiet:
            logging_level = logging.ERROR
            # Configuring console logging
            try:
                console = next(h for h in logging.getLogger().handlers if h.name == "console")
                console.setLevel(logging_level)
            except StopIteration:  # this is raised when the console logger could not be found
                # ignore it in this case
                pass

    def __str__(self):
        config_string = (
            f"notification_engine: {self.notification_engine}"
            + f", configuration_engine: {self.configuration_engine}"
            + f", auth_type: {self.auth_type}"
            + f", debug: {self.debug}"
            + f", quiet: {self.quiet}"
            + f", username: {self.username}"
            + f", username_file: {self.username_file}"
            + f", no_fail: {self.no_fail}"
            + f", key_ttl: {self.key_ttl}"
            + f", schema_parser: {self.schema_parser}"
            + f", remote_schema: {self.remote_schema}"
        )
        return config_string

    def _configure_default_log(self):
        try:
            next(h for h in logging.getLogger().handlers if h.name == "console")
            # don't do anything, we already have a console handler
        except StopIteration:  # this is raised when the console logger could not be found
            # creating default console handler
            console_handler = logging.StreamHandler()
            console_handler.name = "console"
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter("%(message)s"))
            logging.getLogger().addHandler(console_handler)

    def _configure_property(self, param, name, nullable=False):
        value = None
        if param is not None:
            value = param
        elif self._config.get(name) is not None:
            # Setting var from user configuration file
            value = self._config.get(name)
        else:
            if not nullable:
                logger.error(f"{name} has not been configured")
                sys.exit(-1)
        return value

    @staticmethod
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, collections.abc.Mapping):
                d[k] = UserConfig.deep_update(d.get(k, type(v)()), v)
            else:
                d[k] = v
        return d


# class to allow yaml loader to replace ~ with HOME directory
class HomeFolderLoader(yaml.SafeLoader):
    path_matcher = re.compile("~")

    @staticmethod
    def path_constructor(loader, node):
        return os.path.expanduser(node.value)


HomeFolderLoader.add_implicit_resolver("!path", HomeFolderLoader.path_matcher, None)
HomeFolderLoader.add_constructor("!path", HomeFolderLoader.path_constructor)
