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

from . import logger


class Config:
    """
    This class is in charge of holding the user configuration, which can be defined by arguments,
    environment variables or defaults.
    """

    def __init__(self,
                 collector=None):

        try:
            # we build the configuration in priority order from the lower to the higher
            # start from the defaults
            self._config = self._create_default_config()
            # add environment variables
            Config.deep_update(self._config, self._read_env_variables())
            # add constructor parameters
            self.collector = collector

            logger.debug(f"Loading configuration completed")

        except Exception as e:
            logger.error(f"Error occurred while setting the configuration, exception: {type(e)} {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @staticmethod
    def _create_default_config() -> Dict:
   
        collector = {
            "transmitter": {
                "monitoring_server_host": "127.0.0.1",
                "monitoring_server_port": 1111,
                "component_name": "test_component",
                "frequency": 2,
            },
            "enabled": True,
            "telemetry_type": "test_time",
        }

        # main config
        config = {}
        config["collector"] = collector
        return config

    def _read_env_variables(self) -> Dict:
        config = {}
        # TBD
        return config


    @property
    def collector(self) -> Dict:
        return self._collector

    @collector.setter
    def collector(self, collector: Dict):
        c = self._config.get("collector")
        if collector is not None and c is not None:
            Config.deep_update(c, collector)
        elif collector is not None:
            m = collector
        # verify is valid
        assert m is not None, "collector has not been configured"
        self._monitoring = m

    def __str__(self):
        config_string = (
            f"host: {self.host}" +
            f", monitoring: {self.monitoring}"
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