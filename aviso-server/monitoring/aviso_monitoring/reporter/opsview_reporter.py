# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import math
import re
from abc import ABC

import requests
import urllib3

from .. import logger
from ..config import Config


class OpsviewReporter(ABC):
    metric_token_enabled = False
    metric_token = ""

    def __init__(self, config: Config, msg_receiver=None):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.monitor_servers = config.monitor_servers
        self.msg_receiver = msg_receiver
        self.token = {}

    @classmethod
    def configure_metric_vars(cls, config):
        """
        Configures the class attributes based on the provided config.
        """
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        if config.kube_state_metrics["token_enabled"]:
            cls.metric_token_enabled = True
            cls.metric_token = config.kube_state_metrics["token"]

    def ms_authenticate(self, m_server):
        """
        This method authenticate to the monitoring server
        :return: token if successfully authenticated, None otherwise
        """
        headers = {"Content-type": "application/json", "Accept": "application/json"}
        data = {"username": m_server["username"], "password": m_server["password"]}
        try:
            resp = requests.post(
                m_server["url"] + "/login", data=json.dumps(data), headers=headers, verify=False, timeout=60
            )
        except Exception as e:
            logger.exception(f"Not able to authenticate with monitoring server, error {e}")
            return None
        if resp.status_code != 200:
            logger.error(
                f"Not able to authenticate with monitoring server for {m_server['username']} from {m_server['url']}, "
                f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}"
            )
            return None

        return json.loads(resp.text)["token"]

    def submit_metric(self, m_server, token, metric):
        """
        This method send the metric passed to the monitoring server
        :param token: authentication token
        :param metric:
        :return: True if successful, False otherwise
        """
        headers = {
            "Content-type": "application/json",
            "X-Opsview-Username": f"{m_server['username']}",
            "X-Opsview-Token": token,
        }
        url = f"{m_server['url']}/detail?hostname={m_server['service_host']}&servicename=Passive Check: {metric.get('name')}"  # noqa: E501
        data = {
            "set_state": {"result": metric.get("status"), "output": f"{metric.get('message')} "},
        }
        if metric.get("metrics"):
            data["set_state"]["output"] += "| "
            for m in metric.get("metrics"):
                data["set_state"]["output"] += f"{m.get('m_name')}={m.get('m_value')}{m.get('m_unit')}; "
        try:
            resp = requests.post(url, data=json.dumps(data), headers=headers, verify=False, timeout=60)
        except Exception as e:
            logger.exception(f"Not able to post metric, error {e}")
            return False
        if resp.status_code == 401:
            # we need to repeat the login
            token = self.ms_authenticate(m_server)
            if token:
                self.token[m_server["url"]] = token
                if self.submit_metric(m_server, token, metric):
                    return True
        if resp.status_code != 200:
            logger.error(
                f"Not able to post metric to {url}, "
                f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}"
            )
            return False

        return True

    def process_messages(self):
        pass

    def run(self):
        """
        Run the reporter configured. It collects and aggregates a list of TLMs and errors that are then sent to the
        monitoring server as metrics
        :return: True if successful
        """
        logger.debug(f"Running {self.__class__.__name__}...")

        # Process messages
        metrics = self.process_messages()

        # authenticate to monitoring server
        for m_server in self.monitor_servers:
            if m_server["url"] not in self.token:
                token = self.ms_authenticate(m_server)
                if token:
                    self.token[m_server["url"]] = token
            else:
                token = self.token[m_server["url"]]
            if token:
                # send metrics
                for m in metrics:
                    self.submit_metric(m_server, token, m)
            else:
                logger.error(f"{self.__class__.__name__} login to monitoring server not available")

        logger.debug(f"{self.__class__.__name__} cycle completed")
        return True

    def aggregate_time_tlms(tlms):
        """
        This method aggregates the TLMs passed, maintaining the same stats.

        Args:
            tlms (List): List of measurements to aggregates

        Returns:
            Dict: aggregated metric or None if tlms is empty
        """
        if len(tlms) == 0:
            return None

        logger.debug(f"tlms: {tlms}")

        # Initialize the aggregated telemetry
        agg_tlm = {}
        summation = {}

        for tlm in tlms:
            r_tlm = tlm.get("telemetry")
            for key in r_tlm.keys():
                tlm_type = key[: key.rfind("_")]

                # Initialize if tlm_type is new
                if tlm_type not in agg_tlm:
                    agg_tlm[tlm_type + "_counter"] = 0
                    agg_tlm[tlm_type + "_avg"] = 0
                    agg_tlm[tlm_type + "_max"] = -math.inf
                    agg_tlm[tlm_type + "_min"] = math.inf
                    summation[tlm_type] = 0

                agg_tlm[tlm_type + "_counter"] += r_tlm[tlm_type + "_counter"]
                agg_tlm[tlm_type + "_max"] = max(agg_tlm[tlm_type + "_max"], r_tlm[tlm_type + "_max"])
                agg_tlm[tlm_type + "_min"] = min(agg_tlm[tlm_type + "_min"], r_tlm[tlm_type + "_min"])
                summation[tlm_type] += r_tlm[tlm_type + "_counter"] * r_tlm[tlm_type + "_avg"]

        for tlm_type in summation:
            if agg_tlm[tlm_type + "_counter"] > 0:
                agg_tlm[tlm_type + "_avg"] = summation[tlm_type] / agg_tlm[tlm_type + "_counter"]
            else:
                agg_tlm[tlm_type + "_avg"] = 0

        logger.debug(f"agg_tlm: {agg_tlm}")
        return agg_tlm

    def aggregate_unique_counter_tlms(tlms):
        """
        This method aggregates the counter TLMs passed for unique values

        Args:
            tlms (List): List of measurements to aggregates

        Returns:
            Dict: aggregated metric or None if tlms is empty
        """
        if len(tlms) == 0:
            return None

        agg_tlms = {}

        for tlm in tlms:
            telemetry_data = tlm.get("telemetry", {})
            for key, values in telemetry_data.items():
                if key.endswith("_values"):
                    tlm_type = key[: key.rfind("_")]

                    if tlm_type not in agg_tlms:
                        agg_tlms[tlm_type] = {
                            tlm_type + "_counter": 0,
                            tlm_type + "_values": set(),
                        }

                    agg_tlms[tlm_type][tlm_type + "_values"].update(values)

        # Convert sets to lists and update counters
        for tlm_type, data in agg_tlms.items():
            data[tlm_type + "_values"] = list(data[tlm_type + "_values"])
            data[tlm_type + "_counter"] = len(data[tlm_type + "_values"])

        return agg_tlms

    @classmethod
    def retrieve_metrics(cls, metric_servers, req_timeout):
        """
        This methods retrieves the metrics provided by specific metric servers using a Prometheus interface.
        """
        raw_tlms = {}
        for u in metric_servers:
            url = u + "/metrics"
            logger.debug(f"Retrieving metrics from {url}...")
            headers = {}
            try:
                if cls.metric_token_enabled:
                    headers["Authorization"] = f"Bearer {cls.metric_token}"
                resp = requests.get(url, verify=False, timeout=req_timeout, headers=headers)
            except Exception as e:
                logger.exception(f"Not able to get metrics from {url}, error {e}")
                raw_tlms[u] = None
                continue
            if resp.status_code != 200:
                logger.error(
                    f"Not able to get metrics from {url}, "
                    f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}"
                )
                raw_tlms[u] = None
            else:
                raw_tlms[u] = resp.text

        logger.debug("Metrics successfully retrieved")
        return raw_tlms

    def read_from_metrics(metrics, name):
        """
        This methods extract the value associated to name in the metrics text
        :param metrics: Prometheus metrics
        :param name:
        :return: the value as string, None if nothing was found
        """
        pattern = f"{name} [0-9.e+]+"
        res = re.findall(pattern, metrics)
        if len(res) == 1:
            res = res[0].split()
            if len(res) == 2:
                return res[1]
            else:
                return None
        else:
            return None
