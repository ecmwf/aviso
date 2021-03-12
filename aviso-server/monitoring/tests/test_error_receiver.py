import os
import json
import socket
import time
from aviso_monitoring import logger
import datetime
from aviso_monitoring.udp_server import UdpServer
from aviso_monitoring.receiver import Receiver, ETCD_APP_ID, AVISO_REST_APP_ID, AVISO_AUTH_APP_ID

warn_etcd_log = '<181>1 2021-03-09T07:36:55+00:00 aviso-etcd-0 2021-03-09 - - [meta sequenceId="1"] 07:36:55.088752 W | etcdmain: no data-dir provided, using default data-dir ./default.etcd'

err_etcd_log = '<181>1 2021-03-09T07:36:55+00:00 aviso-etcd-0 2021-03-09 - - [meta sequenceId="1"] 2021-01-25 15:12:03.354688 E | etcdserver: publish error: etcdserver: request timed out, possibly due to connection lost'

err_rest_log = 'Mar  9 07:18:34 10-44-0-29 {"asctime": "2021-03-09 07:18:34,385", "hostname": "aviso-rest-blue-56698cb9bc-4s2z7", "process": 42, "thread": 140026491313032, "name": "root", "filename": "frontend.py", "lineno": 73, "levelname": "ERROR", "message": "Value tc3_lace is not valid"}'

err_auth_log = 'Mar  9 07:18:34 10-44-0-29 {"asctime": "2021-03-09 07:18:34,385", "hostname": "aviso-auth-blue-56698cb9bc-4s2z7", "process": 42, "thread": 140026491313032, "name": "root", "filename": "frontend.py", "lineno": 73, "levelname": "ERROR", "message": "Value tc3_lace is not valid"}'


upd_server_config = {
    "host": "127.0.0.1",
    "port": 1114,
    "buffer_size": 64 * 1024
}


def test_send_etcd_log():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])

    # create the UDP server
    receiver = Receiver()
    udp_server = UdpServer(upd_server_config, receiver)
    udp_server.start()

    # send 2 etcd logs, 1 auth, 1 rest
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    assert s.sendto(warn_etcd_log.encode(), (upd_server_config["host"], upd_server_config["port"]))
    assert s.sendto(err_etcd_log.encode(), (upd_server_config["host"], upd_server_config["port"]))
    assert s.sendto(err_rest_log.encode(), (upd_server_config["host"], upd_server_config["port"]))
    assert s.sendto(err_auth_log.encode(), (upd_server_config["host"], upd_server_config["port"]))
    s.close()

    time.sleep(1)
    # verify they are received
    assert len(receiver.incoming_errors(ETCD_APP_ID)) == 2 
    assert len(receiver.incoming_errors(AVISO_REST_APP_ID)) == 1
    assert len(receiver.incoming_errors(AVISO_AUTH_APP_ID)) == 1
    # verify the copy & clear
    assert len(receiver.extract_incoming_errors(ETCD_APP_ID)) == 2
    assert len(receiver.incoming_errors(ETCD_APP_ID)) == 0  

    udp_server.stop()

