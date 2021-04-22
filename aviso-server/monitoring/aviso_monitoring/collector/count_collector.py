# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from .. import logger
from .collector import Collector


class UniqueCountCollector(Collector):
    """
    This specialised collector is used to collect unique results of the function passed in order to count them.
    It is implemented as a decorator.
    """

    def __call__(self, f, args=(), kwargs=None):
        """
        This method collects the result of the function together with a timestamp. It is called in a decorator fashion.

        Args:
            f (Callable): Function to take the time of
            args (tuple, or list): Function arguments
            kwargs(dict): Function arguments
        """
        if type(args) is not tuple and type(args) is not list:
            args = [args] 
        if not kwargs:
            kwargs = {}
        res = f(*args, **kwargs)

        # Collect and update the timestamp if already present
        if self.enabled:
            if not res in self.tlm_buffer:
                self.tlm_buffer.append(res)
            logger.debug("Result collected")
        return res

    def aggregate_tlms(self, tlms):
        """
        This method aggregates the measurements collected in the buffer and create a tlm out of them.
        In this case it select the values and count them

        Args:
            tlms (List): List of measurements to aggregates
        """
        if len(tlms):
            agg_tlm = {
                self.telemetry_name+"_counter": len(tlms),
                self.telemetry_name+"_values": tlms,
            }
            return agg_tlm
        else: 
            return {}
