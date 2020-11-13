# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import requests

from ... import logger
from .collector import Collector
from ...utils import encode_to_str_base64, incr_last_byte


class EtcdCollector(Collector):
    '''
    Base class for etcd collectors
    '''
    def __init__(self, *args, **kwargs):
        self.member_urls = kwargs["member_urls"]
        super().__init__(*args, **kwargs)


class StoreSizeCollector(EtcdCollector):
    '''
    This class aims at collecting the size of the store. For consistency checks all the members and return the highest
    '''

    WARNING_T = 6  # GiB
    CRITICAL_T = 7  # GiB

    def metric(self):
        status = 0
        max_size = 0
        message = f"Store size is nominal"
        for url in self.member_urls:
            size = self.store_size(url)
            if size > self.CRITICAL_T:
                status = 2
                message = f"Store size of {size}GiB on {url}"
            elif size > self.WARNING_T:
                status = 1
                message = f"Store size of {size}GiB on {url}"
            elif size == -1:
                status = 1
                message = f"Could not retrieve the store size on {url}"
            max_size = size if size > max_size else max_size

        # build metric payload
        metric = {
            "name": self.metric_type.name,
            "status": status,
            "message": message,
            "m_name": "store_size",
            "m_value": max_size,
            "m_unit": "GiB"
        }
        logger.debug(f"Store size metric: {metric}")
        return metric

    def store_size(self, url):
        '''
        This method implements the call to a etcd member to retrieve the store size
        :param url: member url
        :return: store size in GiB, -1 if something went wrong
        '''

        url = f"{url}/v3/maintenance/status"
        try:
            resp = requests.post(url, timeout=self.req_timeout)
        except Exception as e:
            logger.error(f"Not able to get status on {url}")
            logger.exception(e)
            return -1
        if resp.status_code != 200:
            logger.error(f"Not able to get status on {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
        data = resp.json()
        size = int(data.get("dbSize"))

        # convert byte in GiB
        size: float = round(size / (1024 * 1024 * 1024), 2)

        return size


class ClusterStatusCollector(EtcdCollector):
    '''
    This class aims at assessing the status of the cluster by checking the health of each member and verifying the
    cluster size is as expected.
    '''

    def metric(self):
        status = 0
        message = f"Cluster status is nominal"

        # first retrieve the member size
        cluster_size = self.cluster_size(self.member_urls[0])  # any of the memeber should give the same info
        if cluster_size != len(self.member_urls):
            status = 2
            message = f"Cluster size is {cluster_size}"

        # now check the health of each member
        for url in self.member_urls:
            if not self.health(url):
                status = 2
                message = f"Cluster member {url} not healthy"

        # build metric payload
        metric = {
            "name": self.metric_type.name,
            "status": status,
            "message": message,
        }
        logger.debug(f"Cluster status metric: {metric}")
        return metric

    def health(self, url):
        '''
        This method implements the call to a etcd member to check its health status
        :param url: member url
        :return: True if healthy
        '''
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
        '''
        This method implements the call to check the size of the cluster is as expected
        :param url: member url
        :return: cluster size
        '''
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


class TotalKeysCollector(EtcdCollector):
    '''
    Abstract class to collect the number of keys associated to a key prefix
    '''

    def metric(self):
        status = 0
        message = f"{self.key_name} keys are nominal"
        t_keys = self.total_keys(self.member_urls[0])  # any member should reply the same

        # build metric payload
        metric = {
            "name": self.metric_type.name,
            "status": status,
            "message": message,
            "m_name": self.m_name,
            "m_value": t_keys,
            "m_unit": ""
        }
        logger.debug(f"{self.key_name} keys metric: {metric}")
        return metric

    def total_keys(self, url):
        '''
        This method implements the call to retrieve the number of keys under a specific key prefix
        :param url: member url
        :return: number of keys
        '''

        url = f"{url}/v3/kv/range"
        range_start = encode_to_str_base64(self.BASE_KEY)
        range_end = encode_to_str_base64(str(incr_last_byte(self.BASE_KEY), "utf-8"))
        self.req_body = {"key": range_start, "range_end": range_end, "count_only": True}
        try:
            resp = requests.post(url, json=self.req_body, timeout=self.req_timeout)
        except Exception as e:
            logger.error(f"Not able to get total keys on {url}")
            logger.exception(e)
            return False
        if resp.status_code != 200:
            logger.error(f"Not able to get total keys on {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
            return False
        data = resp.json()
        assert "count" in data
        total_keys = int(data.get("count"))

        return total_keys


class DissKeysCollector(TotalKeysCollector):
    '''
    This class collects the total number of keys under the dissemination prefix
    '''
    BASE_KEY = "/ec/diss/"

    def __init__(self, *args, **kwargs):
        self.m_name = "diss_keys"
        self.key_name = "Dissemination"
        super().__init__(*args, **kwargs)


class MarsKeysCollector(TotalKeysCollector):
    '''
    This class collects the total number of keys under the mars prefix
    '''
    BASE_KEY = "/ec/mars/"

    def __init__(self, *args, **kwargs):
        self.m_name = "mars_keys"
        self.key_name = "MARS"
        super().__init__(*args, **kwargs)