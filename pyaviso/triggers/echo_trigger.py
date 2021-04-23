# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
from typing import Dict

from .. import logger
from . import trigger
from .trigger import TriggerType


class EchoTrigger(trigger.Trigger):
    """
    This class implements the 'Echo' trigger by printing out to the system log the
    notification
    """

    def __init__(self, notification: Dict[str, any], params: Dict[str, any]):
        trigger.Trigger.__init__(self, notification, params)
        self.trigger_type = TriggerType.echo

    def execute(self):
        logger.info("Starting Echo Trigger...")
        logger.info("Notification received:")
        print(json.dumps(self.notification, indent=4, sort_keys=True))
        logger.debug(f"{self.notification}")
        logger.info("Echo Trigger completed")
