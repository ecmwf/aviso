# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import collections.abc
import sys
from typing import Dict

from . import logger


class Config:
    """
    This class is in charge of holding the configuration for the monitoring system, including UDP server and reporters,
    which can be defined by arguments, environment variables or defaults.
    """

    def __init__(
        self,
        udp_server=None,
        monitor_servers=None,
        aviso_rest_reporter=None,
        aviso_auth_reporter=None,
        etcd_reporter=None,
        prometheus_reporter=None,
    ):

        try:
            # we build the configuration in priority order from the lower to the higher
            # start from the defaults
            self._config = self._create_default_config()
            # add environment variables
            Config.deep_update(self._config, self._read_env_variables())
            # add constructor parameters
            self.udp_server = udp_server
            self.monitor_servers = monitor_servers
            self.aviso_rest_reporter = aviso_rest_reporter
            self.aviso_auth_reporter = aviso_auth_reporter
            self.etcd_reporter = etcd_reporter
            self.prometheus_reporter = prometheus_reporter

            logger.debug(f"Loading configuration completed")

        except Exception as e:
            logger.error(f"Error occurred while setting the configuration, exception: {type(e)} {e}")
            logger.debug("", exc_info=True)
            sys.exit(-1)

    @staticmethod
    def _create_default_config() -> Dict:

        udp_server = {"host": "127.0.0.1", "port": 1111, "buffer_size": 64 * 1024}

        # this are the setting for sending the telemetry to a monitoring server like Opsview
        monitor_servers = [
            {
                "url": "https://localhost",
                "username": "TBD",
                "password": "TBD",
                "service_host": "aviso",
            }
        ]

        aviso_rest_reporter = {
            "enabled": False,
            "frequency": 1,  # min
            "tlms": {
                "rest_resp_time": {
                    "warning_t": 10,  # s
                    "critical_t": 20,  # s
                },
                "rest_pod_available": {
                    "warning_t": 2,  # pods
                    "critical_t": 1,  # pods
                    "req_timeout": 60,
                    "metric_server_url": None,
                },
                "rest_error_log": {},
            },
        }

        aviso_auth_reporter = {
            "enabled": False,
            "frequency": 1,  # in minutes
            "tlms": {
                "auth_resp_time": {"warning_t": 10, "critical_t": 20, "sub_tlms": []},  # s  # s
                "auth_pod_available": {
                    "warning_t": 2,  # pods
                    "critical_t": 1,  # pods
                    "req_timeout": 60,
                    "metric_server_url": None,
                },
                "auth_error_log": {},
            },
        }

        etcd_reporter = {
            "enabled": False,
            "frequency": 5,  # min
            "member_urls": ["http://localhost:2379"],
            "req_timeout": 60,  # s
            "tlms": {"etcd_store_size": {}, "etcd_cluster_status": {}, "etcd_error_log": {}},
        }

        prometheus_reporter = {
            "enabled": False,
            "host": "127.0.0.1",
            "port": 8080,
            "tlms": {
                "auth_users_counter": {"retention_window": 24},  # h
            },
        }

        # main config
        config = {}
        config["udp_server"] = udp_server
        config["monitor_servers"] = monitor_servers
        config["aviso_rest_reporter"] = aviso_rest_reporter
        config["aviso_auth_reporter"] = aviso_auth_reporter
        config["etcd_reporter"] = etcd_reporter
        config["prometheus_reporter"] = prometheus_reporter
        return config

    def _read_env_variables(self) -> Dict:
        config = {}
        # TBD
        return config

    @property
    def udp_server(self):
        return self._udp_server

    @udp_server.setter
    def udp_server(self, udp_server):
        u = self._config.get("udp_server")
        if udp_server is not None and u is not None:
            Config.deep_update(u, udp_server)
        elif udp_server is not None:
            u = udp_server
        # verify is valid
        assert u is not None, "udp_server has not been configured"
        assert u.get("host") is not None, "udp_server host has not been configured"
        assert u.get("port") is not None, "udp_server port has not been configured"
        assert u.get("buffer_size") is not None, "udp_server buffer_size has not been configured"
        self._udp_server = u

    @property
    def monitor_servers(self):
        return self._monitor_servers

    @monitor_servers.setter
    def monitor_servers(self, monitor_servers):
        m = self._config.get("monitor_servers")
        if monitor_servers is not None:
            m = monitor_servers
        # verify is valid
        assert m is not None, "monitor_servers has not been configured"
        for server in m:
            assert server.get("url") is not None, "monitor_server url has not been configured"
            assert server.get("username") is not None, "monitor_server username has not been configured"
            assert server.get("password") is not None, "monitor_server password has not been configured"
            assert server.get("service_host") is not None, "monitor_server service_host has not been configured"
        self._monitor_servers = m

    @property
    def aviso_rest_reporter(self):
        return self._aviso_rest_reporter

    @aviso_rest_reporter.setter
    def aviso_rest_reporter(self, aviso_rest_reporter):
        ar = self._config.get("aviso_rest_reporter")
        if aviso_rest_reporter is not None and ar is not None:
            Config.deep_update(ar, aviso_rest_reporter)
        elif aviso_rest_reporter is not None:
            ar = aviso_rest_reporter
        # verify is valid
        assert ar is not None, "aviso_rest_reporter has not been configured"
        assert ar.get("tlms") is not None, "aviso_rest_reporter tlms has not been configured"
        assert ar.get("enabled") is not None, "aviso_rest_reporter enabled has not been configured"
        if type(ar["enabled"]) is str:
            ar["enabled"] = ar["enabled"].casefold() == "true".casefold()
        assert ar.get("frequency") is not None, "aviso_rest_reporter frequency has not been configured"
        self._aviso_rest_reporter = ar

    @property
    def aviso_auth_reporter(self):
        return self._aviso_auth_reporter

    @aviso_auth_reporter.setter
    def aviso_auth_reporter(self, aviso_auth_reporter):
        aa = self._config.get("aviso_auth_reporter")
        if aviso_auth_reporter is not None and aa is not None:
            Config.deep_update(aa, aviso_auth_reporter)
        elif aviso_auth_reporter is not None:
            aa = aviso_auth_reporter
        # verify is valid
        assert aa is not None, "aviso_auth_reporter has not been configured"
        assert aa.get("tlms") is not None, "aviso_auth_reporter tlms has not been configured"
        assert aa.get("enabled") is not None, "aviso_auth_reporter enabled has not been configured"
        if type(aa["enabled"]) is str:
            aa["enabled"] = aa["enabled"].casefold() == "true".casefold()
        assert aa.get("frequency") is not None, "aviso_auth_reporter frequency has not been configured"
        self._aviso_auth_reporter = aa

    @property
    def etcd_reporter(self):
        return self._etcd_reporter

    @etcd_reporter.setter
    def etcd_reporter(self, etcd_reporter):
        e = self._config.get("etcd_reporter")
        if etcd_reporter is not None and e is not None:
            Config.deep_update(e, etcd_reporter)
        elif etcd_reporter is not None:
            e = etcd_reporter
        # verify is valid
        assert e is not None, "etcd_reporter has not been configured"
        assert e.get("tlms") is not None, "etcd_reporter tlms has not been configured"
        assert e.get("enabled") is not None, "etcd_reporter enabled has not been configured"
        if type(e["enabled"]) is str:
            e["enabled"] = e["enabled"].casefold() == "true".casefold()
        assert e.get("frequency") is not None, "etcd_reporter frequency has not been configured"
        assert e.get("member_urls") is not None, "etcd_reporter member_urls has not been configured"
        assert e.get("req_timeout") is not None, "etcd_reporter req_timeout has not been configured"
        self._etcd_reporter = e

    @property
    def prometheus_reporter(self):
        return self._prometheus_reporter

    @prometheus_reporter.setter
    def prometheus_reporter(self, prometheus_reporter):
        pr = self._config.get("prometheus_reporter")
        if prometheus_reporter is not None and pr is not None:
            Config.deep_update(pr, prometheus_reporter)
        elif prometheus_reporter is not None:
            pr = prometheus_reporter
        # verify is valid
        assert pr is not None, "prometheus_reporter has not been configured"
        assert pr.get("host") is not None, "prometheus_reporter host has not been configured"
        assert pr.get("enabled") is not None, "prometheus_reporter enabled has not been configured"
        if type(pr["enabled"]) is str:
            pr["enabled"] = pr["enabled"].casefold() == "true".casefold()
        assert pr.get("port") is not None, "prometheus_reporter port has not been configured"
        self._prometheus_reporter = pr

    def __str__(self):
        config_string = (
            f"udp_server: {self.udp_server}"
            + f", monitor_servers: {self.monitor_servers}"
            + f", aviso_rest_reporter: {self.aviso_rest_reporter}"
            + f", aviso_auth_reporter: {self.aviso_auth_reporter}"
            + f", etcd_reporter: {self.etcd_reporter}"
            + f", prometheus_reporter: {self.prometheus_reporter}"
        )
        return config_string

    def _configure_property(self, param, name):
        value = None
        if param is not None:
            value = param
        elif self._config.get(name) is not None:
            # Setting var from user configuration file
            value = self._config.get(name)
        else:
            logger.error(f"{name} has not been configured")
            sys.exit(-1)
        return value

    @staticmethod
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, collections.abc.Mapping):
                d[k] = Config.deep_update(d.get(k, type(v)()), v)
            else:
                d[k] = v
        return d
