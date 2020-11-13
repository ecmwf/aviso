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


class EtcdMetricType(Enum):
    """
    This Enum describes the various etcd metrics that can be used
    """

    etcd_store_size = ("etcd_collectors", "StoreSizeCollector")
    etcd_cluster_status = ("etcd_collectors", "ClusterStatusCollector")
    etcd_diss_keys = ("etcd_collectors", "DissKeysCollector")
    etcd_mars_keys = ("etcd_collectors", "MarsKeysCollector")

    def get_class(self):
        module = importlib.import_module("aviso_admin.monitoring.collectors." + self.value[0])
        return getattr(module, self.value[1])


class EtcdMonitor(Monitor):

    def __init__(self, config):
        etcd_config = config["etcd_monitor"]
        self.member_urls = etcd_config["member_urls"]
        self.metrics_name = etcd_config["metrics"]
        self.frequency = etcd_config["frequency"]
        self.enabled = etcd_config["enabled"]
        self.req_timeout = etcd_config["req_timeout"]
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
            m_type = EtcdMetricType[mn.lower()]
            collector = m_type.get_class()(m_type, self.req_timeout, member_urls=self.member_urls)

            # retrieve metric
            r_metrics.append(collector.metric())

        logger.debug("Metrics collection completed")

        return r_metrics