# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import requests
from enum import Enum
import re

from .reporter import Reporter
from .. import logger


class EtcdReporter(Reporter):

    def __init__(self, config, *args, **kwargs):
        etcd_config = config.etcd_reporter
        self.frequency = etcd_config["frequency"]
        self.enabled = etcd_config["enabled"]
        self.tlm_type = etcd_config["tlm_type"]
        self.member_urls = etcd_config["member_urls"]
        self.req_timeout = etcd_config["req_timeout"]
        super().__init__(config, *args, **kwargs)

    def process_tlms(self):
        """
        This method for each metric to process instantiates the relative TLM checker and run it
        :return: the metrics collected
        """
        logger.debug("Etcd processing metrics...")

        # fetch the raw tlms provided by etcd
        raw_tlms = self.retrive_raw_tlms()

        # array of metric to return
        metrics = []
        for mn in self.tlm_type:
            # create the relative metric checker
            m_type = EtcdMetricType[mn.lower()]
            checker = eval(m_type.value + "(m_type, self.req_timeout, member_urls=self.member_urls, raw_tlms=raw_tlms)")

            # retrieve metric
            metrics.append(checker.metric())

        logger.debug("Etcd metrics completed")

        return metrics

    def retrive_raw_tlms(self):
        """
        this methods retrieves the etcd metrics provided by each member. We collect from all of them because some of
        them are not the same
        """
        raw_tlms = {}
        for u in self.member_urls:
            url = u + "/metrics"
            logger.debug(f"Retrieving TLMs from {url}...")
            try:
                resp = requests.get(url, verify=False, timeout=self.req_timeout)
            except Exception as e:
                logger.error(f"Not able to get TLMs from {url}")
                logger.exception(e)
                raw_tlms[u] = None
                continue
            if resp.status_code != 200:
                logger.error(f"Not able to get TLMs from {url}, "
                             f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
                raw_tlms[u] = None
            else:
                raw_tlms[u] = resp.text

        logger.debug("Etcd raw TLMs successfully retrieved")
        return raw_tlms


class EtcdMetricType(Enum):
    """
    This Enum describes the various etcd metrics that can be used and link the name to the relative checker
    """

    etcd_store_size = "StoreSize"
    etcd_cluster_status = "ClusterStatus"
    etcd_total_keys = "TotalKeys"


class EtcdChecker:
    """
    Base class for etcd checkers
    """

    def __init__(self, type, req_timeout=60, *args, **kwargs):
        self.metric_type = type
        self.req_timeout = req_timeout
        self.member_urls = kwargs["member_urls"]
        self.raw_tlms = kwargs["raw_tlms"]

    def metric(self):
        pass

    def read_from_raw_tlms(self, url, tlm_name):
        """
        This methods extract the value associated to tlm_name in the raw_tlms text
        :param url: member url
        :param tlm_name:
        :return: the value as string, None if nothing was found
        """
        pattern = f"{tlm_name} [0-9.e+]+"
        res = re.findall(pattern, self.raw_tlms[url])
        if len(res) == 1:
            res = res[0].split()
            if len(res) == 2:
                return res[1]
            else:
                return None
        else:
            return None


class StoreSize(EtcdChecker):
    """
    This class aims at checking the size of the store.
    """

    def metric(self):

        # defaults
        status = 0
        message = f"Store size is nominal"

        store_logic = self.max_store_size("etcd_mvcc_db_total_size_in_use_in_bytes")
        store_physical = self.max_store_size("etcd_mvcc_db_total_size_in_bytes")
        store_quota = self.max_store_size("etcd_server_quota_backend_bytes")

        if store_logic == -1:
            status = 2
            message = f"Could not retrieve the store size"
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
            "name": self.metric_type.name,
            "status": status,
            "message": message,
            "metrics": [
                {
                    "m_name": "store_logic",
                    "m_value": store_logic,
                    "m_unit": "GiB"
                },
                {
                    "m_name": "store_physical",
                    "m_value": store_physical,
                    "m_unit": "GiB"
                },
                {
                    "m_name": "store_quota",
                    "m_value": store_quota,
                    "m_unit": "GiB"
                }
            ]
        }
        logger.debug(f"Store size metric: {m_status}")
        return m_status

    def max_store_size(self, tlm_name):
        """
        This method returns the max data size for the given tlm_name among all the members
        :param tlm_name:
        :return: data size in GiB, -1 if something went wrong
        """
        max = -1
        for u in self.member_urls:
            size = self.read_from_raw_tlms(u, tlm_name)
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
        message = f"Cluster status is nominal"

        # first retrieve the member size
        cluster_size = self.cluster_size(self.member_urls[0])  # any of the member should give the same info
        if cluster_size != len(self.member_urls):
            status = 2
            message = f"Cluster size is {cluster_size}"

        # now check the health of each member
        for url in self.member_urls:
            if not self.health(url):
                status = 2
                message = f"Cluster member {url} not healthy"

        # check if there is a leader
        leader = self.read_from_raw_tlms(self.member_urls[0], "etcd_server_has_leader")
        if leader != "1":
            status = 1
            message = f"Cluster has no leader"

        # retrieve total failed hearthbeat
        tot_failed_heartbeat = 0
        for url in self.member_urls:
            failed_heartbeat = self.read_from_raw_tlms(url, "etcd_server_heartbeat_send_failures_total")
            if failed_heartbeat:
                tot_failed_heartbeat += int(failed_heartbeat)

        # build metric payload
        m_status = {
            "name": self.metric_type.name,
            "status": status,
            "message": message,
            "metrics": [
                {
                    "m_name": "failed_heartbeat",
                    "m_value": tot_failed_heartbeat,
                    "m_unit": ""
                }
            ]
        }
        logger.debug(f"Cluster status metric: {m_status}")
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
            logger.error(f"Not able to get health on {url}")
            logger.exception(e)
            return False
        if resp.status_code != 200:
            logger.error(f"Not able to get health on {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
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
            logger.error(f"Not able to get cluster info on {url}")
            logger.exception(e)
            return False
        if resp.status_code != 200:
            logger.error(f"Not able to get cluster info on {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
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
        message = f"Total number of keys is nominal"
        # any member should reply the same
        t_keys = self.read_from_raw_tlms(self.member_urls[0], "etcd_debugging_mvcc_keys_total")
        if t_keys is None:
            status = 2
            message = f"Cannot retrieve total number of keys"

        # build metric payload
        m_status = {
            "name": self.metric_type.name,
            "status": status,
            "message": message,
            "metrics": [
                {
                    "m_name": "total_keys",
                    "m_value": t_keys,
                    "m_unit": ""
                }
            ]
        }
        logger.debug(f"Total keys metric: {m_status}")
        return m_status
