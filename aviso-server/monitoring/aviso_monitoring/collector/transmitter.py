# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from threading import Thread
import time
import datetime
import json
import socket

from .. import logger


class Transmitter(Thread):
    """
    This class encapsulates the capabilities required to transmit the telemetry
    to the monitoring server. It runs as a background thread and regularly scans
    the telemetry buffer and aggregates the telemetries.
    """

    def __init__(self, config, tlm_buffer, aggregate_tlms, telemetry_type):
        super(Transmitter, self).__init__()
        self.monitoring_server_host = config["monitoring_server_host"]
        self.monitoring_server_port = config["monitoring_server_port"]
        self.component_name = config["component_name"]
        self.frequency = config["frequency"]  # in seconds
        self.tlm_buffer = tlm_buffer
        self.aggregate_tlms = aggregate_tlms
        self.telemetry_type = telemetry_type
        # run in the background
        self.setDaemon(True)

    def run(self):
        """
        Main method of telemetry transmitter. It runs its lifecycle
        """
        logger.debug("Telemetry transmitter started")
        while True:
            # wait for next round
            time.sleep(self.frequency)
            # process the telemetry
            self.transmitter_cycle()

    def transmitter_cycle(self):
        """
        This method implements the lifecycle of the telemetry transmitter that is made of:
        1) reading and clearing the buffer
        2) aggregating the data
        3) transmitting the aggregated tlm

        Returns:
            bool: True if successful False otherwise
        """
        # logger.debug("Telemetry transmitter cycle started")

        if len(self.tlm_buffer):  # don't do anything if the buffer is empty

            # read the event buffer and clear it
            tlms = self.tlm_buffer.copy()
            logger.debug(f"{len(tlms)} TLMs found in the buffer")
            self.tlm_buffer.clear()

            # aggregate the telemetries
            agg_tlm = self.aggregate_tlms(tlms)

            # send the telemetry
            if not self.transmit_tlm(agg_tlm):
                return False

        logger.debug("Telemetry transmitter cycle completed")
        return True

    def transmit_tlm(self, tlm):
        """
        This method transmits the tml as UPD packet to the monitoring server

        Args:
            tlm (Dict): telemetry to transmit

        Returns:
            bool: True if successful False otherwise
        """
        # prepare message to send as UDP packet
        message = {
            "telemetry_type": self.telemetry_type,
            "component_name": self.component_name,
            "hostname": socket.gethostname(),
            "time": datetime.datetime.timestamp(datetime.datetime.utcnow()),
            "telemetry": tlm
        }
        # send the message
        byte_message = json.dumps(message).encode()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            logger.debug(f"Sending tlm {message} to {self.monitoring_server_host}:{self.monitoring_server_port}")
            res = s.sendto(byte_message, (self.monitoring_server_host, self.monitoring_server_port))
            logger.debug(f"Tlm sending return: {res}")
        except Exception as e:
            logger.warn(f"Telemetry could not be sent, {e}")
            return False
        s.close()
        return True
