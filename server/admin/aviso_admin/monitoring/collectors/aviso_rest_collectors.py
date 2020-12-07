# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import requests
import datetime

from .collector import Collector
from ... import logger

class AvisoRestCollector(Collector):
    '''
    Base class for aviso-rest collectors
    '''
    def __init__(self, *args, **kwargs):
        self.url = kwargs["url"]
        super().__init__(*args, **kwargs)

class ResponseTimeCollector(AvisoRestCollector):
    '''
    This task performs a test notification and measure the response time
    '''

    WARNING_T = 5  # s
    CRITICAL_T = 10  # s

    def metric(self):
        status = 0
        message = f"Response time is nominal"
        resp_time = self.measure_test_notification(self.url)
        if resp_time > self.CRITICAL_T:
            status = 2
            message = f"Response time of {resp_time}s on {self.url}"
        elif resp_time > self.WARNING_T:
            status = 1
            message = f"Response time of {resp_time}s on {self.url}"
        elif resp_time == -1:
            status = 2
            message = f"Could not submit test notification on {self.url}"

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

    def measure_test_notification(self, url):
        '''
        This method implements the call to submit a test notification
        :param url: endpoint to sent the notification to
        :return: response time in seconds, -1 if failed
        '''

        url = f"{url}/api/v1/notification"
        # body for a test notification
        body = {
            "type": "aviso", 
            "data": {
                "event": "mars", 
                "request": { "class": "od", "date": "20000101", "domain": "g", "expver": "1", "step": "0", "stream": "enfo", "time": "0" }
                }, 
            "datacontenttype": "application/json", 
            "id": "0c02fdc5-148c-43b5-b2fa-cb1f590369ff", 
            "source": "/host/user", 
            "specversion": "1.0", 
            "time": "2000-01-01T00:00:00.000Z"
        }
        try:
            resp = requests.post(url, json=body, timeout=self.req_timeout)
        except Exception as e:
            logger.error(f"Not able to submit test notification on {url}")
            logger.exception(e)
            return -1
        if resp.status_code != 200:
            logger.error(f"Not able to submit test notification mon {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
            return -1

        return resp.elapsed.total_seconds()