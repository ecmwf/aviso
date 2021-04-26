# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Callable, Dict

from .. import logger
from . import trigger
from .trigger import TriggerType


class FunctionTrigger(trigger.Trigger):
    """
    This class implements the 'Function' trigger by executing the function defined by the user and
    passing the notification key and value and the params as argument
    """

    def __init__(self, notification: Dict[str, any], params: Dict[str, any]):
        trigger.Trigger.__init__(self, notification, params)
        assert self.params.get("function") is not None, "'function' is a mandatory field for the 'Function' trigger"
        self.function: Callable = self.params.get("function")
        self.trigger_type = TriggerType.function

    def execute(self):
        logger.info("Starting Function Trigger...")
        logger.debug(f"calling function {self.function.__name__}")

        # run the function
        logger.debug("Running function trigger")
        self.function(self.notification)

        logger.info("Function Trigger completed")
