# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Iterable
from .collector import Collector
import time
from timeit import default_timer as timer
from queue import Queue
from .. import logger

class TimeCollector(Collector):
    """
    This specialised collector is used to collect the time taken to complete a function. It is implemented as a decorator.
    """

    def __call__(self, f, args=(), kwargs={}):
        """
        This method collects the time taken to execute the function. It is called in a decorator fashion.

        Args:
            f (Callable): Function to take the time of
            args (tuple, or list): Function arguments
            kwargs(dict): Function arguments
        """
        if type(args) is not tuple and type(args) is not list:
            args = [args] 
        start = timer()
        res = f(*args, **kwargs)
        self.tlm_buffer.append(timer()-start)
        logger.debug("Time collected")
        return res

    def aggregate_tlms(self, tlms):
        """
        This method aggregates the measurements collected in the buffer and create a tlm out of them.
        In this case it create a few stats of the times taken.

        Args:
            tlms (List): List of measurements to aggregates
        """
        if len(tlms):
            agg_tlm = {
                self.telemetry_type+"_counter": len(tlms),
                self.telemetry_type+"_avg": sum(tlms) / len(tlms),
                self.telemetry_type+"_max": max(tlms),
                self.telemetry_type+"_min": min(tlms)
            }
            return agg_tlm
        else: 
            return {}
        