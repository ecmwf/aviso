# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Dict

from .. import logger
from .trigger import Trigger, TriggerType


class TriggerFactory:
    """
    This class is in charge of creating a trigger for the specific trigger requested.
    """

    def create_trigger(self, notification: Dict[str, any], params: Dict[str, any]) -> Trigger:

        assert "type" in params, "'type' is a mandatory field in trigger"
        # find specific trigger class
        trigger_type = TriggerType[params.get("type").lower()]
        trigger_class = trigger_type.get_class()

        # instantiate the specific trigger
        logger.debug(f"Creating {trigger_type.name} trigger...")
        t = trigger_class(notification, params)
        logger.debug(f"Trigger {trigger_type.name} created")

        return t
