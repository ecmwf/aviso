

import requests

from aviso_admin import logger


class Collector():
    def __init__(self, type, member_urls, req_timeout=60):
        self.member_urls = member_urls
        self.metric_type = type
        self.req_timeout = req_timeout

    def metric(self):
        raise NotImplementedError()


class StoreSizeCollector(Collector):

    WARNING_T = 5  # GiB
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

        url = f"{url}/v3/maintenance/status"
        try:
            resp = requests.post(url, timeout=self.req_timeout)
        except Exception as e:
            logger.error(f"Not able to get status on {url}")
            logger.exception(e)
            return False
        if resp.status_code != 200:
            logger.error(f"Not able to get status on {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
        data = resp.json()
        size = int(data.get("dbSize"))

        # convert byte in GiB
        size = round(size / (1024 * 1024 * 1024), 2)

        return size


class ClusterStatusCollector(Collector):

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


class TotalKeysCollector(Collector):

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

        url = f"{url}/v3/kv/range"
        try:
            resp = requests.post(url, json=self.req_body, timeout=self.req_timeout)
        except Exception as e:
            logger.error(f"Not able to get total diss keys on {url}")
            logger.exception(e)
            return False
        if resp.status_code != 200:
            logger.error(f"Not able to get total diss keys on {url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
        data = resp.json()
        total_keys = int(data.get("count"))

        return total_keys


class DissKeysCollector(TotalKeysCollector):

    def __init__(self, *args):
        self.m_name = "diss_keys"
        self.key_name = "Dissemination"
        self.req_body = {"key": "L2VjL2Rpc3M=", "range_end": "L2VjL2Rpc3Mw", "count_only": True}
        super().__init__(*args)


class MarsKeysCollector(TotalKeysCollector):

    def __init__(self, *args):
        self.m_name = "mars_keys"
        self.key_name = "MARS"
        self.req_body = {"key": "L2VjL21hcnM=", "range_end": "L2VjL21hcnMw", "count_only": True}
        super().__init__(*args)