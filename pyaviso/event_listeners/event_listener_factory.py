# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from datetime import datetime
from typing import Dict, List, Optional

from .. import logger
from ..engine.engine_factory import EngineFactory
from ..triggers import trigger_factory as tf
from . import event_listener as el


class EventListenerFactory:
    """
    Factory class of EventListener objects. It creates them by parsing a key-value dictionary
    """

    def __init__(self, engine_factory: EngineFactory, listener_schema: Dict[str, any]):
        """
        :param engine_factory:
        :param listener_schema:
        """
        self._engine_factory = engine_factory
        self._listener_schema = listener_schema

    def create_listeners(
        self,
        listeners_dict: Dict[str, any],
        from_date: datetime = None,
        to_date: datetime = None,
        payload_key: str = None,
    ) -> List[el.EventListener]:
        """
        This method is used to parse a key-value dictionary and create a list of event listeners.

        :param listeners_dict: key-value dictionary to parse
        :param from_date: date from when to request notifications, if None it will be from now
        :param to_date: date until when to request notifications, if None it will be until now
        :param payload_key: key to use for the payload in the notification dictionary
        :return: a list of EventListener objects
        """
        listeners: List[el.EventListener] = []

        # parse the listeners dictionary
        logger.debug("Parsing the listeners file")
        assert listeners_dict is not None, "Event listeners definition cannot be empty"
        listener_list: Optional[List[Dict[str, any]]] = listeners_dict.get("listeners")
        assert listener_list is not None, "Event listeners definition must start with the keyword 'listeners'"

        # Create the engine to connect to the notification server
        engine = self._engine_factory.create_engine()

        for listen in listener_list:
            # each listener is a dictionary
            assert isinstance(listen, dict), "Wrong file structure"

            # extract the relevant listener schema
            assert "event" in listen, "Wrong file structure, 'event' could not be located"
            event_type = listen.get("event")
            assert event_type in self._listener_schema, f"Wrong schema structure, {event_type} could not be located"
            schema = self._listener_schema.get(event_type)

            # Parse the request and build the key to the forecast dataset
            assert "request" in listen, "Wrong file structure, 'request' could not be located"
            request: Optional[Dict[str, any]] = listen.get("request")

            # Parse the triggers
            triggers: Optional[List[Dict[str, any]]] = self._parse_triggers(listen)

            # create the listener
            listener = el.EventListener(event_type, engine, request, triggers, schema, from_date, to_date, payload_key)
            listeners.append(listener)

        return listeners

    def _parse_triggers(self, listener: Dict[str, any]) -> Optional[List[Dict[str, any]]]:
        """
        This method parses the triggers block and return the list of trigger types to use
        :param listener:
        :return:
        """
        # Parse the triggers
        assert "triggers" in listener, "'triggers' is a mandatory field"
        triggers: Optional[List[Dict[str, any]]] = listener.get("triggers")
        assert triggers is not None, "At least one trigger must be defined"
        # validate the types of the triggers
        for t in triggers:
            assert "type" in t, "'type' is a mandatory field in trigger"
            try:
                # early validation of the trigger type
                tf.TriggerType[t.get("type").lower()]
            except KeyError as e:
                raise KeyError(f"Trigger type {e.args[0]} not recognised")

        return triggers
