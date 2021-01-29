# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

from aviso_monitoring import logger
from aviso_monitoring.config import Config
from aviso_monitoring.reporter.etcd_reporter import EtcdReporter

tlm_type = "test2"  # to be defined
config = {
    "etcd_reporter": {
        "enabled": True,
        "member_urls": ["http://localhost:2379"],
    },
    # this are the setting for sending the telemetry to a monitoring server like Opsview
    "monitor_server": {
        "url": "https://monitoring-dev.ecmwf.int/rest",
        "username": "TBD",
        "password": "TBD",
        "service_host": "aviso",
        "req_timeout": 60,  # seconds
    }
}


# you need to set the connection to opsview to run this test and select a tml_type associated to a passive check
def test_run_reporter():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = EtcdReporter(Config(**config))
    reporter.run()


def test_process_tlms():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = EtcdReporter(Config(**config))
    metrics = reporter.process_tlms()
    assert len(metrics) == 3
    store_size = list(filter(lambda m: m["name"] == "etcd_store_size", metrics))[0]
    assert len(store_size["metrics"]) == 3
    status = list(filter(lambda m: m["name"] == "etcd_cluster_status", metrics))[0]
    assert len(status["metrics"]) == 1
    keys = list(filter(lambda m: m["name"] == "etcd_total_keys", metrics))[0]
    assert len(keys["metrics"]) == 1
