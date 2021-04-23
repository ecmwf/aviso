# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import requests
from aviso_monitoring.collector.time_collector import TimeCollector
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthMetricType

from . import logger
from .custom_exceptions import (
    BackendUnavailableException,
    InternalSystemError,
    InvalidInputError,
)


class BackendAdapter:
    def __init__(self, config):
        backend_conf = config.backend
        self.url = f"{backend_conf['url']}{backend_conf['route']}"
        self.req_timeout = backend_conf["req_timeout"]

        # assign explicitly a decorator to monitor the forwarding
        if backend_conf["monitor"]:
            self.timer = TimeCollector(
                config.monitoring, tlm_type=AvisoAuthMetricType.auth_resp_time.name, tlm_name="be"
            )
            self.forward = self.timed_forward
        else:
            self.forward = self.forward_impl

    def timed_forward(self, request):
        """
        This method is an explicit decorator of the forward_impl method to provide time performance monitoring
        """
        return self.timer(self.forward_impl, args=request)

    def forward_impl(self, request):
        """
        This method forwards the request to the backend configured
        :param request:
        :return: response content from backend
        - InternalSystemError otherwise
        """
        if request.data is None:
            raise InvalidInputError("Invalid request, data cannot be empty")
        try:
            resp = requests.post(self.url, data=request.data, timeout=self.req_timeout)
            # raise an error for http cases
            resp.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            message = f"Error connecting to backend {self.url}, {str(errh)}"
            if resp.status_code == 400 and "required revision has been compacted" in resp.json().get("error"):
                raise InvalidInputError("History not available")
            if resp.status_code == 408 or (resp.status_code >= 500 and resp.status_code < 600):
                logger.warning(message)
                raise BackendUnavailableException(f"Error connecting to backend")
            else:
                logger.error(message)
                raise InternalSystemError(f"Error connecting to backend, please contact the support team")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
            logger.warning(f"Error connecting to backend {self.url}, {str(err)}")
            raise BackendUnavailableException(f"Error connecting to backend")
        except Exception as e:
            logger.exception(e)
            raise InternalSystemError(f"Error connecting to backend, please contact the support team")

        # just in case requests does not always raise an error
        if resp.status_code != 200:
            logger.debug(
                f"Error in forwarding requests to backend {self.url}, status {resp.status_code}, {resp.reason}, "
                f"{resp.content.decode()}"
            )
            raise InternalSystemError(f"Error connecting to backend, please contact the support team")
        else:
            return resp.content
