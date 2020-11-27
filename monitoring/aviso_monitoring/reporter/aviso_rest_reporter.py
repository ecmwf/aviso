# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from .reporter import Reporter
from .. import logger


class AvisoRestReporter(Reporter):


    def __init__(self, config, *args, **kwargs):
        aviso_rest_config = config.aviso_rest_reporter
        self.frequency = aviso_rest_config["frequency"]
        self.enabled = aviso_rest_config["enabled"]
        self.warning_t = aviso_rest_config["warning_t"]
        self.critical_t = aviso_rest_config["critical_t"]
        self.tlm_type = aviso_rest_config["tlm_type"]
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
        new_tlms = self.tlm_receiver.extract_incoming_tlms(self.tlm_type)
        if len(new_tlms):
            
            # aggregate the telemetries
            agg_tlm = self.aggregate_tlms_stats(new_tlms)

            # translate to metric
            metrics.append(self.to_metric(agg_tlm))
        else:
            # create a default metric
            metrics.append(self.to_metric())

        logger.debug(f"Processing tlms {self.tlm_type} completed")

        return metrics
      

    def to_metric(self, tlm=None):
        """
        This method transforms the response time aggregated into a metric that inclide a status evaluation

        Args:
            resp_time (Dict): TLM response time to evaluate and report

        Returns:
            Dict: metric
        """
        status = 0
        message = f"Response time is nominal"
        if tlm:
            resp_time_max = tlm.get(self.tlm_type+"_max") # we evaluate with the max value
            if resp_time_max > self.critical_t:
                status = 2
                message = f"Response time of {resp_time_max}s"
            elif resp_time_max > self.warning_t:
                status = 1
                message = f"Response time of {resp_time_max}s"

            # build metric payload
            m_status = {
                "name": self.tlm_type,
                "status": status,
                "message": message,
                "metrics": [
                    {
                        "m_name": self.tlm_type+"_avg",
                        "m_value": tlm.get(self.tlm_type+"_avg"),
                        "m_unit": "s"
                    },
                    {
                        "m_name": self.tlm_type+"_max",
                        "m_value": tlm.get(self.tlm_type+"_max"),
                        "m_unit": "s"
                    },
                    {
                        "m_name": self.tlm_type+"_min",
                        "m_value": tlm.get(self.tlm_type+"_min"),
                        "m_unit": "s"
                    }

                ]
            }
        else: # default metrics when no tlm have been received
            m_status = {
                "name": self.tlm_type,
                "status": status,
            }
        logger.debug(f"Response time metric: {m_status}")
        return m_status