# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import requests
from .collector import Collector
from ... import logger
from ...utils import encode_to_str_base64

class AvisoAuthCollector(Collector):
    '''
    Base class for aviso-rest collectors
    '''
    def __init__(self, *args, **kwargs):
        self.url = kwargs["url"]
        self.username = kwargs["username"]
        self.password = kwargs["password"]
        super().__init__(*args, **kwargs)

class ResponseTimeCollector(AvisoAuthCollector):
    '''
    This task performs a test notification and measure the response time
    '''

    WARNING_T = 5  # s
    CRITICAL_T = 10  # s
    TEST_PULL_KEY = "/ec/config/aviso/"

    def metric(self):
        status = 0
        message = f"Response time is nominal"
        resp_time = self.measure_test_pull(self.url)
        if resp_time > self.CRITICAL_T:
            status = 2
            message = f"Response time of {resp_time}s on {self.url}"
        elif resp_time > self.WARNING_T:
            status = 1
            message = f"Response time of {resp_time}s on {self.url}"
        elif resp_time == -1:
            status = 2
            message = f"Could not submit test pull on {self.url}"

        # build metric payload
        metric = {
            "name": self.metric_type.name,
            "status": status,
            "message": message,
            "m_name": "resp_time",
            "m_value": resp_time,
            "m_unit": "s"
        }
        logger.debug(f"Response time metric: {metric}")
        return metric

    def measure_test_pull(self, url):
        '''
        This method implements the call to submit a test pull
        :param url: endpoint to sent the request to
        :return: response time in seconds, -1 if failed
        '''

        url = url + "/v3/kv/range"
        header = {"Authorization": f"EmailKey {self.username}:{self.password}"}
        # body for a test pull
        body = {
            "key": encode_to_str_base64(self.TEST_PULL_KEY),
            "range_end": None,
            "keys_only": True,
        }
        # make the call
        logger.debug(f"Pull request: {body}")
        try:
            resp = requests.post(url, headers=header, json=body, timeout=self.req_timeout)
        except Exception as e:
            logger.error(f"Not able to submit test pull on {url}")
            logger.exception(e)
            return -1
        if resp.status_code != 200:
            logger.error(f"Test pull not returned on {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
            return -1

        return resp.elapsed.total_seconds()