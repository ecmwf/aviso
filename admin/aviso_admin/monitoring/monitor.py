# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import requests
import urllib3
from aviso_admin.monitoring.etcd.etcd_monitor import EtcdMonitor

from .. import logger


class Monitor:

    def __init__(self, config):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.server_url = config["server_url"]
        self.service_host = config["service_host"]
        self.frequency = config["frequency"]
        self.req_timeout = config["req_timeout"]
        self.etcd_config = config["etcd"]
        self.username = config["username"]
        self.password = config["password"]

    def authenticate(self):
        headers = {"Content-type": "application/json", "Accept": "application/json"}
        data = {"username": self.username, "password": self.password}
        try:
            resp = requests.post(self.server_url + "/login", data=json.dumps(data), headers=headers,
                                 verify=False, timeout=self.req_timeout)
        except Exception as e:
            logger.error("Not able to authenticate with monitoring server")
            logger.exception(e)
            return None
        if resp.status_code != 200:
            logger.error(f"Not able to authenticate with monitoring server for {self.username} from {self.server_url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
            return None

        return json.loads(resp.text)["token"]

    def post_metric(self, token, metric):
        headers = {"Content-type": "application/json", "X-Opsview-Username": f"{self.username}", "X-Opsview-Token": token}
        url = f"{self.server_url}/detail?hostname={self.service_host}&servicename=Passive Check: {metric.get('name')}"
        data = {
            "passive_checks": {"enabled": 1},
            "set_state": {"result": metric.get('status'), "output": f"{metric.get('message')} "}
        }
        if metric.get("m_name"):
            data["set_state"]["output"] += f"| {metric.get('m_name')}={metric.get('m_value')}{metric.get('m_unit')}"
        try:
            resp = requests.post(url, data=json.dumps(data), headers=headers, verify=False, timeout=self.req_timeout)
        except Exception as e:
            logger.error("Not able to post metric")
            logger.exception(e)
            return False
        if resp.status_code != 200:
            logger.error(f"Not able to post metric to {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
            return False

        return True

    def run(self):
        """
        :return: True if successful
        """
        logger.info("Running monitor...")

        # Retrieve telemetries for etcd
        etcd_metrics = EtcdMonitor(self.etcd_config).retrieve_metrics()

        # authenticate to monitoring server
        token = self.authenticate()
        if token:
            # send etcd metrics
            for m in etcd_metrics:
                self.post_metric(token, m)
            logger.info("Monitoring cycle completed")
        else:
            logger.info("Monitoring cycle could not be complected, login to monitoring server not available")
