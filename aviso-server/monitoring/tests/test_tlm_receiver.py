# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import json
import os
import socket
import time

import pytest
from aviso_monitoring import logger
from aviso_monitoring.receiver import Receiver
from aviso_monitoring.udp_server import UdpServer

test_message = {
    "telemetry_type": "type1",
    "component_name": "test_comp",
    "hostname": "me",
    "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
    "telemetry": {
        "test_avg": 1.2,
    },
}

upd_server_config = {"host": "127.0.0.1", "port": 1117, "buffer_size": 64 * 1024}


def test_send_message():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    # create the UDP server
    receiver = Receiver()
    udp_server = UdpServer(upd_server_config, receiver)
    udp_server.start()

    # send 2 test message
    byte_message = json.dumps(test_message).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    assert s.sendto(byte_message, (upd_server_config["host"], upd_server_config["port"]))
    assert s.sendto(byte_message, (upd_server_config["host"], upd_server_config["port"]))
    s.close()

    time.sleep(1)
    # verify they are received
    assert len(receiver.incoming_tlms(test_message["telemetry_type"])) == 2

    # send message of different type
    test_message2 = test_message.copy()
    test_message2["telemetry_type"] = "type2"
    byte_message = json.dumps(test_message2).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    assert s.sendto(byte_message, (upd_server_config["host"], upd_server_config["port"]))
    s.close()

    time.sleep(1)
    # verify it's received properly
    assert len(receiver.incoming_tlms(test_message["telemetry_type"])) == 2
    assert len(receiver.incoming_tlms(test_message2["telemetry_type"])) == 1

    # send a wrong message of same type
    test_message2.pop("component_name")
    byte_message = json.dumps(test_message2).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    assert s.sendto(byte_message, (upd_server_config["host"], upd_server_config["port"]))
    s.close()

    time.sleep(1)
    # verify it's NOT received properly
    assert len(receiver.incoming_tlms(test_message["telemetry_type"])) == 2
    assert len(receiver.incoming_tlms(test_message2["telemetry_type"])) == 1

    udp_server.stop()


@pytest.mark.skip()
def test_send_log():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    err_rest_log1 = '<191>1 2021-04-12T13:18:52.322093+00:00 aviso-rest-green-9c975dc86-mvplw aviso-rest 58 - [origin software="aviso"]  {"asctime": "2021-07-13 13:18:52,325", "hostname": "aviso-rest-green-59c4cc8bbc-grkct", "process": 48, "thread": 140014721616776, "name": "root", "filename": "frontend.py", "lineno": 76, "levelname": "ERROR", "message": "<_InactiveRpcError of RPC that terminated with:\n\tstatus = StatusCode.UNAVAILABLE\n\tdetails = "failed to connect to all addresses"\n\tdebug_error_string = "{"created":"@1626182332.324220765","description":"Failed to pick subchannel","file":"src/core/ext/filters/client_channel/client_channel.cc","file_line":5420,"referenced_errors":[{"created":"@1626182332.324214424","description":"failed to connect to all addresses","file":"src/core/ext/filters/client_channel/lb_policy/pick_first/pick_first.cc","file_line":398,"grpc_status":14}]}"\n>", "exc_info": "Traceback (most recent call last):\n  File "/aviso/pyaviso/engine/etcd_grpc_engine.py", line 95, in pull\n    metadata=self._server.metadata,\n  File "/usr/local/lib/python3.6/site-packages/grpc/_channel.py", line 946, in __call__\n    return _end_unary_response_blocking(state, call, False, None)\n  File "/usr/local/lib/python3.6/site-packages/grpc/_channel.py", line 849, in _end_unary_response_blocking\n    raise _InactiveRpcError(state)\ngrpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that terminated with:\n\tstatus = StatusCode.UNAVAILABLE\n\tdetails = "failed to connect to all addresses"\n\tdebug_error_string = "{"created":"@1626182332.324220765","description":"Failed to pick subchannel","file":"src/core/ext/filters/client_channel/client_channel.cc","file_line":5420,"referenced_errors":[{"created":"@1626182332.324214424","description":"failed to connect to all addresses","file":"src/core/ext/filters/client_channel/lb_policy/pick_first/pick_first.cc","file_line":398,"grpc_status":14}]}"\n>\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File "/usr/local/lib/python3.6/site-packages/flask/app.py", line 1950, in full_dispatch_request\n    rv = self.dispatch_request()\n  File "/usr/local/lib/python3.6/site-packages/flask/app.py", line 1936, in dispatch_request\n    return self.view_functions[rule.endpoint](**req.view_args)\n  File "/aviso/aviso-server/rest/aviso_rest/frontend.py", line 113, in notify\n    self.timed_notify(notification, config=self.config.aviso)\n  File "/aviso/aviso-server/rest/aviso_rest/frontend.py", line 125, in timed_notify\n    return self.timer(self.notification_manager.notify, args=(notification, config))\n  File "/aviso/aviso-server/monitoring/aviso_monitoring/collector/time_collector.py", line 35, in __call__\n    res = f(*args, **kwargs)\n  File "/aviso/pyaviso/notification_manager.py", line 199, in notify\n    listener_schema = config.schema_parser.parser().load(config)\n  File "/aviso/pyaviso/event_listeners/listener_schema_parser.py", line 54, in load\n    remote_schema_files = config_manager.pull(config.notification_engine.service)\n  File "/aviso/pyaviso/service_config_manager.py", line 121, in pull\n    kvs = self._engine.pull(service_key, key_only)\n  File "/aviso/pyaviso/engine/etcd_grpc_engine.py", line 107, in pull\n    raise EngineException(e)\npyaviso.custom_exceptions.EngineException: <_InactiveRpcError of RPC that terminated with:\n\tstatus = StatusCode.UNAVAILABLE\n\tdetails = "failed to connect to all addresses"\n\tdebug_error_string = "{"created":"@1626182332.324220765","description":"Failed to pick subchannel","file":"src/core/ext/filters/client_channel/client_channel.cc","file_line":5420,"referenced_errors":[{"created":"@1626182332.324214424","description":"failed to connect to all addresses","file":"src/core/ext/filters/client_channel/lb_policy/pick_first/pick_first.cc","file_line":398,"grpc_status":14}]}"\n>"}'  # noqa: E501

    upd_server_config = {"host": "127.0.0.1", "port": 1111}

    # send 2 etcd logs, 1 auth, 1 rest
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(1000):
        assert s.sendto(err_rest_log1.encode(), (upd_server_config["host"], upd_server_config["port"]))
        time.sleep(0.001)
    s.close()
