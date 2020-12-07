# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import collections.abc
import os
import re
import sys
from typing import Dict
import yaml

from .. import logger


class Config:
    """
    This class is in charge of holding the configuration for the collector, which can be defined by arguments,
    environment variables or defaults.
    """

    def __init__(self,
                 transmitter=None,
                 enabled=None,
                 telemetry_type=None):

        try:
            # we build the configuration in priority order from the lower to the higher
            # start from the defaults
            self._config = self._create_default_config()
            # add environment variables
            Config.deep_update(self._config, self._read_env_variables())
            # add constructor parameters
            self.transmitter = transmitter
            self.enabled = enabled
            self.telemetry_type = telemetry_type

            logger.debug(f"Loading configuration completed")

        except Exception as e:
            logger.error(f"Error occurred while setting the configuration, exception: {type(e)} {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @staticmethod
    def _create_default_config() -> Dict:
   
        transmitter = {
            "monitoring_server_host": "127.0.0.1",
            "monitoring_server_port": 1111,
            "component_name": "TBD",
            "frequency": 2,
        }

        # main config
        config = {}
        config["transmitter"] = transmitter
        config["enabled"] = True
        config["telemetry_type"] = "TBD"
        return config

    def _read_env_variables(self) -> Dict:
        config = {}
        # TBD
        return config


    @property
    def transmitter(self):
        return self._transmitter

    @transmitter.setter
    def transmitter(self, transmitter):
        t = self._config.get("transmitter")
        if transmitter is not None and t is not None:
            Config.deep_update(t, transmitter)
        elif transmitter is not None:
            t = transmitter
        # verify is valid
        assert t is not None, "transmitter has not been configured"
        assert t["monitoring_server_host"] is not None, "transmitter monitoring_server_host has not been configured"
        assert t["monitoring_server_port"] is not None, "transmitter monitoring_server_port has not been configured"
        assert t["component_name"] is not None, "transmitter component_name has not been configured"
        assert t["frequency"] is not None, "transmitter frequency has not been configured"
        self._transmitter = t
    
    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        self._enabled = self._configure_property(enabled, "enabled")
    
    @property
    def telemetry_type(self):
        return self._telemetry_type

    @telemetry_type.setter
    def telemetry_type(self, telemetry_type):
        self._telemetry_type = self._configure_property(telemetry_type, "telemetry_type")

    def __str__(self):
        config_string = (
            f"transmitter: {self.transmitter}" +
            f", enabled: {self.enabled}" +
            f", telemetry_type: {self.telemetry_type}"
        )
        return config_string

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