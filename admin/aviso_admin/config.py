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
from typing import Optional, Dict

import yaml

from . import logger, HOME_FOLDER, SYSTEM_FOLDER

# Default configuration location
CONF_FILE = "config.yaml"


class Config:
    """
    This class is in charge of holding the user configuration, which can be defined by command line options,
    environment variables, configuration files or defaults.
    """

    def __init__(self,
                 conf_path: Optional[str] = None,
                 logging_path: Optional[str] = None,
                 debug: Optional[bool] = None,
                 compactor: [Dict[str, any]] = None,
                 cleaner: [Dict[str, any]] = None,
                 monitor: [Dict[str, any]] = None):
        """
        :param conf_path: path to the system configuration file. If not provided,
        the default location is HOME_FOLDER/user_config.yaml.
        :param logging_path: path to the logging configuration file. If not provided,
        the default location is the logging section of the HOME_FOLDER/user_config.yaml.
        :param debug: flag to activate the debug log to the console output
        :param compactor: config for the compactor process
        :param cleaner: config for the cleaner process
        :param monitor: config for monitor processes
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
            self.compactor = compactor
            self.cleaner = cleaner
            self.monitor = monitor

            logger.debug(f"Loading configuration completed")

        except Exception as e:
            logger.error(f"Error occurred while setting the configuration, exception: {type(e)} {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @staticmethod
    def _create_default_config() -> Dict[str, any]:
        # compactor
        compactor = {
            "url": "http://localhost:2379",
            "req_timeout": 60,  # seconds
            "history_path": "/ec/admin/history",
            "retention_period": 16,  # days
            "scheduled_time": "00:00",
        }

        # cleaner
        cleaner = {
            "url": "http://localhost:2379",
            "req_timeout": 60,  # seconds
            "dest_path": "/ec/admin/",
            "diss_path": "/ec/diss/",
            "mars_path": "/ec/mars/",
            "retention_period": 15,  # days
            "scheduled_time": "00:00"
        }

        # monitors
        etcd = {
            "member_urls": ["http://localhost:2379"],
            "metrics": ["etcd_store_size", "etcd_cluster_status", "etcd_diss_keys", "etcd_mars_keys"]
        }
        monitor = {
            "server_url": "https://localhost",
            "service_host": "aviso",
            "req_timeout": 60,  # seconds
            "frequency": 5,  # in minutes
            "etcd": etcd
        }

        # main config
        config = {
            "compactor": compactor,
            "cleaner": cleaner,
            "monitor": monitor,
            "debug": False
        }
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
        if "AVISO_ADMIN_CONFIG" in os.environ:
            env_path = os.environ["AVISO_ADMIN_CONFIG"]
            parse_config(env_path)

        # Finally the user config option
        if user_conf_path:
            parse_config(user_conf_path)

        return current_config

    def _read_env_variables(self) -> Dict[str, any]:
        config = {"cleaner": {}, "compactor": {}}
        if "AVISO_ADMIN_DEBUG" in os.environ:
            config["debug"] = os.environ["AVISO_ADMIN_DEBUG"]
        if "AVISO_ADMIN_CLEANER_URL" in os.environ:
            config["cleaner"]["url"] = os.environ["AVISO_ADMIN_CLEANER_URL"]
        if "AVISO_ADMIN_CLEANER_RETENTION_PERIOD" in os.environ:
            config["cleaner"]["retention_period"] = os.environ["AVISO_ADMIN_CLEANER_RETENTION_PERIOD"]
        if "AVISO_ADMIN_CLEANER_SCHEDULED_TIME" in os.environ:
            config["cleaner"]["scheduled_time"] = os.environ["AVISO_ADMIN_CLEANER_SCHEDULED_TIME"]
        if "AVISO_ADMIN_COMPACTOR_URL" in os.environ:
            config["compactor"]["url"] = os.environ["AVISO_ADMIN_COMPACTOR_URL"]
        if "AVISO_ADMIN_COMPACTOR_RETENTION_PERIOD" in os.environ:
            config["compactor"]["retention_period"] = os.environ["AVISO_ADMIN_COMPACTOR_RETENTION_PERIOD"]
        if "AVISO_ADMIN_COMPACTOR_SCHEDULED_TIME" in os.environ:
            config["compactor"]["scheduled_time"] = os.environ["AVISO_ADMIN_COMPACTOR_SCHEDULED_TIME"]
        return config

    def logging_setup(self, logging_conf_path: str):

        if logging_conf_path is not None:
            try:
                with open(logging_conf_path, "r") as f:
                    log_config = yaml.safe_load(f.read())
            except Exception as e:
                logger.warning(f"Not able to load the logging configuration, exception: {type(e)} {e}")
                logger.debug("", exc_info=True)
                sys.exit(-1)
        elif "AVISO_ADMIN_LOG" in os.environ:
            try:
                with open(os.environ["AVISO_ADMIN_LOG"], "r") as f:
                    log_config = yaml.safe_load(f.read())
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
    def compactor(self) -> Dict[str, any]:
        return self._compactor

    @compactor.setter
    def compactor(self, compactor: Dict[str, any]):
        comp = self._config.get("compactor")
        if compactor is not None and comp is not None:
            Config.deep_update(comp, compactor)
        elif compactor is not None:
            comp = compactor
        # verify is valid
        assert comp is not None, "compactor has not been configured"
        assert comp.get("url") is not None, "compactor url has not been configured"
        assert comp.get("req_timeout") is not None, "compactor req_timeout has not been configured"
        assert comp.get("history_path") is not None, "compactor history_path has not been configured"
        assert comp.get("retention_period") is not None, "compactor retention_period has not been configured"
        assert comp.get("scheduled_time") is not None, "compactor scheduled_time has not been configured"
        self._compactor = comp

    @property
    def cleaner(self) -> Dict[str, any]:
        return self._cleaner

    @cleaner.setter
    def cleaner(self, cleaner: Dict[str, any]):
        cl = self._config.get("cleaner")
        if cleaner is not None and cl is not None:
            Config.deep_update(cl, cleaner)
        elif cleaner is not None:
            cl = cleaner
        # verify is valid
        assert cl is not None, "cleaner has not been configured"
        assert cl.get("url") is not None, "cleaner url has not been configured"
        assert cl.get("req_timeout") is not None, "cleaner req_timeout has not been configured"
        assert cl.get("dest_path") is not None, "cleaner dest_path has not been configured"
        assert cl.get("diss_path") is not None, "cleaner diss_path has not been configured"
        assert cl.get("mars_path") is not None, "cleaner mars_path has not been configured"
        assert cl.get("retention_period") is not None, "cleaner retention_period has not been configured"
        self._cleaner = cl

    @property
    def monitor(self) -> Dict[str, any]:
        return self._monitor

    @monitor.setter
    def monitor(self, monitor: Dict[str, any]):
        m = self._config.get("monitor")
        if monitor is not None and m is not None:
            Config.deep_update(m, monitor)
        elif monitor is not None:
            m = monitor
        # verify is valid
        assert m is not None, "monitor has not been configured"
        assert m.get("frequency") is not None, "frequency has not been configured"
        assert m.get("etcd") is not None, "etcd monitor has not been configured"
        assert m.get("server_url") is not None, "server_url has not been configured"
        assert m.get("service_host") is not None, "service_host has not been configured"
        assert m.get("username") is not None, "username has not been configured"
        assert m.get("password") is not None, "password has not been configured"
        assert m.get("req_timeout") is not None, "req_timeout has not been configured"
        assert m["etcd"].get("member_urls") is not None, "etcd member_urls have not been configured"
        assert m["etcd"].get("metrics") is not None, "etcd metrics have not been configured"
        self._monitor = m

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
                f"compactor: {self.compactor}" +
                f", cleaner: {self.cleaner}" +
                f", monitor: {self.monitor}" +
                f", debug: {self.debug}"
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
class HomeFolderLoader(yaml.SafeLoader):
    path_matcher = re.compile('~')

    @staticmethod
    def path_constructor(loader, node):
        return os.path.expanduser(node.value)


HomeFolderLoader.add_implicit_resolver('!path', HomeFolderLoader.path_matcher, None)
HomeFolderLoader.add_constructor('!path', HomeFolderLoader.path_constructor)
