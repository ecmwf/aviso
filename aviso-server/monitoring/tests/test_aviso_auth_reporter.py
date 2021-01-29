# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import datetime
from aviso_monitoring import logger
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthReporter
from aviso_monitoring.receiver import Receiver
from aviso_monitoring.config import Config

tlm_type = "test2"  # to be defined
config = {
    "aviso_auth_reporter": {
        "tlm_type": tlm_type,
        "enabled": True,
        "frequency": 2,  # in minutes
        "sub_tlms": ["t1", "t2"]

    },
    # this are the setting for sending the telemetry to a monitoring server like Opsview
    "monitor_server": {
        "url": "https://monitoring-dev.ecmwf.int/rest",
        "username": "TBD",
        "password": "TBD",
        "service_host": "aviso",
        "req_timeout": 60,  # seconds
    },
    "udp_server": {
        "host": "127.0.0.1",
        "port": 1111
    }
}


def receiver():
    test_tlm1 = {
        "telemetry_type": tlm_type,
        "component_name": "test_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{tlm_type}_counter": 2,
            f"{tlm_type}_avg": 2,
            f"{tlm_type}_max": 3,
            f"{tlm_type}_min": 1
        }
    }
    test_tlm2 = {
        "telemetry_type": tlm_type,
        "component_name": "test_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{tlm_type}_counter": 2,
            f"{tlm_type}_avg": 3,
            f"{tlm_type}_max": 4,
            f"{tlm_type}_min": 2
        }
    }
    test_tlm1t1 = {
        "telemetry_type": tlm_type,
        "component_name": "test_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{tlm_type}_t1_counter": 20,
            f"{tlm_type}_t1_avg": 20,
            f"{tlm_type}_t1_max": 30,
            f"{tlm_type}_t1_min": 10
        }
    }
    test_tlm2t1 = {
        "telemetry_type": tlm_type,
        "component_name": "test_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{tlm_type}_t1_counter": 20,
            f"{tlm_type}_t1_avg": 30,
            f"{tlm_type}_t1_max": 40,
            f"{tlm_type}_t1_min": 20
        }
    }
    test_tlm1t2 = {
        "telemetry_type": tlm_type,
        "component_name": "test_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{tlm_type}_t2_counter": 200,
            f"{tlm_type}_t2_avg": 200,
            f"{tlm_type}_t2_max": 300,
            f"{tlm_type}_t2_min": 100
        }
    }
    test_tlm2t2 = {
        "telemetry_type": tlm_type,
        "component_name": "test_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{tlm_type}_t2_counter": 200,
            f"{tlm_type}_t2_avg": 300,
            f"{tlm_type}_t2_max": 400,
            f"{tlm_type}_t2_min": 200
        }
    }
    receiver = Receiver()
    receiver._incoming_tlms[tlm_type] = [test_tlm1, test_tlm2, test_tlm1t1, test_tlm2t1, test_tlm1t2, test_tlm2t2]
    return receiver


# you need to set the connection to opsview to run this test and select a tml_type associated to a passive check
def test_run_reporter():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = AvisoAuthReporter(Config(**config), receiver())
    reporter.run()


def test_process_tlms():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = AvisoAuthReporter(Config(**config), receiver())
    metrics = reporter.process_tlms()
    assert len(metrics) == 1
    assert len(metrics[0].get("metrics")) == 6
    assert len(list(filter(lambda m: m["m_value"] == 4, metrics[0].get("metrics")))) == 1
