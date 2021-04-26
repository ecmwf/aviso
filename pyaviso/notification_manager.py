# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from datetime import datetime
from typing import Dict, List, Tuple

import yaml

from . import exit_channel, logger, user_config
from .authentication.auth import Auth
from .custom_exceptions import EventListenerException, InvalidInputError
from .engine import engine_factory as ef
from .event_listeners.event_listener import DEFAULT_PAYLOAD_KEY, EventListener
from .event_listeners.listener_manager import ListenerManager


class NotificationManager:
    """
    This class manages implements the various operations associated to the notification system
    """

    def __init__(self):
        self.listener_manager = ListenerManager()

    def _listen(
        self,
        config: user_config.UserConfig = None,
        listeners_file_paths: List[str] = None,
        listeners: Dict[str, any] = None,
        from_date: datetime = None,
        to_date: datetime = None,
    ) -> int:
        """
        This method parses the inputs and calls the listener manager to create the listeners
        :param config: UserConfig object
        :param listeners_file_paths: list of file paths to YAML listener files
        :param listeners: listeners as dictionaries
        :param from_date: date from when to request notifications, if None it will be from now
        :param to_date: date until when to request notifications, if None it will be until now
        :return: number of listeners running
        """
        # check we have listeners
        listeners_list = []
        if listeners_file_paths is not None and len(listeners_file_paths) > 0:
            listeners_list = self._load_listener_files(listeners_file_paths)
        elif listeners is None:
            if hasattr(config, "listeners"):
                listeners_list.append(config.listeners)
            else:
                raise EventListenerException("Listeners not defined")
        else:
            listeners_list.append(listeners)

        # retrieve listener schema
        listener_schema = config.schema_parser.parser().load(config)

        # Call the listener manager
        return self.listener_manager.listen(listeners_list, listener_schema, config, from_date, to_date)

    def listen(
        self,
        config: user_config.UserConfig = None,
        listeners_file_paths: List[str] = None,
        listeners: Dict[str, any] = None,
        from_date: datetime = None,
        to_date: datetime = None,
        now: bool = False,
        catchup: bool = False,
    ):
        """
        This method implements the main workflow to instantiate and execute new listeners and holding the main thread in
        active waiting.
        :param config: UserConfig object
        :param listeners_file_paths: list of file paths to YAML listener files
        :param listeners: listeners as dictionaries
        :param from_date: date from when to request notifications, if None it will be from now
        :param to_date: date until when to request notifications, if None it will be until now
        :param now: if True ignore missed notifications, only listen to new ones
        :param catchup: if True retrieve first the missed notifications
        :return:
        """
        logger.debug("Calling listen...")

        # first check the config
        if config is None:
            config = user_config.UserConfig()

        # check the inputs
        now_date = datetime.utcnow()
        if from_date:
            assert from_date < now_date, "from_date must be in the past"
        if to_date:
            assert to_date < now_date, "to_date must be in the past"
            assert from_date is not None, "from_date is required if to_date is defined"
            assert to_date > from_date, "to_date must be later than from_date"

        # define the catchup behaviour and set it in the notification engine
        assert not (now and catchup), "Only now or catchup can be specified at the same time"
        if catchup:
            config.notification_engine.catchup = True
        else:
            if now:
                config.notification_engine.catchup = False

        # Call the listener manager
        self._listen(config, listeners_file_paths, listeners, from_date, to_date)

        # keep the main process running and wait for the listening thread to terminate
        l_exit = exit_channel.get()  # this is blocking until all listener ends or there is an error
        if l_exit:  # it exits successful
            return
        else:  # it exits with errors
            raise EventListenerException("Error in one of the listening process")

    def key(
        self, params: Dict, config: user_config.UserConfig = None, listener_schema: Dict = None
    ) -> Tuple[str, str, str]:
        """
        Generate a key to send to the notification server with the params passed and complying to the current schema
        :param params: parameters to use in the key
        :param config:
        :param listener_schema: event listener schema are loaded as dictionary
        :return: tuple of leaf key and root key
        """
        logger.debug(f"Calling generate key with the following parameters {params}...")

        # first check the config
        if config is None:
            config = user_config.UserConfig()

        if "event" not in params:
            raise InvalidInputError("Invalid notification, 'event' could not be located")
        listener_type = params["event"]

        if not listener_schema:
            # retrieve listener schema
            logger.debug("Getting schema...")
            listener_schema = config.schema_parser.parser().load(config)
        # # extract the relevant listener schema
        if listener_type not in listener_schema:
            raise InvalidInputError(f"Invalid notification, {listener_type} could not be located in the schema")
        event_schema = listener_schema.get(listener_type)
        logger.debug("Relevant schema successfully found")

        logger.debug("Generating key...")
        filtered_params = params.copy()
        filtered_params.pop("event")
        key, root, admin_key = EventListener.derive_notification_keys(
            filtered_params, event_schema, config.notification_engine.type
        )
        logger.debug(f"Keys generated {root}, {key}, {admin_key}")

        return key, root, admin_key

    def value(self, params: Dict, config: user_config.UserConfig = None) -> str:
        """
        :param params: parameters to use in the key
        :param config:
        :return: the value on the server corresponding to the key which is generated according to the current schema and
        the parameters defined
        """
        logger.debug(f"Calling get value with the following parameters {params}...")

        # first check the config
        if config is None:
            config = user_config.UserConfig()

        # first generate the key corresponding the to the parameters passed
        key, base_key, admin_key = self.key(params, config)

        # create the engine
        engine_factory: ef.EngineFactory = ef.EngineFactory(config.notification_engine, Auth.get_auth(config))
        engine = engine_factory.create_engine()

        # retrieve the value
        kvs = engine.pull(key=key, prefix=False)
        assert len(kvs) < 2, "Error in retrieving value from key, more than one value returned"
        if len(kvs) == 0:
            logger.debug("No value returned")
        else:
            return kvs[0]["value"].decode()

    def notify(self, notification: Dict, config: user_config.UserConfig = None) -> bool:
        """
        Send a notification to the server. The notification is made of a key-value pair created using the params passed
        and a status that is sent to the base key. This is needed for the catchup feature.
        :param notification: dictionary of the notification ready to submit
        :param config: UserConfig object
        :return: True if the notification has been submitted
        """
        logger.debug(f"Calling notify with the following notification {notification}...")

        # first check the config
        if config is None:
            config = user_config.UserConfig()

        # retrieve listener schema
        logger.debug("Getting schema...")
        listener_schema = config.schema_parser.parser().load(config)

        # validate the input
        try:
            # check the payload key
            payload_key = listener_schema.get("payload")
            if not payload_key:
                payload_key = DEFAULT_PAYLOAD_KEY
            assert "event" in notification, "Invalid notification, 'event' could not be located"
            value = "None"
            if payload_key in notification:
                value = notification.pop(payload_key)
        except AssertionError as e:
            raise InvalidInputError(e)

        # first check the config
        if config is None:
            config = user_config.UserConfig()

        # read the TTL for this key
        ttl = config.key_ttl
        if "ttl" in notification:
            ttl = int(notification.pop("ttl"))
        # translate default -1 into the default of the engine interface
        ttl = None if ttl == -1 else ttl

        # generate the key
        key, base_key, admin_key = self.key(notification, config, listener_schema)

        # create the engine
        engine_factory: ef.EngineFactory = ef.EngineFactory(config.notification_engine, Auth.get_auth(config))
        engine = engine_factory.create_engine()

        # submit the notification with status update
        logger.debug(f"Submit key {key}, value {value} with status update")
        kvs = [{"key": key, "value": value}]
        engine.push_with_status(
            kvs, base_key=base_key, admin_key=admin_key, message=f"notification to key {key}", ttl=ttl
        )

        return True

    def _load_listener_files(self, listener_files: List[str]):
        """
        :param listener_files: list of file paths to YAML listener files
        :return: return list of dictionaries from the listener files
        """
        # Open YAML notification listener files
        assert listener_files is not None
        listeners: List[Dict[str, any]] = []
        for listener_file in listener_files:
            logger.debug(f"Reading listener file {listener_file}")
            try:
                with open(listener_file, "r") as f:
                    listeners_dict = yaml.safe_load(f)
                    listeners.append(listeners_dict)
            except Exception as e:
                raise EventListenerException(f"Not able to load listener file {listener_file},{e}")
        return listeners
