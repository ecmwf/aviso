# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import importlib
from enum import Enum
from .monitor import Monitor
from .. import logger


class AvisoAuthMetricType(Enum):
    """
    This Enum describes the various metrics that can be used for aviso-auth
    """

    auth_resp_time = ("aviso_auth_collectors", "ResponseTimeCollector")

    def get_class(self):
        module = importlib.import_module("aviso_admin.monitoring.collectors." + self.value[0])
        return getattr(module, self.value[1])


class AvisoAuthMonitor(Monitor):

    def __init__(self, config):
        aviso_auth_config = config["aviso_auth_monitor"]
        self.url = aviso_auth_config["url"]
        self.metrics_name = aviso_auth_config["metrics"]
        self.frequency = aviso_auth_config["frequency"]
        self.enabled = aviso_auth_config["enabled"]
        self.req_timeout = aviso_auth_config["req_timeout"]
        self.username = aviso_auth_config["username"]
        self.password = aviso_auth_config["password"]
        super().__init__(config)

    def retrieve_metrics(self):
        """
        This method for each metric to collect instantiates the relative collector and run it
        :return: the metrics collected
        """
        logger.debug("Collecting metrics...")

        # array of metric to return
        r_metrics = []
        for mn in self.metrics_name:
            # create the relative metric collector
            m_type = AvisoAuthMetricType[mn.lower()]
            collector = m_type.get_class()(
                m_type, 
                self.req_timeout, 
                url=self.url,
                username=self.username,
                password=self.password)

            # retrieve metric
            r_metrics.append(collector.metric())

        logger.debug("Metrics collection completed")

        return r_metrics