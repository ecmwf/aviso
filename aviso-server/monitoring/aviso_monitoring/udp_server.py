# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import socket
from threading import Thread
from typing import Dict

from . import logger

msgFromServer = "Hello UDP Client"
bytesToSend = str.encode(msgFromServer)


class UdpServerException(Exception):
    pass


class UdpServer(Thread):

    def __init__(self, config: Dict, receiver):
        super(UdpServer, self).__init__()
        self.config = config
        self.receiver = receiver
        # run in the background
        self.setDaemon(True)
        # Create a datagram socket
        self.server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # Bind to address and ip
        try:
            self.server.bind((config.get("host"), config.get("port")))
        except OSError as e:
            logger.error(f"Could not bind UDP server to {config.get('host')}:{config.get('port')}")
            logger.debug("", exc_info=True)
            raise UdpServerException(e)
        logger.debug("UDP server created")
        self.go = True

    def stop(self):
        self.go = False
        self.server.close()
        logger.debug("Terminating UDP server")

    def run(self):
        if self.server.getsockname()[1] == 0:
            logger.debug("Terminating UDP server as not bound")
        else:
            logger.debug("UDP server listening...")
            # Listen for incoming datagrams
            while self.go:
                bytes_address_pair = self.server.recvfrom(self.config.get("buffer_size"))
                message_str = bytes_address_pair[0].decode()
                address = bytes_address_pair[1]
                logger.debug(f"Message received from {address[0]}:{address[1]}, content: {message_str}")
                # send message to the receiver
                self.receiver.process_message(message_str)



