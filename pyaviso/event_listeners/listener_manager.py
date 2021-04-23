# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from datetime import datetime
from typing import Dict, List

from .. import logger, user_config
from ..authentication.auth import Auth
from ..custom_exceptions import EventListenerException
from ..engine import engine_factory as ef
from . import event_listener_factory as elf
from .event_listener import EventListener


class ListenerManager:
    """
    This class manages the execution of the various event listeners
    """

    def __init__(self):
        self._listeners: List[EventListener] = []

    @property
    def listeners(self) -> List[EventListener]:
        return self._listeners

    def _run_listeners(self) -> bool:
        """
        This method is used to execute all the listeners currently managed

        :return: True if all the listeners are in execution, False otherwise
        """
        logger.debug("Calling run all listeners...")
        result = True
        listener_to_remove: List[EventListener] = []
        for listener in self._listeners:
            # Execute the listener
            if not listener.listen():
                result = False
                listener_to_remove.append(listener)
            else:
                keys = ",".join(listener.keys)
                logger.info(f"Listening to {keys} at {listener.engine.host}:{listener.engine.port}...")

        # now remove all of the listeners that were not able to start
        for listener in listener_to_remove:
            self._listeners.remove(listener)

        return result

    def _add_listener(self, listener: EventListener) -> None:
        """
        Add a listener to the internal listener list of the manager

        :param listener: EventListener object
        """
        self._listeners.append(listener)

    def _add_listeners(self, listeners: List[EventListener]) -> None:
        """
        Add the listener list to the internal listener list of the manager

        :param listeners: EventListener list
        """
        for listener in listeners:
            self._add_listener(listener)

    def _stop_listener(self, listener: EventListener) -> bool:
        """
        Stop the execution of listener passed as argument.

        :param listener: EventListener object
        :return: True if stopped, False otherwise
        """
        try:
            logger.debug(f"Calling stop {listener}...")
            # Stop the listener
            return listener.stop()
        except ValueError as error:
            logger.error(f"Error in stopping listener, exception message: {error}")
            logger.debug("", exc_info=True)
            return False

    def _cancel_listener(self, listener: EventListener) -> None:
        """
        Stop and delete the listener passed as argument

        :param listener: EventListener object
        """
        # first stop listener
        self._stop_listener(listener)
        # now remove it from the list
        self._listeners.remove(listener)

    def cancel_listeners(self) -> None:
        """
        Stop the execution of any listener currently in execution

        :return: True if no listener is currently in execution
        """
        # first cancel all the notification listeners
        for listener in self._listeners:
            self._stop_listener(listener)

        # now remove all of them from the internal list
        self._listeners.clear()

    def listen(
        self,
        listeners: List[Dict[str, any]],
        listener_schema: Dict[str, any],
        config: user_config.UserConfig = None,
        from_date: datetime = None,
        to_date: datetime = None,
    ) -> int:
        """
        This method implements the main workflow to instantiate and execute new listeners
        :param listeners: listeners as list of dictionaries
        :param listener_schema: schema to use to validate the listeners
        :param config: UserConfig object
        :param from_date: date from when to request notifications, if None it will be from now
        :param to_date: date until when to request notifications, if None it will be until now
        :return: number of listeners running
        """
        logger.debug("Calling listen in ListenerManager...")

        # first check the config
        if config is None:
            config = user_config.UserConfig()

        # Create the engine and listener factories
        engine_factory: ef.EngineFactory = ef.EngineFactory(config.notification_engine, Auth.get_auth(config))
        listener_factory: elf.EventListenerFactory = elf.EventListenerFactory(engine_factory, listener_schema)

        # read the payload key from the schema
        payload_key = listener_schema.get("payload")

        # Parse notification listeners
        event_listeners: List[EventListener] = []
        for ls in listeners:
            logger.debug(f"Reading listeners {ls}")
            try:
                for ev_listener in listener_factory.create_listeners(ls, from_date, to_date, payload_key):
                    event_listeners.append(ev_listener)
                logger.debug("Listener dictionary correctly parsed")
            except Exception as e:
                raise EventListenerException(f"Not able to load listener dictionary {ls}: {e}")

        # Add the listeners to the manager and run them
        logger.debug("Starting listeners...")
        self._add_listeners(event_listeners)
        if not self._run_listeners():
            if len(self.listeners) == 0:
                raise EventListenerException("Listeners could not start, please check logs")
            else:
                logger.error("One or more listeners were not able to start")

        # return the number of listeners running
        return len(self.listeners)
