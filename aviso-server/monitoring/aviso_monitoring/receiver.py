# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from . import logger


class Receiver:
    """
    This class is in charge of processing the messages received
    """

    def __init__(self) -> None:
        # setup the income telemetry lists
        self._incoming_tlms = {}

    def process_message(self, message):
        """
        This method validates and parses the message received

        Args:
            message (Dict): message received
        Returns:
            bool: True if successfully parsed, False otherwise
        """
        logger.debug(f"Message received")

        # validate message
        try:
            assert message.get("telemetry_type")
            assert message.get("component_name")
            assert message.get("hostname")
            assert message.get("time")
            assert message.get("telemetry")
        except AssertionError as e:
            logger.warn(f"Validation error in message received, {e}")
            return False

        # adding to the right telemetry list
        tlm_type = message.get("telemetry_type")
        if tlm_type in self._incoming_tlms:
            self._incoming_tlms[tlm_type].append(message)
        else:
            self._incoming_tlms[tlm_type] = [message]

        return True

    def incoming_tlms(self, tlm_type):
        """
        Args:
            tlm_type (string): type of tlm to return
        Returns:
            list: list of tlms received of the specific type
        """
        return self._incoming_tlms.get(tlm_type)

    def extract_incoming_tlms(self, tlm_type):
        """
        Args:
            tlm_type (string): type of tlm to extract
        Returns:
            list: a copy list of tlms received of the specific type while
            the original list has been cleared.
        """
        if tlm_type in self._incoming_tlms:
            tlms = self._incoming_tlms.get(tlm_type).copy()
            self._incoming_tlms.get(tlm_type).clear()
            logger.debug(f"Telemetry list {tlm_type} extracted, {len(tlms)} tlms")
            return tlms
        else:
            return []
