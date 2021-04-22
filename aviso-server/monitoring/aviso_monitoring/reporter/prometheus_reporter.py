# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from threading import Thread

import urllib3
from flask import Flask, Response

from .. import logger
from ..config import Config
from .aviso_auth_reporter import AvisoAuthMetricType


class PrometheusReporter(Thread):
    """
    This class provides an endpoint for the Prometheus scraper. It is meant to provide to Prometheus the metrics not required by Opsview but still useful for 
    investigation
    """

    def __init__(self, config: Config, msg_receiver):
        super(PrometheusReporter, self).__init__()
        prometheus_config = config.prometheus_reporter
        self.host = prometheus_config["host"]
        self.port = prometheus_config["port"]
        self.enabled = prometheus_config["enabled"]
        self.tlms = prometheus_config["tlms"]
        self.msg_receiver = msg_receiver
        # run in the background
        self.setDaemon(True)
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self.handler = self.create_handler()
        

    def create_handler(self) -> Flask:
        handler = Flask(__name__)
        handler.title = "aviso-auth"
        logger.handlers = handler.logger.handlers

        def json_response(m, code, header=None):
            h = {'Content-Type': 'application/json'}
            if header:
                h.update(header)
            return json.dumps({"message": str(m)}), code, h

        @handler.errorhandler(Exception)
        def default_error_handler(e):
            logging.exception(str(e))
            return json_response(e, 500)

        @handler.route("/metrics", methods=["GET"])
        def metrics():
            logger.debug(f"Requesting metrics...")

            resp_content = ""
            # check for each tlm
            for tlm_type in self.tlms.keys():
                # create the relative metric checker
                m_type = AvisoAuthMetricType[tlm_type.lower()]
                checker = eval(m_type.value + "(tlm_type, msg_receiver=self.msg_receiver, **self.tlms[tlm_type])")

                # retrieve metric
                resp_content += checker.metric()

            return Response(resp_content)

        return handler


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
        
        # read only the telemetry field of the tlm
        r_tlms = list(map(lambda t: t.get("telemetry"), tlms))

        # determine tlm_type
        first_key = list(r_tlms[0].keys())[0]
        tlm_type = first_key[:first_key.rfind("_")]

        # create a unique list of values
        aggr_values= []
        for tlm in r_tlms:
            for v in tlm[tlm_type + "_values"]:
                if not v in aggr_values:
                    aggr_values.append(v)

        agg_tlm = {
            tlm_type + "_counter": len(aggr_values),
            tlm_type + "_values": aggr_values,
        }
        return agg_tlm

    def run(self):
        logger.info(f"Running prometheus reporter on server flask")
        
        # flask internal server for non-production environments but it's fine for this usecase
        # Gunicorn does not work because spread the request over independent processes and therefore the Receiver object cannot be shared in this way
        self.handler.run( 
            host=self.host,
            port=self.port, 
            use_reloader=False)
    

class UsersCounter():

    def __init__(self, tlm_type, *args, **kwargs):
        self.metric_name = tlm_type
        self.retention_window = kwargs["retention_window"]
        self.msg_receiver = kwargs["msg_receiver"]

    def metric(self):

        logger.debug(f"Processing tlms {self.metric_name}...")

        assert self.msg_receiver, "Msg receiver is None"
        # get the tlms but not clear the buffer, we need it for the retention window
        buffer = self.msg_receiver.extract_incoming_tlms(self.metric_name, clear=False)

        if len(buffer):
            logger.debug(f"Processing {len(buffer)} tlms {self.metric_name}...")

            # consider only the ones in the retention window and reset the buffer
            start = datetime.utcnow() - timedelta(hours=self.retention_window)
            new_tlms = list(filter(lambda tlm: datetime.fromtimestamp(tlm["time"]) > start, buffer))
            self.msg_receiver.set_incoming_tlms(self.metric_name, new_tlms)

            # aggregate the telemetries
            agg_tlm = PrometheusReporter.aggregate_unique_counter_tlms(new_tlms)

            # translate to metric
            metric = self.to_metric(agg_tlm)
        else:
            # create a default metric
            metric = self.to_metric()

        logger.debug(f"Processing tlms {self.metric_name} completed")

        return metric

    def to_metric(self, tlm=None):
        """
        This method transforms the aggregated counter into a metric

        Args:
            tlm (Dict): TLM aggregated to evaluate and report

        Returns:
            str: metric
        """
        metric = "# HELP aviso_auth_users Number of users in the last 24 hours\n# TYPE aviso_auth_users gauge\naviso_auth_users "
        if tlm:
            users_count = tlm.get(self.metric_name + "_counter")
            metric+=f"{users_count}\n"
            users = tlm.get(self.metric_name + "_values")
            metric+=f'# Users: {users}\n'

        else:  # default metrics when no tlm have been received
            metric+="0\n"
            users = ""
        logger.debug(f"{self.metric_name} metric: {metric} for users: {users}")
        return metric
