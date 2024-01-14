# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum

import requests

from .. import logger
from ..receiver import ETCD_APP_NAME
from .opsview_reporter import OpsviewReporter


class EtcdReporter(OpsviewReporter):
    def __init__(self, config, *args, **kwargs):
        self.etcd_config = config.etcd_reporter
        self.frequency = self.etcd_config["frequency"]
        self.enabled = self.etcd_config["enabled"]
        self.req_timeout = self.etcd_config["req_timeout"]
        self.member_urls = self.etcd_config["member_urls"]
        self.tlms = self.etcd_config["tlms"]
        self.req_mem_count = self.etcd_config["req_mem_count"]
        super().__init__(config, *args, **kwargs)

    def process_messages(self):
        """
        This method for each metric to process instantiates the relative TLM checker and run it
        :return: the metrics collected
        """
        logger.debug("Etcd processing metrics...")

        # fetch the raw tlms provided by etcd
        raw_tlms = OpsviewReporter.retrieve_metrics(self.member_urls, self.req_timeout)  # noqa: F841

        # array of metric to return
        metrics = []

        # check for each tlm
        for tlm_type in self.tlms.keys():
            # create the relative metric checker
            m_type = EtcdMetricType[tlm_type.lower()]
            checker = eval(
                m_type.value
                + "(tlm_type, msg_receiver=self.msg_receiver, raw_tlms=raw_tlms, **self.tlms[tlm_type], \
                    **self.etcd_config)"
            )

            # retrieve metric
            metrics.append(checker.metric())

        logger.debug("Etcd metrics completed")

        return metrics


class EtcdMetricType(Enum):
    """
    This Enum describes the various etcd metrics that can be used and link the name to the relative checker
    """

    etcd_store_size = "StoreSize"
    etcd_cluster_status = "ClusterStatus"
    etcd_total_keys = "TotalKeys"
    etcd_error_log = "ErrorLog"


class EtcdChecker:
    """
    Base class for etcd checkers
    """

    def __init__(self, tlm_type, req_timeout=60, *args, **kwargs):
        self.metric_name = tlm_type
        self.req_timeout = req_timeout
        self.member_urls = kwargs["member_urls"]
        self.raw_tlms = kwargs["raw_tlms"]
        self.msg_receiver = kwargs["msg_receiver"]
        self.req_mem_count = kwargs["req_mem_count"]

    def metric(self):
        pass


class StoreSize(EtcdChecker):
    """
    This class aims at checking the size of the store.
    """

    def metric(self):
        # defaults
        status = 0
        message = "Store size is nominal"

        store_logic = self.max_store_size("etcd_mvcc_db_total_size_in_use_in_bytes")
        store_physical = self.max_store_size("etcd_mvcc_db_total_size_in_bytes")
        store_quota = self.max_store_size("etcd_server_quota_backend_bytes")

        if store_logic == -1:
            status = 2
            message = "Could not retrieve the store size"
        else:
            utilisation = store_logic * 100 / store_quota
            if utilisation > 85:
                status = 2
                message = f"Store size {store_logic} GiB exceeded 85% of the quota available: {store_quota} GiB."
            elif utilisation > 70:
                status = 1
                message = f"Store size {store_logic} GiB exceeded 85% of the quota available: {store_quota} GiB."

        # build metric payload
        m_status = {
            "name": self.metric_name,
            "status": status,
            "message": message,
            "metrics": [
                {"m_name": "store_logic", "m_value": store_logic, "m_unit": "GiB"},
                {"m_name": "store_physical", "m_value": store_physical, "m_unit": "GiB"},
                {"m_name": "store_quota", "m_value": store_quota, "m_unit": "GiB"},
            ],
        }
        logger.debug(f"{self.metric_name} metric: {m_status}")
        return m_status

    def max_store_size(self, tlm_name):
        """
        This method returns the max data size for the given tlm_name among all the members
        :param tlm_name:
        :return: data size in GiB, -1 if something went wrong
        """
        max = -1
        for u in self.member_urls:
            if self.raw_tlms[u]:
                size = OpsviewReporter.read_from_metrics(self.raw_tlms[u], tlm_name)
                if size:
                    # convert byte in GiB
                    size = round(float(size) / (1024 * 1024 * 1024), 2)
                    max = size if size > max else max
        return max


class ClusterStatus(EtcdChecker):
    """
    This class aims at assessing the status of the cluster by checking the health of each member and verifying the
    cluster size is as expected.
    """

    def metric(self):
        status = 0
        message = "Cluster status is nominal"

        # first retrieve the member size
        cluster_size = self.cluster_size(self.member_urls[0])  # any of the member should give the same info
        if cluster_size != self.req_mem_count:
            status = 2
            if cluster_size:
                message = f"Cluster size is {cluster_size}"
            else:
                message = "Not able to get cluster info"

        if status == 0:
            # now check the health of each member
            for url in self.member_urls:
                if not self.health(url):
                    status = 2
                    message = f"Cluster member {url} not healthy"
                    break

        if status == 0:
            # check if there is a leader
            if self.raw_tlms[self.member_urls[0]] is None:
                status = 1
                message = f"Could not retrieve metrics from {self.member_urls[0]}"
            else:
                leader = OpsviewReporter.read_from_metrics(self.raw_tlms[self.member_urls[0]], "etcd_server_has_leader")
                if leader != "1":
                    status = 1
                    message = "Cluster has no leader"

        # build metric payload
        m_status = {
            "name": self.metric_name,
            "status": status,
            "message": message,
        }
        logger.debug(f"{self.metric_name} metric: {m_status}")
        return m_status

    def health(self, url):
        """
        This method implements the call to a etcd member to check its health status
        :param url: member url
        :return: True if healthy
        """
        url = f"{url}/health"
        try:
            resp = requests.get(url, timeout=self.req_timeout)
        except Exception as e:
            logger.exception(f"Not able to get health on {url}, error {e}")
            return False
        if resp.status_code != 200:
            logger.error(
                f"Not able to get health on {url}, "
                f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}"
            )
        data = resp.json()
        healthy = bool(data.get("health"))

        return healthy

    def cluster_size(self, url):
        """
        This method implements the call to check the size of the cluster is as expected
        :param url: member url
        :return: cluster size
        """
        url = f"{url}/v3/cluster/member/list"
        try:
            resp = requests.post(url, timeout=self.req_timeout)
        except Exception as e:
            logger.exception(f"Not able to get cluster info on {url}, error {e}")
            return False
        if resp.status_code != 200:
            logger.error(
                f"Not able to get cluster info on {url}, "
                f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}"
            )
        data = resp.json()
        cluster_size = len(data.get("members"))

        return cluster_size


class TotalKeys(EtcdChecker):
    """
    Collect the total number of keys associated
    """

    def metric(self):
        # defaults
        status = 0
        message = "Total number of keys is nominal"
        # any member should reply the same
        t_keys = OpsviewReporter.read_from_metrics(self.raw_tlms[self.member_urls[0]], "etcd_debugging_mvcc_keys_total")
        if t_keys is None:
            status = 2
            message = "Cannot retrieve total number of keys"

        # build metric payload
        m_status = {
            "name": self.metric_name,
            "status": status,
            "message": message,
            "metrics": [{"m_name": "total_keys", "m_value": t_keys, "m_unit": ""}],
        }
        logger.debug(f"{self.metric_name} metric: {m_status}")
        return m_status


class ErrorLog(EtcdChecker):
    """
    Collect the errors received
    """

    def metric(self):
        # defaults
        status = 0
        message = "No error to report"

        # fetch the error log
        assert self.msg_receiver, "Msg receiver is None"
        new_errs = self.msg_receiver.extract_incoming_errors(ETCD_APP_NAME)

        if len(new_errs):
            logger.debug(f"Processing {len(new_errs)} tlms {self.metric_name}...")

            # select warnings and errors
            warns = list(filter(lambda log: ('level":"warn"' in log), new_errs))
            errs = list(filter(lambda log: ('level":"error"' in log), new_errs))
            fatals = list(filter(lambda log: ('level":"fatal"' in log), new_errs))
            panics = list(filter(lambda log: ('level":"panic"' in log), new_errs))

            # put together the worst errors
            errs += fatals
            errs += panics

            if len(errs):
                status = 2
                message = f"Errors received: {errs}"
            elif len(warns):
                status = 1
                message = f"Warnings received: {warns}"

        # build metric payload
        m_status = {"name": self.metric_name, "status": status, "message": message}
        logger.debug(f"{self.metric_name} metric: {m_status}")
        return m_status
