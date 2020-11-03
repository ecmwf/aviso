# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

from aviso_admin import config, logger
from aviso_admin.monitoring.etcd.etcd_collectors import ClusterStatusCollector, StoreSizeCollector, DissKeysCollector, \
    MarsKeysCollector
from aviso_admin.monitoring.etcd.etcd_monitor import EtcdMetricType
from aviso_admin.monitoring.monitor import Monitor

'''
Set url and credentials in the system config to access to the monitoring server
monitor:
  server_url: "https://xxx"
  username: "xxx"
  password: "xxx"
'''

def conf() -> config.Config:  # this automatically configure the logging
    #c = config.Config(conf_path="tests/config.yaml")
    c = config.Config()
    return c


def test_run_monitor():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    config = conf().monitor
    config["etcd"]["metrics"] = ["etcd_store_size", "etcd_cluster_status", "etcd_diss_keys", "etcd_mars_keys"]
    monitor = Monitor(config)
    monitor.run()


def test_storage_size():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = StoreSizeCollector(EtcdMetricType.etcd_store_size, conf().monitor["etcd"]["member_urls"])
    size = collector.store_size(conf().monitor["etcd"]["member_urls"][0])
    assert size is not None


def test_StoreSizeCollector():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = StoreSizeCollector(EtcdMetricType.etcd_store_size, conf().monitor["etcd"]["member_urls"])
    metric = collector.metric()
    assert metric.get("name")
    assert metric.get("m_value") is not None


def test_cluster_size():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = ClusterStatusCollector(EtcdMetricType.etcd_cluster_status, conf().monitor["etcd"]["member_urls"])
    size = collector.cluster_size(conf().monitor["etcd"]["member_urls"][0])
    assert size == len(conf().monitor["etcd"]["member_urls"])


def test_health():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = ClusterStatusCollector(EtcdMetricType.etcd_cluster_status, conf().monitor["etcd"]["member_urls"])
    assert collector.health(conf().monitor["etcd"]["member_urls"][0])


def test_ClusterStatusCollector():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = ClusterStatusCollector(EtcdMetricType.etcd_cluster_status, conf().monitor["etcd"]["member_urls"])
    metric = collector.metric()
    assert metric["status"] == 0


def test_diss_keys():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = DissKeysCollector(EtcdMetricType.etcd_diss_keys, conf().monitor["etcd"]["member_urls"])
    assert collector.total_keys(conf().monitor["etcd"]["member_urls"][0]) > 0


def test_DissKeysCollector():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = DissKeysCollector(EtcdMetricType.etcd_diss_keys, conf().monitor["etcd"]["member_urls"])
    metric = collector.metric()
    assert metric["status"] == 0
    assert metric["m_value"] > 0


def test_mars_keys():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = MarsKeysCollector(EtcdMetricType.etcd_mars_keys, conf().monitor["etcd"]["member_urls"])
    assert collector.total_keys(conf().monitor["etcd"]["member_urls"][0]) > 0


def test_MarsKeysCollector():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = MarsKeysCollector(EtcdMetricType.etcd_mars_keys, conf().monitor["etcd"]["member_urls"])
    metric = collector.metric()
    assert metric["status"] == 0
    assert metric["m_value"] > 0
