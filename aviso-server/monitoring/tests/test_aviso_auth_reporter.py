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
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthReporter, AvisoAuthMetricType
from aviso_monitoring.receiver import Receiver, AVISO_AUTH_APP_NAME
from aviso_monitoring.config import Config

time_type = AvisoAuthMetricType.auth_resp_time.name
config = {
    "aviso_auth_reporter": {
        "enabled": True,
        "frequency": 2,  # in minutes
        "tlms": {
            "auth_resp_time": {
                "sub_tlms": ["t1", "t2"]
            }
        }
    },
    # this are the setting for sending the telemetry to a monitoring server like Opsview
    "monitor_servers": [{
        "url": "https://monitoring-dev.ecmwf.int/rest",
        "username": "TBD",
        "password": "TBD",
        "service_host": "aviso",
    }],
    "udp_server": {
        "host": "127.0.0.1",
        "port": 1110
    }
}


def receiver():
    time_tlm1 = {
        "telemetry_type": time_type,
        "component_name": "time_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{time_type}_counter": 2,
            f"{time_type}_avg": 2,
            f"{time_type}_max": 3,
            f"{time_type}_min": 1
        }
    }
    time_tlm2 = {
        "telemetry_type": time_type,
        "component_name": "time_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{time_type}_counter": 2,
            f"{time_type}_avg": 3,
            f"{time_type}_max": 4,
            f"{time_type}_min": 2
        }
    }
    time_tlm1t1 = {
        "telemetry_type": time_type,
        "component_name": "time_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{time_type}_t1_counter": 20,
            f"{time_type}_t1_avg": 20,
            f"{time_type}_t1_max": 30,
            f"{time_type}_t1_min": 10
        }
    }
    time_tlm2t1 = {
        "telemetry_type": time_type,
        "component_name": "time_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{time_type}_t1_counter": 20,
            f"{time_type}_t1_avg": 30,
            f"{time_type}_t1_max": 40,
            f"{time_type}_t1_min": 20
        }
    }
    time_tlm1t2 = {
        "telemetry_type": time_type,
        "component_name": "time_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{time_type}_t2_counter": 200,
            f"{time_type}_t2_avg": 200,
            f"{time_type}_t2_max": 300,
            f"{time_type}_t2_min": 100
        }
    }
    time_tlm2t2 = {
        "telemetry_type": time_type,
        "component_name": "time_comp",
        "hostname": "me",
        "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
        "telemetry": {
            f"{time_type}_t2_counter": 200,
            f"{time_type}_t2_avg": 300,
            f"{time_type}_t2_max": 400,
            f"{time_type}_t2_min": 200
        }
    }
    
    err_auth_log = '<191>1 2021-04-12T09:00:08.931717+00:00 aviso-auth-green-7f6d59848f-cg6zv aviso-auth 49 - [origin software="aviso"]  {"asctime": "2021-04-12 09:00:08,931", "hostname": "aviso-auth-green-7f6d59848f-cg6zv", "process": 49, "thread": 140428749499272, "name": "aviso-monitoring", "filename": "time_collector.py", "lineno": 38, "levelname": "ERROR", "message": "Time collected"}'

    receiver = Receiver()
    receiver._incoming_tlms[time_type] = [time_tlm1, time_tlm2, time_tlm1t1, time_tlm2t1, time_tlm1t2, time_tlm2t2]
    receiver._incoming_errors[AVISO_AUTH_APP_NAME] = [err_auth_log]
    return receiver


# you need to set the connection to opsview to run this test and select a tml_type associated to a passive check
def test_run_reporter():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = AvisoAuthReporter(Config(**config), receiver())
    reporter.run()


def test_process_tlms():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = AvisoAuthReporter(Config(**config), receiver())
    metrics = reporter.process_messages()
    assert len(metrics) == 3
    timer = list(filter(lambda m: m["name"] == time_type, metrics))[0]
    assert len(timer.get("metrics")) == 6
    assert len(list(filter(lambda m: m["m_value"] == 4, timer.get("metrics")))) == 1
    errors = list(filter(lambda m: m["name"] == "auth_error_log", metrics))[0]
    assert errors["status"] == 2