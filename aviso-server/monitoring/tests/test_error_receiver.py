# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import socket
import time

from aviso_monitoring import logger
from aviso_monitoring.receiver import (
    AVISO_AUTH_APP_NAME,
    AVISO_REST_APP_NAME,
    ETCD_APP_NAME,
    Receiver,
)
from aviso_monitoring.udp_server import UdpServer

warn_etcd_log = '<189>1 2021-08-21T21:11:18+00:00 aviso-etcd-1 etcd - - [origin enterpriseId="7464" \
    software="aviso"] {"level":"warn","ts":"2021-08-21T21:11:18.819Z","caller":"rafthttp/probing_status.go:68", \
    "msg":"prober detected unhealthy status","round-tripper-name":"ROUND_TRIPPER_RAFT_MESSAGE", \
    "remote-peer-id":"ae1516e20f24c2ba","rtt":"2.5562ms","error":"dial tcp: i/o timeout"}'

err_etcd_log = '<189>1 2021-08-21T21:11:18+00:00 aviso-etcd-1 etcd - - [origin enterpriseId="7464" \
    software="aviso"] {"level":"error","ts":"2021-08-21T21:11:18.819Z","caller":"rafthttp/probing_status.go:68", \
    "msg":"prober detected unhealthy status","round-tripper-name":"ROUND_TRIPPER_RAFT_MESSAGE", \
    "remote-peer-id":"ae1516e20f24c2ba","rtt":"2.5562ms","error":"etcdserver: request timed out, \
    possibly due to connection lost"}'

err_rest_log = '<191>1 2021-04-12T09:19:12.252093+00:00 aviso-rest-green-9c975dc86-mvplw aviso-rest 58 - \
    [origin software="aviso"]  {"asctime": "2021-03-09 07:18:34,385", "hostname": "aviso-rest-blue-56698cb9bc-4s2z7", \
        "process": 42, "thread": 140026491313032, "name": "root", "filename": "frontend.py", "lineno": 73, "levelname":\
             "ERROR", "message": "Value tc3_lace is not valid"}'

err_auth_log = '<191>1 2021-04-12T09:19:12.252093+00:00 aviso-auth-green-9c975dc86-mvplw aviso-auth 58 - \
    [origin software="aviso"]  {"asctime": "2021-03-09 07:18:34,385", "hostname": "aviso-auth-blue-56698cb9bc-4s2z7",\
         "process": 42, "thread": 140026491313032, "name": "root", "filename": "frontend.py", "lineno": 73, \
             "levelname": "ERROR", "message": "Value tc3_lace is not valid"}'


upd_server_config = {"host": "127.0.0.1", "port": 1114, "buffer_size": 64 * 1024}


def test_send_etcd_log():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

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
    assert len(receiver.incoming_errors(ETCD_APP_NAME)) == 2
    assert len(receiver.incoming_errors(AVISO_REST_APP_NAME)) == 1
    assert len(receiver.incoming_errors(AVISO_AUTH_APP_NAME)) == 1
    # verify the copy & clear
    assert len(receiver.extract_incoming_errors(ETCD_APP_NAME)) == 2
    assert len(receiver.incoming_errors(ETCD_APP_NAME)) == 0

    udp_server.stop()
