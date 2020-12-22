# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import base64
import json

import requests

from . import logger
from .custom_exceptions import InternalSystemError, InvalidInputError


class Authoriser:

    def __init__(self, config, cache=None):
        self.url = config["url"]
        self.req_timeout = config["req_timeout"]
        self.open_keys = config["open_keys"]
        self.protected_keys = config["protected_keys"]
        self.cert = config["cert"]
        self.key = config["key"]

        # assign explicitly a decorator to provide cache for _allowed_destinations
        if cache:
            self._allowed_destinations = cache.memoize(timeout=config["cache_timeout"])(
                self._allowed_destinations_impl)
        else:
            self._allowed_destinations = self._allowed_destinations_impl

    def _allowed_destinations_impl(self, username: str):
        """
        This method returns the destinations allowed to this username.
        Access this method by self._allowed_destinations.
        :param username:
        :return:
        - the list of allowed destinations associated to this username if valid
        - InternalSystemError otherwise
        """
        logger.debug(f"Request allowed destinations for username {username}")
        try:
            resp = requests.get(self.url, params={"id": username}, timeout=self.req_timeout, cert=(self.cert, self.key))
        except Exception as e:
            logger.exception(e)
            raise InternalSystemError(f'Error in retrieving destinations for {username}')

        if resp.status_code != 200:
            logger.error(f'Not able to retrieve destinations for {username} from {self.url}, '
                         f'status {resp.status_code}, {resp.reason}, {resp.content.decode()}')
            raise InternalSystemError(f'Error in retrieving destinations for {username}')

        resp_body = resp.json()
        if resp_body.get("success") != "yes":
            logger.error(f'Error in retrieving destinations for {username} from {self.url}, '
                         f'error {resp_body.get("error")}')
            raise InternalSystemError(f'Error in retrieving destinations for {username}')

        destinations = []
        if resp_body.get("destinationList"):
            destinations = list(map(lambda x: x.get("name"), resp_body.get("destinationList")))

        logger.debug(f"Username {username} is allowed to access: {destinations}")
        return destinations

    def is_authorised(self, username: str, request):
        """
        This method verifies that the user can access to the resource specified in the request
        :param username:
        :param request:
        :return:
        - True if authorised
        - False if not authorised
        - InternalSystemError otherwise
        """
        # we expect only JSON body
        body = request.json
        if body is None:
            logger.debug("Invalid request, Body cannot be empty")
            raise InvalidInputError("Invalid request, Body cannot be empty")

        # extract key
        if body.get("key") is None:
            logger.debug("key not found in the body")
            raise InvalidInputError("Invalid request, key not found in the body")

        backend_key = Authoriser._decode_to_bytes(body["key"]).decode()
        logger.debug(f"Request received to access to backend key {backend_key}")

        # check it's an allowed resource
        return self._is_backend_key_allowed(username, backend_key)

    def _is_backend_key_allowed(self, username: str, backend_key: str):
        """
        :param username:
        :param backend_key:
        :return:
        - True if authorised
        - False if not authorised
        - InternalSystemError otherwise
        """
        # first check if we are accessing to a open key space, open to everyone
        if len(list(filter(lambda x: backend_key.startswith(x), self.open_keys))) > 0:
            return True

        # now check if we are accessing to a key space that is open only to authorised users
        elif len(list(filter(lambda x: backend_key.startswith(x), self.protected_keys))) > 0:

            allowed_destinations = self._allowed_destinations(username)
            logger.debug(f"Destination allowed: {allowed_destinations}")

            # extract the destination
            destination = backend_key.split("/ec/diss/")[1].split("/")[0]
            return destination in allowed_destinations

        # denied access to anything else
        else:
            return False

    @staticmethod
    def _encode_to_str_base64(obj: any) -> str:
        """
        Internal method to translate the object passed in a field that could be accepted by etcd and the request library
        for the key or value. The request library accepts only strings encoded in base64 while etcd wants binaries for
        the key and value fields.
        :param obj:
        :return: a base64 string representation of the binary translation
        """
        if type(obj) is bytes:
            binary = obj
        elif type(obj) is str:
            binary = obj.encode()
        else:
            binary = str(obj).encode()

        return str(base64.b64encode(binary), "utf-8")

    @staticmethod
    def _decode_to_bytes(string: str) -> any:
        """
        Internal method to translate what is coming back from the notification server.
        The request library returns only string base64 encoded
        :param string:
        :return: the payload decoded from the base64 string representation
        """
        return base64.decodebytes(string.encode())

    @staticmethod
    def _incr_last_byte(path: str) -> bytes:
        """
        This function determines the end of the range required for a range call with the etcd3 API
        By incrementing the last byte of the input path, it allows to make a range call describing the input
        path as a branch rather than a leaf path.

        :param path: the path representing the start of the range
        :return: the path representing the end of the range
        """
        bytes_types = (bytes, bytearray)

        if not isinstance(path, bytes_types):
            if not isinstance(path, str):
                path = str(path)
            path = path.encode("utf-8")
        s = bytearray(path)

        # increment the last byte
        s[-1] = s[-1] + 1
        return bytes(s)
