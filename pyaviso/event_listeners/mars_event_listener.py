# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from datetime import datetime
from typing import Dict, List

from .event_listener import EventListener
from .. import logger
from ..engine.engine import Engine


class MarsEventListener(EventListener):
    def __init__(self,
                 engine: Engine,
                 request: Dict[str, any],
                 triggers: List[Dict[str, any]],
                 listener_schema: Dict[str, any],
                 from_date: datetime = None,
                 to_date: datetime = None):
        super(MarsEventListener, self).__init__(engine, request, triggers, listener_schema, from_date, to_date)

    def __str__(self):
        return f"MARS listener to keys: {self.keys}"

    def callback(self, key: str, value: str):
        """
        This callback function first parses the key and build a notification dictionary, it then filters it using the
        self.filter requested. If it passes the filter phase the notification is then passed to the triggers
        otherwise the notification is ignored.
        :param key:
        :param value:
        :return:
        """
        # parse and filter the key
        not_request: Dict[str, any] = self.parse_key(key)
        if self._is_expected(not_request):
            # prepare the notification dictionary to pass to the trigger
            notification: Dict[str, any] = {"event": "mars", "request": not_request}
            # execute all the triggers defined in the EventListener
            logger.info("A valid notification has been received, executing triggers...")
            logger.debug(f"{notification}")
            self.execute_triggers(notification)

