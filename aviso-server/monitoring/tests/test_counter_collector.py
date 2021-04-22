# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import os
from random import random
from time import sleep

from aviso_monitoring import logger
from aviso_monitoring.collector.config import Config
from aviso_monitoring.collector.count_collector import UniqueCountCollector
from aviso_monitoring.udp_server import UdpServer


def do_something(fix=False):
    if fix:
        return 0
    else:
        return random()

telemetry_type = "test_counter"

collector_config = {
    "transmitter": {
        "monitoring_server_host": "127.0.0.1",
        "monitoring_server_port": 1113,
        "component_name": "test_component",
        "frequency": 2,
    },
    "enabled": True,
}

upd_server_config = {
    "host": "127.0.0.1",
    "port": 1113,
    "buffer_size": 64 * 1024
}

received = False


class ReceiverMock:

    def process_message(self, message):
        logger.debug(f"Message received: {message}")
        message = json.loads(message)
        assert message.get("telemetry_type") == telemetry_type
        assert message.get("component_name") == collector_config.get("transmitter").get("component_name")
        assert message.get("hostname")
        assert message.get("time")
        assert message.get("telemetry")
        assert message.get("telemetry").get(f"{telemetry_type}_counter") == 6
        assert message.get("telemetry").get(f"{telemetry_type}_values")
        global received
        received = True


def test_count():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])

    # create the UDP server with mock ServiceRegister
    udp_server = UdpServer(upd_server_config, ReceiverMock())
    udp_server.start()

    # create the collector
    counter = UniqueCountCollector(Config(**collector_config), tlm_type=telemetry_type)

    # call the function
    for i in range(5):
        counter(do_something)

    for i in range(5):
        counter(do_something, args=True) # this will return always only the same

    # wait to receive it
    sleep(5)
    assert received
    udp_server.stop()


