# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
from typing import Dict

from .. import logger
from . import trigger
from .trigger import TriggerType


class LogTrigger(trigger.Trigger):
    """
    This class implements the 'Log' trigger by logging to the log file specified the
    notification received
    """

    def __init__(self, notification: Dict[str, any], params: Dict[str, any]):
        trigger.Trigger.__init__(self, notification, params)
        self.trigger_type = TriggerType.log

    def execute(self):
        logger.info("Starting Log Trigger...")
        # create a file handler for the log specified
        log_path = self.params.get("path")
        handler = logging.FileHandler(log_path, "a")
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        # get the logger and the new file handler to it
        log = logging.getLogger()
        log.addHandler(handler)
        # log the notification
        logger.info(f"Notification received: {self.notification}")
        # remove the logger
        log.removeHandler(handler)
        logger.info("Log Trigger completed")
