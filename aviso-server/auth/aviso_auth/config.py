# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import collections.abc
import logging
import logging.config
import logging.handlers
import os
import re
import sys
import socket
from typing import Dict

import yaml
from aviso_monitoring.collector.config import Config as MonitoringConfig

from . import logger, HOME_FOLDER, SYSTEM_FOLDER

# Default configuration location
CONF_FILE = "config.yaml"


class Config:
    """
    This class is in charge of holding the user configuration, which can be defined by command line options,
    environment variables, configuration files or defaults.
    """

    def __init__(self,
                 conf_path=None,
                 logging_path=None,
                 debug=None,
                 authorisation_server=None,
                 authentication_server=None,
                 backend=None,
                 frontend=None,
                 cache=None,
                 monitoring=None):
        """
        :param conf_path: path to the system configuration file. If not provided,
        the default location is HOME_FOLDER/user_config.yaml.
        :param logging_path: path to the logging configuration file. If not provided,
        the default location is the logging section of the HOME_FOLDER/user_config.yaml.
        :param debug: flag to activate the debug log to the console output
        :param authorisation_server: server used for authorise the requests
        :param authentication_server: server used for authenticate the requests
        :param backend: server used to forward the valid requests
        :param frontend: configuration for the REST frontend
        :param cache: configuration dictionary to initialise Flask cache
        :param monitoring: configuration related to the monitoring of this component
        """
        try:
            # we build the configuration in priority order from the lower to the higher
            # start from the defaults
            self._config = self._create_default_config()
            # add the configuration files
            Config.deep_update(self._config, self._parse_config_files(conf_path))
            # initialise logger, this needs to be done ASAP
            self.logging_setup(logging_path)
            # add environment variables
            Config.deep_update(self._config, self._read_env_variables())
            # add constructor parameters
            self.debug = debug
            self.authorisation_server = authorisation_server
            self.authentication_server = authentication_server
            self.backend = backend
            self.frontend = frontend
            self.cache = cache
            self.monitoring = monitoring

            logger.debug(f"Loading configuration completed")

        except Exception as e:
            logger.error(f"Error occurred while setting the configuration, exception: {type(e)} {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @staticmethod
    def _create_default_config() -> Dict[str, any]:
        # authentication_server
        authentication_server = {}
        authentication_server["url"] = "https://api.ecmwf.int/v1/who-am-i"
        authentication_server["req_timeout"] = 60  # seconds
        authentication_server["cache_timeout"] = 86400  # 1 day in seconds
        authentication_server["monitor"] = False

        # authorisation_server
        authorisation_server = {}
        authorisation_server["url"] = "https://127.0..0.1:8080"
        authorisation_server["req_timeout"] = 60  # seconds
        authorisation_server["cache_timeout"] = 86400  # 1 day in seconds
        authorisation_server["open_keys"] = ["/ec/mars", "/ec/config/aviso"]
        authorisation_server["protected_keys"] = ["/ec/diss"]
        authorisation_server["username"] = None
        authorisation_server["password"] = None
        authorisation_server["monitor"] = False

        # backend
        backend = {}
        backend["url"] = "http://127.0.0.1:2379"
        backend["req_timeout"] = 60  # seconds
        backend["route"] = "/v3/kv/range"
        backend["monitor"] = False

        # frontend
        frontend = {}
        frontend["host"] = "127.0.0.1"
        frontend["port"] = 8080
        frontend["server_type"] = "flask"
        frontend["workers"] = "1"

        # main config
        config = {}
        config["monitoring"] = {}
        config["authorisation_server"] = authorisation_server
        config["authentication_server"] = authentication_server
        config["backend"] = backend
        config["debug"] = False
        config["frontend"] = frontend
        config["cache"] = {"CACHE_TYPE": "simple"}  # set CACHE_TYPE to "null" to disable it
        return config

    def _parse_config_files(self, user_conf_path: str) -> Dict[str, any]:
        # build the configuration dictionary from system and user inputs
        current_config = {}

        def parse_config(file_path: str):
            try:
                with open(file_path, "r") as f:
                    config = yaml.load(f.read(), Loader=HomeFolderLoader)
                # merge with the current config
                Config.deep_update(current_config, config)
            except Exception as e:
                logger.error(f"Not able to load the configuration in {file_path}, exception: {type(e)} {e}")
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
        if "AVISO_AUTH_CONFIG" in os.environ:
            env_path = os.environ["AVISO_AUTH_CONFIG"]
            parse_config(env_path)

        # Finally the user config option
        if user_conf_path:
            parse_config(user_conf_path)

        # instantiate Aviso Monitoring config
        if "monitoring" in current_config:
            # noinspection PyTypeChecker
            current_config["monitoring"] = MonitoringConfig(conf_from_file=current_config["monitoring"])

        return current_config

    def _read_env_variables(self) -> Dict[str, any]:
        config = {"backend": {}, "authentication_server": {}, "authorisation_server": {}, "frontend": {}}
        if "AVISO_AUTH_DEBUG" in os.environ:
            config["debug"] = os.environ["AVISO_AUTH_DEBUG"]
        if "AVISO_AUTH_FRONTEND_HOST" in os.environ:
            config["frontend"]["host"] = os.environ["AVISO_AUTH_FRONTEND_HOST"]
        if "AVISO_AUTH_FRONTEND_PORT" in os.environ:
            config["frontend"]["port"] = int(os.environ["AVISO_AUTH_FRONTEND_PORT"])
        if "AVISO_AUTH_FRONTEND_SERVER_TYPE" in os.environ:
            config["frontend"]["server_type"] = os.environ["AVISO_AUTH_FRONTEND_SERVER_TYPE"]
        if "AVISO_AUTH_FRONTEND_WORKERS" in os.environ:
            config["frontend"]["workers"] = int(os.environ["AVISO_AUTH_FRONTEND_WORKERS"])
        if "AVISO_AUTH_BACKEND_URL" in os.environ:
            config["backend"]["url"] = os.environ["AVISO_AUTH_BACKEND_URL"]
        if "AVISO_AUTH_BACKEND_MONITOR" in os.environ:
            config["backend"]["monitor"] = os.environ["AVISO_AUTH_BACKEND_MONITOR"]
        if "AVISO_AUTH_AUTHENTICATION_URL" in os.environ:
            config["authentication_server"]["url"] = os.environ["AVISO_AUTH_AUTHENTICATION_URL"]
        if "AVISO_AUTH_AUTHENTICATION_MONITOR" in os.environ:
            config["authentication_server"]["monitor"] = os.environ["AVISO_AUTH_AUTHENTICATION_MONITOR"]
        if "AVISO_AUTH_AUTHORISATION_URL" in os.environ:
            config["authorisation_server"]["url"] = os.environ["AVISO_AUTH_AUTHORISATION_URL"]
        if "AVISO_AUTH_AUTHORISATION_MONITOR" in os.environ:
            config["authorisation_server"]["monitor"] = os.environ["AVISO_AUTH_AUTHORISATION_MONITOR"]
        return config

    def logging_setup(self, logging_conf_path: str):

        if logging_conf_path is not None:
            try:
                with open(logging_conf_path, "r") as f:
                    log_config = yaml.load(f.read(), Loader=yaml.Loader)
            except Exception as e:
                logger.warning(f"Not able to load the logging configuration, exception: {type(e)} {e}")
                logger.debug("", exc_info=True)
                sys.exit(-1)
        elif "AVISO_LOG" in os.environ:
            try:
                with open(os.environ["AVISO_LOG"], "r") as f:
                    log_config = yaml.load(f.read(), Loader=yaml.Loader)
            except Exception as e:
                logger.warning(f"Not able to load the logging configuration, exception: {type(e)} {e}")
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
            logger.warning(f"Not able to load the logging configuration, exception: {type(e)} {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @property
    def monitoring(self) -> MonitoringConfig:
        return self._monitoring

    @monitoring.setter
    def monitoring(self, monitoring: Dict):
        m = self._config.get("monitoring")
        if monitoring is not None: 
            m = MonitoringConfig(**m)   
        # verify is valid
        assert m is not None, "monitoring has not been configured"
        self._monitoring = m

    @property
    def authentication_server(self) -> Dict[str, any]:
        return self._authentication_server

    @authentication_server.setter
    def authentication_server(self, authentication_server: Dict[str, any]):
        server = self._config.get("authentication_server")
        if authentication_server is not None and server is not None:
            Config.deep_update(server, authentication_server)
        elif authentication_server is not None:
            server = authentication_server
        # verify is valid
        assert server is not None, "authentication_server has not been configured"
        assert server.get("url") is not None, "authentication_server url has not been configured"
        assert server.get("req_timeout") is not None, "authentication_server req_timeout has not been configured"
        assert server.get("cache_timeout") is not None, "authentication_server cache_timeout has not been configured"
        assert server.get("monitor") is not None, "authentication_server monitor has not been configured"
        self._authentication_server = server

    @property
    def authorisation_server(self) -> Dict[str, any]:
        return self._authorisation_server

    @authorisation_server.setter
    def authorisation_server(self, authorisation_server: Dict[str, any]):
        server = self._config.get("authorisation_server")
        if authorisation_server is not None and server is not None:
            Config.deep_update(server, authorisation_server)
        elif authorisation_server is not None:
            server = authorisation_server
        # verify is valid
        assert server is not None, "authorisation_server has not been configured"
        assert server.get("url") is not None, "authorisation_server url has not been configured"
        assert server.get("req_timeout") is not None, "authorisation_server req_timeout has not been configured"
        assert server.get("cache_timeout") is not None, "authorisation_server cache_timeout has not been configured"
        assert server.get("username") is not None, "authorisation_server username has not been configured"
        assert server.get("password") is not None, "authorisation_server password has not been configured"
        assert server.get("monitor") is not None, "authorisation_server monitor has not been configured"
        self._authorisation_server = server

    @property
    def backend(self) -> Dict[str, any]:
        return self._backend

    @backend.setter
    def backend(self, backend: Dict[str, any]):
        server = self._config.get("backend")
        if backend is not None and server is not None:
            Config.deep_update(server, backend)
        elif backend is not None:
            server = backend
        # verify is valid
        assert server is not None, "backend has not been configured"
        assert server.get("url") is not None, "backend url has not been configured"
        assert server.get("req_timeout") is not None, "backend timeout has not been configured"
        assert server.get("route") is not None, "backend route has not been configured"
        assert server.get("monitor") is not None, "backend monitor has not been configured"
        self._backend = server

    @property
    def frontend(self) -> Dict[str, any]:
        return self._frontend

    @frontend.setter
    def frontend(self, frontend: Dict[str, any]):
        fe = self._config.get("frontend")
        if frontend is not None and fe is not None:
            Config.deep_update(fe, frontend)
        elif frontend is not None:
            fe = frontend
        # verify is valid
        assert fe is not None, "frontend has not been configured"
        assert fe.get("host") is not None, "frontend host has not been configured"
        assert fe.get("port") is not None, "frontend port has not been configured"
        assert fe.get("server_type") is not None, "frontend server_type has not been configured"
        assert fe.get("workers") is not None, "frontend workers has not been configured"
        self._frontend = fe

    @property
    def cache(self):
        return self._cache

    @cache.setter
    def cache(self, cache: Dict):
        self._cache = self._configure_property(cache, "cache")

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

    def __str__(self):
        config_string = (
                f"authorisation_server: {self.authorisation_server}" +
                f", authentication_server: {self.authentication_server}" +
                f", backend: {self.backend}" +
                f", debug: {self.debug}" +
                f", frontend: {self.frontend}" +
                f", monitoring: {self.monitoring}"
        )
        return config_string

    def _configure_default_log(self):
        # creating default console handler
        console_handler = logging.StreamHandler()
        console_handler.name = "console"
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(console_handler)

    def _configure_property(self, param, name):
        value = None
        if param is not None:
            value = param
        elif self._config.get(name) is not None:
            # Setting var from user configuration file
            value = self._config.get(name)
        else:
            logger.error(f"{name} has not been configured")
            sys.exit(-1)
        return value

    @staticmethod
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, collections.abc.Mapping):
                d[k] = Config.deep_update(d.get(k, type(v)()), v)
            else:
                d[k] = v
        return d


# class to allow yaml loader to replace ~ with HOME directory
class HomeFolderLoader(yaml.Loader):
    path_matcher = re.compile('~')

    @staticmethod
    def path_constructor(loader, node):
        return os.path.expanduser(node.value)


HomeFolderLoader.add_implicit_resolver('!path', HomeFolderLoader.path_matcher, None)
HomeFolderLoader.add_constructor('!path', HomeFolderLoader.path_constructor)

# class to add hostname to the possible attributes to use in the logging
class HostnameFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = HostnameFilter.hostname
        return True