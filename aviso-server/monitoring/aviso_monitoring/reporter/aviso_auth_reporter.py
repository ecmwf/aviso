# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from .reporter import Reporter
from .. import logger


class AvisoAuthReporter(Reporter):


    def __init__(self, config, *args, **kwargs):
        aviso_auth_config = config.aviso_auth_reporter
        self.frequency = aviso_auth_config["frequency"]
        self.enabled = aviso_auth_config["enabled"]
        self.warning_t = aviso_auth_config["warning_t"]
        self.critical_t = aviso_auth_config["critical_t"]
        self.tlm_type = aviso_auth_config["tlm_type"]
        self.sub_tlms = aviso_auth_config["sub_tlms"]
        super().__init__(config, *args, **kwargs)

    def process_tlms(self):
        """
        This method searches in the receiver incoming tlm lists for tlms of tlm_type it aggregates them and 
        return the resulting metric.
        Returns:
            list: list of the metrics aggregated
        """
        logger.debug(f"Processing tlms {self.tlm_type}...")

        # array of metrics to return
        metrics = []

        # incoming tlms
        new_tlms = self.tlm_receiver.extract_incoming_tlms(self.tlm_type)
        if len(new_tlms):
            agg_tlms = []

            # process first the sub_tlm
            if len(self.sub_tlms) > 0:
                for sub_tlm in self.sub_tlms:  
                    s_tlms = list(filter(lambda tlm: ("_"+sub_tlm in list(tlm.get("telemetry").keys())[0]), new_tlms))  
                    # aggregate the telemetries
                    agg_tlms.append(self.aggregate_tlms_stats(s_tlms))
                    # remove these tlms from the main list
                    new_tlms = [tlm for tlm in new_tlms if tlm not in s_tlms]
            
            # process the main tlms
            agg_tlms.append(self.aggregate_tlms_stats(new_tlms))

            # translate all into one metric
            metrics.append(self.to_metric(agg_tlms))
        else:
            # create a default metric
            metrics.append(self.to_metric())

        logger.debug(f"Processing tlms {self.tlm_type} completed")

        return metrics


    def to_metric(self, tlms=None):
        """
        This method transforms the response time aggregated into one metric that inclides a status evaluation

        Args:
            tlms (Dict): TLMs aggregated to evaluate and report

        Returns:
            Dict: metric
        """
        status = 0
        message = f"Response time is nominal"
        if tlms:
            resp_time_max = 0
            for tlm in tlms:
                for k in list(tlm.keys()):
                    if k == self.tlm_type+"_max":
                        resp_time_max = tlm.get(k) # we evaluate with the max value of the main tlm
            if resp_time_max > self.critical_t:
                status = 2
                message = f"Response time of {resp_time_max}s"
            elif resp_time_max > self.warning_t:
                status = 1
                message = f"Response time of {resp_time_max}s"

            # build metric payload
            metrics = []
            for tlm in tlms:
                for k in list(tlm.keys()):
                    if "avg" in k or "max" in k:
                        metrics.append({
                            "m_name": k,
                            "m_value": tlm.get(k),
                            "m_unit": "s"
                        }),
            m_status = {
                "name": self.tlm_type,
                "status": status,
                "message": message,
                "metrics": metrics
            }
        else: # default metrics when no tlm have been received
            m_status = {
                "name": self.tlm_type,
                "status": status,
                "message": message
            }
        logger.debug(f"Response time metric: {m_status}")
        return m_status