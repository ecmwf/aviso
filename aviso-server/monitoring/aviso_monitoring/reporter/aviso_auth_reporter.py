# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
from enum import Enum

from .. import logger
from ..receiver import AVISO_AUTH_APP_NAME
from .opsview_reporter import OpsviewReporter


class AvisoAuthReporter(OpsviewReporter):
    def __init__(self, config, *args, **kwargs):
        aviso_auth_config = config.aviso_auth_reporter
        self.frequency = aviso_auth_config["frequency"]
        self.enabled = aviso_auth_config["enabled"]
        self.tlms = aviso_auth_config["tlms"]
        super().__init__(config, *args, **kwargs)

    def process_messages(self):
        """
        This method searches in the receiver incoming tlm lists for tlms of tlm_type it aggregates them and
        return the resulting metric.
        Returns:
            list: list of the metrics aggregated
        """
        logger.debug("Processing tlms aviso-auth...")

        # array of metrics to return
        metrics = []

        # check for each tlm
        for tlm_type in self.tlms.keys():
            # create the relative metric checker
            m_type = AvisoAuthMetricType[tlm_type.lower()]
            checker = eval(m_type.value + "(tlm_type, msg_receiver=self.msg_receiver, **self.tlms[tlm_type])")

            # retrieve metric
            metrics.append(checker.metric())

        logger.debug("Aviso Auth metrics completed")

        return metrics


class AvisoAuthMetricType(Enum):
    """
    This Enum describes the various metrics that can be used and link the name to the relative checker
    """

    auth_resp_time = "ResponseTime"
    auth_error_log = "ErrorLog"
    auth_pod_available = "PodAvailable"
    auth_users_counter = "UsersCounter"  # this is a Prometheus checker


class AvisoAuthChecker:
    """
    Base class for aviso auth checkers
    """

    def __init__(self, tlm_type, *args, **kwargs):
        self.metric_name = tlm_type
        self.msg_receiver = kwargs["msg_receiver"]

    def metric(self):
        pass


class ResponseTime(AvisoAuthChecker):
    def __init__(self, *args, **kwargs):
        self.warning_t = kwargs["warning_t"]
        self.critical_t = kwargs["critical_t"]
        self.sub_tlms = kwargs["sub_tlms"]
        super().__init__(*args, **kwargs)

    def metric(self):
        # incoming tlms
        assert self.msg_receiver, "Msg receiver is None"
        new_tlms = self.msg_receiver.extract_incoming_tlms(self.metric_name)

        if len(new_tlms):
            logger.debug(f"Processing {len(new_tlms)} tlms {self.metric_name}...")
            agg_tlms = []

            # process first the sub_tlm
            if len(self.sub_tlms):
                for sub_tlm in self.sub_tlms:
                    s_tlms = list(filter(lambda tlm: ("_" + sub_tlm in list(tlm.get("telemetry").keys())[0]), new_tlms))
                    # aggregate the telemetries
                    agg_tlms.append(OpsviewReporter.aggregate_time_tlms(s_tlms))
                    # remove these tlms from the main list
                    new_tlms = [tlm for tlm in new_tlms if tlm not in s_tlms]

            # process the main tlms
            agg_tlms.append(OpsviewReporter.aggregate_time_tlms(new_tlms))

            # clear None values from calling aggregate_tlms_stats with empty list
            agg_tlms = [x for x in agg_tlms if x is not None]

            # translate all into one metric
            metric = self.to_metric(agg_tlms)
        else:
            # create a default metric
            metric = self.to_metric()

        logger.debug(f"Processing tlms {self.metric_name} completed")

        return metric

    def to_metric(self, tlms=None):
        """
        This method transforms the response time aggregated into one metric that includes a status evaluation

        Args:
            tlms (Dict): TLMs aggregated to evaluate and report, if None or empty list it will be ignored

        Returns:
            Dict: metric
        """
        status = 0
        message = "Response time is nominal"
        if tlms:
            resp_time_max = 0
            for tlm in tlms:
                for k in list(tlm.keys()):
                    if k == self.metric_name + "_max":
                        resp_time_max = tlm.get(k)  # we evaluate with the max value of the main tlm
            if resp_time_max > self.critical_t:
                status = 2
                message = f"Response time of {resp_time_max}s > than threshold {self.critical_t}"
            elif resp_time_max > self.warning_t:
                status = 1
                message = f"Response time of {resp_time_max}s > than threshold {self.warning_t}"

            # build metric payload
            metrics = []
            for tlm in tlms:
                for k in list(tlm.keys()):
                    if "avg" in k or "max" in k:
                        metrics.append({"m_name": k, "m_value": tlm.get(k), "m_unit": "s"}),
            m_status = {"name": self.metric_name, "status": status, "message": message, "metrics": metrics}
        else:  # default metrics when no tlm have been received
            m_status = {"name": self.metric_name, "status": status, "message": ""}
        logger.debug(f"{self.metric_name} metric: {m_status}")
        return m_status


class ErrorLog(AvisoAuthChecker):
    """
    Collect the errors received
    """

    def metric(self):
        # defaults
        status = 0
        message = "No error to report"

        # fetch the error log
        assert self.msg_receiver, "Msg receiver is None"
        new_errs = self.msg_receiver.extract_incoming_errors(AVISO_AUTH_APP_NAME)

        # discard errors that are not related to the application
        new_errs = list(
            filter(lambda log: ("404 Not Found: The requested URL was not found on the server" not in log), new_errs)
        )

        if len(new_errs):
            logger.debug(f"Processing {len(new_errs)} tlms {self.metric_name}...")

            # select warnings and errors
            warns = list(filter(lambda log: ("WARNING" in log), new_errs))
            errs = list(filter(lambda log: ("ERROR" in log), new_errs))

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


class PodAvailable(AvisoAuthChecker):
    """
    Check pod availability
    """

    def __init__(self, *args, **kwargs):
        self.warning_t = kwargs["warning_t"]
        self.critical_t = kwargs["critical_t"]
        self.req_timeout = kwargs["req_timeout"]
        self.metric_server_url = kwargs["metric_server_url"]
        self.opsview_reporter = OpsviewReporter()
        super().__init__(*args, **kwargs)

    def metric(self):
        pattern = r'kube_deployment_status_replicas{namespace="aviso",deployment="aviso-auth-\w+"}'
        # defaults
        status = 0
        message = "All pods available"
        m_status = None

        # fetch the cluster metrics
        if self.metric_server_url:
            metrics = self.opsview_reporter.retrieve_metrics([self.metric_server_url], self.req_timeout)[
                self.metric_server_url
            ]
            if metrics:
                logger.debug(f"Processing tlm {self.metric_name}...")

                av_pod = self.opsview_reporter.read_from_metrics(metrics, pattern)
                if av_pod:
                    av_pod = int(av_pod)
                    if av_pod <= self.critical_t:
                        status = 2
                        message = f"Available pods: {av_pod} below critical threshold of {self.critical_t}"
                    elif av_pod <= self.warning_t:
                        status = 1
                        message = f"Available pods: {av_pod} below warning threshold of {self.warning_t}"

                    # build metric payload
                    m_status = {
                        "name": self.metric_name,
                        "status": status,
                        "message": message,
                        "metrics": [
                            {"m_name": self.metric_name, "m_value": av_pod, "m_unit": "pods"},
                        ],
                    }
                else:
                    logger.warning(f"Could not find {pattern} for {self.metric_name}")
        else:
            m_status = {"name": self.metric_name, "status": 1, "message": "Metric server not defined"}
        # check if a metric was generated
        if m_status is None:
            m_status = {"name": self.metric_name, "status": 1, "message": "Metric could not be retrieved"}
        logger.debug(f"{self.metric_name} metric: {m_status}")
        return m_status
