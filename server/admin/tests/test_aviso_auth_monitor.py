# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
from aviso_admin import config, logger
from aviso_admin.monitoring.collectors.aviso_auth_collectors import ResponseTimeCollector
from aviso_admin.monitoring.aviso_auth_monitor import AvisoAuthMetricType, AvisoAuthMonitor

'''
Set url anc credentials in the system config to access to aviso-auth
aviso_auth_monitor :
  url: "https://xxx"
  "username: ""
  "password": ""
'''

def conf() -> config.Config:  # this automatically configure the logging
    #c = config.Config(conf_path="tests/config.yaml")
    c = config.Config()
    return c


def test_run_monitor():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    config = conf().monitor
    config["aviso_auth_monitor"]["metrics"] = ["auth_resp_time"]
    monitor = AvisoAuthMonitor(config)
    monitor.run()


def test_measure_test_pull():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = ResponseTimeCollector(
        AvisoAuthMetricType.auth_resp_time, 
        url=conf().monitor["aviso_auth_monitor"]["url"],
        username=conf().monitor["aviso_auth_monitor"]["username"],
        password=conf().monitor["aviso_auth_monitor"]["password"])
    assert collector.measure_test_pull(conf().monitor["aviso_auth_monitor"]["url"]) > 0


def test_ResponseTimeCollector():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    collector = ResponseTimeCollector(
        AvisoAuthMetricType.auth_resp_time, 
        url=conf().monitor["aviso_auth_monitor"]["url"],
        username=conf().monitor["aviso_auth_monitor"]["username"],
        password=conf().monitor["aviso_auth_monitor"]["password"])
    metric = collector.metric()
    assert metric.get("name")
    assert metric.get("m_value") is not None

