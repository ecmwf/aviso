import datetime
import json
import os
import socket
import time

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
