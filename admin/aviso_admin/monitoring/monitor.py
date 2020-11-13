# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC
import json
import requests
import urllib3
from .. import logger

class Monitor(ABC):

    def __init__(self, config):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.ms_url = config["monitor_server"]["url"]
        self.ms_service_host = config["monitor_server"]["service_host"]
        self.ms_req_timeout = config["monitor_server"]["req_timeout"]
        self.ms_username = config["monitor_server"]["username"]
        self.ms_password = config["monitor_server"]["password"]

    def ms_authenticate(self):
        '''
        This method authenticate to the monitoring server
        :return: token if succefully authenticated, None otherwise
        '''
        headers = {"Content-type": "application/json", "Accept": "application/json"}
        data = {"username": self.ms_username, "password": self.ms_password}
        try:
            resp = requests.post(self.ms_url + "/login", data=json.dumps(data), headers=headers,
                                 verify=False, timeout=self.ms_req_timeout)
        except Exception as e:
            logger.error("Not able to authenticate with monitoring server")
            logger.exception(e)
            return None
        if resp.status_code != 200:
            logger.error(f"Not able to authenticate with monitoring server for {self.ms_username} from {self.ms_url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
            return None

        return json.loads(resp.text)["token"]

    def post_metric(self, token, metric):
        '''
        This method send the metric passed to the monitoring server
        :param token: authentication token
        :param metric:
        :return: True if successful, False otherwise
        '''
        headers = {"Content-type": "application/json", "X-Opsview-Username": f"{self.ms_username}", "X-Opsview-Token": token}
        url = f"{self.ms_url}/detail?hostname={self.ms_service_host}&servicename=Passive Check: {metric.get('name')}"
        data = {
            "passive_checks": {"enabled": 1},
            "set_state": {"result": metric.get('status'), "output": f"{metric.get('message')} "}
        }
        if metric.get("m_name"):
            data["set_state"]["output"] += f"| {metric.get('m_name')}={metric.get('m_value')}{metric.get('m_unit')}"
        try:
            resp = requests.post(url, data=json.dumps(data), headers=headers, verify=False, timeout=self.ms_req_timeout)
        except Exception as e:
            logger.error("Not able to post metric")
            logger.exception(e)
            return False
        if resp.status_code != 200:
            logger.error(f"Not able to post metric to {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
            return False

        return True

    def retrieve_metrics(self):
        pass

    def run(self):
        """
        Run the various monitors configured. Each monitor collects a list of metrics that are then being sent to the
        monitoring server
        :return: True if successful
        """
        logger.info(f"Running {self.__class__.__name__}...")

        # Retrieve telemetries for etcd
        metrics = self.retrieve_metrics()

        # authenticate to monitoring server
        token = self.ms_authenticate()
        if token:
            # send etcd metrics
            for m in metrics:
                self.post_metric(token, m)
            logger.info(f"{self.__class__.__name__} cycle completed")
            return True
        else:
            logger.info(f"{self.__class__.__name__} cycle could not be complected, login to monitoring server not available")
            return False