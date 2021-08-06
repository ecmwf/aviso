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
import socket
import sys
from typing import Dict

import yaml
from aviso_monitoring.collector.config import Config as MonitoringConfig
from yaml import Loader

from pyaviso.user_config import UserConfig as AvisoConfig

from . import HOME_FOLDER, SYSTEM_FOLDER, logger

# Default configuration location
CONF_FILE = "config.yaml"


class Config:
    """
    This class is in charge of holding the user configuration, which can be defined by arguments,
    environment variables, configuration files or defaults.
    """

    def __init__(
        self,
        conf_path=None,
        logging_path=None,
        debug=None,
        host=None,
        port=None,
        server_type=None,
        workers=None,
        aviso=None,
        monitoring=None,
        skips=None,
    ):
        """

        :param conf_path: path to the system configuration file. If not provided,
        the default location is HOME_FOLDER/user_config.yaml.
        :param logging_path: path to the logging configuration file. If not provided,
        the default location is the logging section of the HOME_FOLDER/user_config.yaml.
        :param debug: flag to activate the debug log to the console output
        :param aviso: configuration related to the aviso module
        :param monitoring: configuration related to the monitoring of this component
        :param skips: dict of request fields to use to identify requests we want to ignore - {field1: [value1, value2]}
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
            self.host = host
            self.port = port
            self.server_type = server_type
            self.workers = workers
            self.aviso = aviso
            self.monitoring = monitoring
            self.skips = skips

            logger.debug("Loading configuration completed")

        except Exception as e:
            logger.error(f"Error occurred while setting the configuration, exception: {type(e)} {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @staticmethod
    def _create_default_config() -> Dict:

        # main config
        config = {}
        config["monitoring"] = None
        config["aviso"] = None
        config["debug"] = False
        config["host"] = "127.0.0.1"
        config["port"] = 8080
        config["server_type"] = "flask"
        config["workers"] = "1"
        config["skips"] = {}
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
        if "AVISO_REST_CONFIG" in os.environ:
            env_path = os.environ["AVISO_REST_CONFIG"]
            parse_config(env_path)

        # Finally the user config option
        if user_conf_path:
            parse_config(user_conf_path)

        # instantiate Aviso Config
        if "aviso" in current_config:
            current_config["aviso"] = AvisoConfig(conf_from_file=current_config["aviso"])

        # instantiate Aviso Monitoring config
        if "monitoring" in current_config:
            current_config["monitoring"] = MonitoringConfig(conf_from_file=current_config["monitoring"])

        return current_config

    def _read_env_variables(self) -> Dict[str, any]:
        config = {}
        if "AVISO_REST_DEBUG" in os.environ:
            config["debug"] = os.environ["AVISO_REST_DEBUG"]
        if "AVISO_REST_HOST" in os.environ:
            config["host"] = os.environ["AVISO_REST_HOST"]
        if "AVISO_REST_PORT" in os.environ:
            config["port"] = int(os.environ["AVISO_REST_PORT"])
        if "AVISO_REST_SERVER_TYPE" in os.environ:
            config["server_type"] = os.environ["AVISO_REST_SERVER_TYPE"]
        if "AVISO_REST_WORKERS" in os.environ:
            config["workers"] = int(os.environ["AVISO_REST_WORKERS"])
        return config

    def logging_setup(self, logging_conf_path: str):

        if logging_conf_path is not None:
            try:
                with open(logging_conf_path, "r") as f:
                    log_config = yaml.load(f.read(), Loader=Loader)
            except Exception as e:
                logger.warning(f"Not able to load the logging configuration, exception: {type(e)} {e}")
                logger.debug("", exc_info=True)
                sys.exit(-1)
        elif "AVISO_LOG" in os.environ:
            try:
                with open(os.environ["AVISO_LOG"], "r") as f:
                    log_config = yaml.load(f.read(), Loader=Loader)
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
            m = MonitoringConfig(**monitoring)
        if m is None:
            m = MonitoringConfig()
        # verify is valid
        assert m is not None, "monitoring has not been configured"
        self._monitoring = m

    @property
    def aviso(self) -> AvisoConfig:
        return self._aviso

    @aviso.setter
    def aviso(self, aviso: Dict):
        av = self._config.get("aviso")
        if aviso is not None:
            av = AvisoConfig(**aviso)
        if av is None:
            av = AvisoConfig()
        # verify is valid
        assert av is not None, "aviso has not been configured"
        self._aviso = av

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host: str):
        self._host = self._configure_property(host, "host")

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port: int):
        self._port = self._configure_property(port, "port")

    @property
    def server_type(self):
        return self._server_type

    @server_type.setter
    def server_type(self, server_type: str):
        self._server_type = self._configure_property(server_type, "server_type")

    @property
    def workers(self):
        return self._workers

    @workers.setter
    def workers(self, workers: int):
        self._workers = self._configure_property(workers, "workers")

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
    def skips(self):
        return self._skips

    @skips.setter
    def skips(self, skips: str):
        self._skips = self._configure_property(skips, "skips")

    def __str__(self):
        config_string = (
            f"host: {self.host}"
            + f", port: {self.port}"
            + f", server_type: {self.server_type}"
            + f", debug: {self.debug}"
            + f", workers: {self.workers}"
            + f", aviso: {self.aviso}"
            + f", monitoring: {self.monitoring}"
            + f", skips: {self.skips}"
        )
        return config_string

    def _configure_default_log(self):
        # creating default console handler
        console_handler = logging.StreamHandler()
        console_handler.name = "console"
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))
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
    path_matcher = re.compile("~")

    @staticmethod
    def path_constructor(loader, node):
        return os.path.expanduser(node.value)


HomeFolderLoader.add_implicit_resolver("!path", HomeFolderLoader.path_matcher, None)
HomeFolderLoader.add_constructor("!path", HomeFolderLoader.path_constructor)


# class to add hostname to the possible attributes to use in the logging
class HostnameFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = HostnameFilter.hostname
        return True


# class to add a counter number to each log record to use it as id of the log record. Useful to check if any log got
# lost. To avoid skipping ids it needs to be applied to one handler. Also it will be replicated for each worker.
class CounterFilter(logging.Filter):
    logging_counter = 0

    def filter(self, record):
        record.counter = CounterFilter.logging_counter
        CounterFilter.logging_counter += 1
        return True
