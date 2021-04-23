# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json

from . import logger

ETCD_APP_NAME = "etcd"
AVISO_AUTH_APP_NAME = "aviso-auth"
AVISO_REST_APP_NAME = "aviso-rest"


class Receiver:
    """
    This class is in charge of processing the messages received
    """

    def __init__(self) -> None:
        # setup the income telemetry lists
        self._incoming_tlms = {}
        self._incoming_errors = {ETCD_APP_NAME: [], AVISO_AUTH_APP_NAME: [], AVISO_REST_APP_NAME: []}

    def process_message(self, message):
        """
        This method validates and parses the message received

        Args:
            message (str): message received
        Returns:
            bool: True if successfully parsed, False otherwise
        """
        # first check if it's a log message
        if message.startswith("<"):  # this is the PRI part of a syslog message
            if ETCD_APP_NAME in message:
                self._incoming_errors[ETCD_APP_NAME].append(message)
                logger.debug(f"{ETCD_APP_NAME} log received")
                return True
            elif AVISO_AUTH_APP_NAME in message:
                self._incoming_errors[AVISO_AUTH_APP_NAME].append(message)
                logger.debug(f"{AVISO_AUTH_APP_NAME} log received")
                return True
            elif AVISO_REST_APP_NAME in message:
                self._incoming_errors[AVISO_REST_APP_NAME].append(message)
                logger.debug(f"{AVISO_REST_APP_NAME} log received")
                return True
        else:
            # validate telemetry message
            try:
                message = json.loads(message)
                assert message.get("telemetry_type")
                assert message.get("component_name")
                assert message.get("hostname")
                assert message.get("time")
                assert message.get("telemetry")
            except Exception as e:
                logger.warn(f"Validation error in message received {message}, {e}")
                return False

            # adding to the right telemetry list
            tlm_type = message.get("telemetry_type")
            if tlm_type in self._incoming_tlms:
                self._incoming_tlms[tlm_type].append(message)
            else:
                self._incoming_tlms[tlm_type] = [message]
            logger.debug(f"{message} added to {tlm_type} buffer")

            return True

    def incoming_tlms(self, tlm_type):
        """
        Args:
            tlm_type (string): type of tlm to return
        Returns:
            list: list of tlms received of the specific type
        """
        return self._incoming_tlms.get(tlm_type)

    def incoming_errors(self, app_id):
        """
        Args:
            app_id (string): app required
        Returns:
            list: list of errors received for the specific app
        """
        return self._incoming_errors.get(app_id)

    def extract_incoming_tlms(self, tlm_type, clear=True):
        """
        Args:
            tlm_type (string): type of tlm to extract
            clear (bool): if True the buffer is cleared
        Returns:
            list: a copy list of tlms received of the specific type while
            the original list has been cleared.
        """
        if tlm_type in self._incoming_tlms:
            if clear:
                tlms = self._incoming_tlms.get(tlm_type).copy()
                self._incoming_tlms.get(tlm_type).clear()
            else:
                tlms = self._incoming_tlms.get(tlm_type)
            logger.debug(f"Telemetry list {tlm_type} extracted, {len(tlms)} tlms")
            return tlms
        else:
            return []

    def set_incoming_tlms(self, tlm_type, tlms):
        self._incoming_tlms[tlm_type] = tlms

    def extract_incoming_errors(self, app_id):
        """
        Args:
            app_id (string): app required
        Returns:
            list: a copy list of errors received of the specific app while
            the original list has been cleared.
        """
        if app_id in self._incoming_errors:
            errors = self._incoming_errors.get(app_id).copy()
            self._incoming_errors.get(app_id).clear()
            logger.debug(f"Error list {app_id} extracted, {len(errors)} tlms")
            return errors
        else:
            return []
