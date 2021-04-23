# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import os
import time
from multiprocessing import Process

import pytest
import requests
from aviso_monitoring import logger
from aviso_monitoring.config import Config
from aviso_monitoring.receiver import AVISO_AUTH_APP_NAME, Receiver
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthMetricType
from aviso_monitoring.reporter.prometheus_reporter import PrometheusReporter

counter_type = AvisoAuthMetricType.auth_users_counter.name
config = {"prometheus_reporter": {"enabled": True, "port": 8090}, "udp_server": {"host": "127.0.0.1", "port": 1120}}


def receiver():

    counter_tlm1 = {
        "telemetry_type": counter_type,
        "component_name": "counter_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{counter_type}_counter": 1,
            f"{counter_type}_values": ["apple"],
        },
    }
    counter_tlm2 = {
        "telemetry_type": counter_type,
        "component_name": "counter_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{counter_type}_counter": 2,
            f"{counter_type}_values": ["apple", "pear"],
        },
    }

    receiver = Receiver()
    receiver._incoming_tlms[counter_type] = [counter_tlm1, counter_tlm2]
    return receiver


@pytest.fixture(scope="module", autouse=True)
def prepost_module():
    # Run the frontend at global level so it will be executed once and accessible to all tests
    reporter = PrometheusReporter(Config(**config), receiver())
    reporter.start()
    time.sleep(3)
    yield


def test_metrics():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    conf = Config(**config)
    resp = requests.get(f"http://{conf.prometheus_reporter['host']}:{conf.prometheus_reporter['port']}/metrics")
    assert resp.status_code == 200
    assert " 2\n" in resp.text
