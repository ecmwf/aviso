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
import math
from .. import logger

class Reporter(ABC):

    def __init__(self, config, tlm_receiver):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.ms_url = config["monitor_server"]["url"]
        self.ms_service_host = config["monitor_server"]["service_host"]
        self.ms_req_timeout = config["monitor_server"]["req_timeout"]
        self.ms_username = config["monitor_server"]["username"]
        self.ms_password = config["monitor_server"]["password"]
        self.tlm_receiver = tlm_receiver

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

    def submit_metric(self, token, metric):
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
        if metric.get("metrics"):
            data["set_state"]["output"] += "| "
            for m in metric.get("metrics"):
                data["set_state"]["output"] += f"{m.get('m_name')}={m.get('m_value')}{m.get('m_unit')}; "
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

    def process_tlms(self):
        pass

    def run(self):
        """
        Run the various monitors configured. Each monitor collects a list of metrics that are then being sent to the
        monitoring server
        :return: True if successful
        """
        logger.debug(f"Running {self.__class__.__name__}...")

        # Process metrics
        metrics = self.process_tlms()

        # authenticate to monitoring server
        token = self.ms_authenticate()
        if token:
            # send etcd metrics
            for m in metrics:
                self.submit_metric(token, m)
            logger.debug(f"{self.__class__.__name__} cycle completed")
            return True
        else:
            logger.error(f"{self.__class__.__name__} cycle could not be complected, login to monitoring server not available")
            return False


    def aggregate_tlms_stats(self, tlms):
        """
        This method aggregates the telemetry passed, maintaining the same stats.

        Args:
            tlms (List): List of measurements to aggregates
        """
        # read only the telemetry field of the tlm
        r_tlms = map(lambda t: t.get("telemetry"), tlms)
        # setup the aggregated tlm to return 
        agg_tlm = {
            self.TLM_TYPE+"_counter": 0,
            self.TLM_TYPE+"_avg": 0,
            self.TLM_TYPE+"_max": -math.inf,
            self.TLM_TYPE+"_min": math.inf
            }
        sum = 0
        for tlm in r_tlms:
            agg_tlm[self.TLM_TYPE+"_counter"] += tlm[self.TLM_TYPE+"_counter"]
            agg_tlm[self.TLM_TYPE+"_max"] = tlm[self.TLM_TYPE+"_max"] if tlm[self.TLM_TYPE+"_max"] > agg_tlm[self.TLM_TYPE+"_max"] else agg_tlm[self.TLM_TYPE+"_max"]
            agg_tlm[self.TLM_TYPE+"_min"] = tlm[self.TLM_TYPE+"_min"] if tlm[self.TLM_TYPE+"_min"] < agg_tlm[self.TLM_TYPE+"_min"] else agg_tlm[self.TLM_TYPE+"_min"]
            sum = tlm[self.TLM_TYPE+"_counter"] * tlm[self.TLM_TYPE+"_avg"]
        agg_tlm[self.TLM_TYPE+"_avg"] = sum / agg_tlm[self.TLM_TYPE+"_counter"]
        
        return agg_tlm