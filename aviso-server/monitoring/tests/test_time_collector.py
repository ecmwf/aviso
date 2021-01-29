# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from time import sleep
import os
from aviso_monitoring.udp_server import UdpServer
from aviso_monitoring.collector.time_collector import TimeCollector
from aviso_monitoring.collector.config import Config
from aviso_monitoring import logger


def take_some_time(seconds=0.1, flag=False, flag2=True):
    sleep(seconds)
    print(flag)
    print(flag2)
    return flag2


collector_config = {
    "transmitter": {
        "monitoring_server_host": "127.0.0.1",
        "monitoring_server_port": 1111,
        "component_name": "test_component",
        "frequency": 2,
    },
    "enabled": True,
    "telemetry_type": "test_time",
}

upd_server_config = {
    "host": "127.0.0.1",
    "port": 1111,
    "buffer_size": 64 * 1024
}

received = False


class ReceiverMock:

    def process_message(self, message):
        logger.debug(f"Message received: {message}")
        assert message.get("telemetry_type") == collector_config.get("telemetry_type")
        assert message.get("component_name") == collector_config.get("transmitter").get("component_name")
        assert message.get("hostname")
        assert message.get("time")
        assert message.get("telemetry")
        assert message.get("telemetry").get(f"{collector_config.get('telemetry_type')}_avg") > 0
        assert message.get("telemetry").get(f"{collector_config.get('telemetry_type')}_counter") == 10
        global received
        received = True


def test_measure_time():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])

    # create the UDP server with mock ServiceRegister
    udp_server = UdpServer(upd_server_config, ReceiverMock())
    udp_server.start()

    # create the collector
    timer = TimeCollector(Config(**collector_config))

    # call the function
    for i in range(10):
        timer(take_some_time, args=0.1)

    # wait to receive it
    sleep(2)
    assert received
    udp_server.stop()


def test_calling_timer():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])

    # create the collector
    timer = TimeCollector(Config(**collector_config))

    assert timer(take_some_time)
    timer(take_some_time, args=0.1)
    timer(take_some_time, args=[0.1])
    assert not timer(take_some_time, args=(0.1, True, False))
    timer(take_some_time, args=[0.1, False])
    timer(take_some_time, kwargs={"flag": True})
    timer(take_some_time, args=0.2, kwargs={"flag": True})
