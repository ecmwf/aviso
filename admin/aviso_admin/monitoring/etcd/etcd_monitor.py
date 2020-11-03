# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import importlib
from enum import Enum

from aviso_admin import logger


class EtcdMetricType(Enum):
    """
    This Enum describes the various etcd metrics that can be used
    """

    etcd_store_size = ("etcd_collectors", "StoreSizeCollector")
    etcd_cluster_status = ("etcd_collectors", "ClusterStatusCollector")
    etcd_diss_keys = ("etcd_collectors", "DissKeysCollector")
    etcd_mars_keys = ("etcd_collectors", "MarsKeysCollector")

    def get_class(self):
        module = importlib.import_module("aviso_admin.monitoring.etcd." + self.value[0])
        return getattr(module, self.value[1])


class EtcdMonitor:

    def __init__(self, config):
        self.member_urls = config["member_urls"]
        self.metrics_name = config["metrics"]

    def retrieve_metrics(self):
        """
        :return: True if successful
        """
        logger.debug("Running etcd monitor...")

        # array of metric to return
        r_metrics = []
        for mn in self.metrics_name:
            # create the relative metric collector
            m_type = EtcdMetricType[mn.lower()]
            collector = m_type.get_class()(m_type, self.member_urls)

            # retrieve metric
            r_metrics.append(collector.metric())

        logger.debug("etcd monitor completed")

        return r_metrics