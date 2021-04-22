# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import os

from aviso_monitoring import logger
from aviso_monitoring.config import Config
from aviso_monitoring.receiver import AVISO_REST_APP_NAME, Receiver
from aviso_monitoring.reporter.aviso_rest_reporter import (
    AvisoRestMetricType,
    AvisoRestReporter,
)

config = {
    "aviso_rest_reporter": {
        "enabled": True,
        "frequency": 2,  # in minutes

    },
    # this are the setting for sending the telemetry to a monitoring server like Opsview
    "monitor_servers": [{
        "url": "https://monitoring-dev.ecmwf.int/rest",
        "username": "TBD",
        "password": "TBD",
        "service_host": "aviso"
    }],
    "udp_server": {
        "host": "127.0.0.1",
        "port": 1112
    }
}

tlm_type = AvisoRestMetricType.rest_resp_time.name

def receiver():
    tlms = [
        {'telemetry_type': tlm_type, 
        'component_name': 'aviso-rest', 
        'hostname': 'aviso-rest-blue-55f6dd8876-6kg5k', 
        'time': 1615206256.11515, 
        'telemetry': {
            tlm_type+'_counter': 2, 
            tlm_type+'_avg': 2, 
            tlm_type+'_max': 3, 
            tlm_type+'_min': 1
        }}, 
        {'telemetry_type': tlm_type, 
        'component_name': 'aviso-rest', 
        'hostname': 'aviso-rest-blue-55f6dd8876-6kg5k', 
        'time': 1615206256.889785, 
        'telemetry': {
            tlm_type+'_counter': 2, 
            tlm_type+'_avg': 3, 
            tlm_type+'_max': 4, 
            tlm_type+'_min': 2
        }}
    ]

    err_rest_log = '<191>1 2021-04-12T09:19:12.252093+00:00 aviso-rest-green-9c975dc86-mvplw aviso-rest 58 - [origin software="aviso"]  {"asctime": "2021-04-12 09:19:12,252", "hostname": "aviso-rest-green-9c975dc86-mvplw", "process": 58, "thread": 139943263611624, "name": "aviso-monitoring", "filename": "transmitter.py", "lineno": 74, "levelname": "ERROR", "message": "Telemetry transmitter cycle completed"}'

    receiver = Receiver()
    receiver._incoming_tlms[tlm_type] = tlms
    receiver._incoming_errors[AVISO_REST_APP_NAME] = [err_rest_log]
    return receiver


# you need to set the connection to opsview to run this test and select a tml_type associated to a passive check
def test_run_reporter():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = AvisoRestReporter(Config(**config), receiver())
    reporter.run()


def test_process_tlms():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    reporter = AvisoRestReporter(Config(**config), receiver())
    metrics = reporter.process_messages()
    assert len(metrics) == 3
    assert len(metrics[0].get("metrics")) == 3
    assert len(list(filter(lambda m: m["m_value"] == 4, metrics[0].get("metrics")))) == 1
    errors = list(filter(lambda m: m["name"] == "rest_error_log", metrics))[0]
    assert errors["status"] == 2