# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import requests
from . import logger
from .custom_exceptions import InvalidInputError, InternalSystemError


class BackendAdapter:

    def __init__(self, config):
        self.url = f"{config['url']}{config['route']}"
        self.req_timeout = config["req_timeout"]

    def forward(self, request):
        """
        This method forwards the request to the backend configured
        :param request:
        :return: response content from backend
        """
        if request.data is None:
            raise InvalidInputError("Invalid request, data cannot be empty")
        try:
            resp = requests.post(self.url, data=request.data, timeout=self.req_timeout)
        except Exception as e:
            logger.exception(e)
            raise InternalSystemError(f'Error connecting to backend')

        if resp.status_code != 200:
            logger.debug(
                f'Error in forwarding requests to backend {self.url}, status {resp.status_code}, {resp.reason}, '
                f'{resp.content.decode()}')
            if resp.status_code == 400 and 'required revision has been compacted' in resp.json().get("error"):
                raise InvalidInputError("History not available")
            else:
                raise InternalSystemError(f'Error connecting to backend')
        else:
            return resp.content













