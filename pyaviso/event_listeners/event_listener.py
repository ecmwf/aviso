# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import itertools
import re
from datetime import datetime
from typing import Dict, List

import parse

from .. import logger
from ..custom_exceptions import EventListenerException
from ..engine import EngineType
from ..engine.engine import Engine
from ..triggers import trigger_factory as tf
from .validation import *  # noqa: F403

DEFAULT_PAYLOAD_KEY = "payload"


class EventListener:
    """
    This class contains of all the details needed to create an event listener and execute its triggers
    """

    def __init__(
        self,
        event_type: str,
        engine: Engine,
        request: Dict[str, any],
        triggers: List[Dict[str, any]],
        listener_schema: Dict[str, any],
        from_date: datetime = None,
        to_date: datetime = None,
        payload_key: str = None,
    ):
        self._event_type = event_type
        self._engine = engine
        self._request = request if request else {}
        self._triggers = triggers
        self._listener_schema = listener_schema
        self._trigger_factory = tf.TriggerFactory()
        self._keys = self.key_expansion(self._request)
        self._filter = self.filter_expansion(self._request)
        self._from_date = from_date
        self._to_date = to_date
        self.payload_key = payload_key

    def __str__(self):
        return f"{self.event_type} listener to keys: {self.keys}"

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def payload_key(self) -> str:
        return self._payload_key

    @payload_key.setter
    def payload_key(self, payload_key: any):
        if payload_key:
            self._payload_key = payload_key
        else:
            self._payload_key = DEFAULT_PAYLOAD_KEY

    @property
    def from_date(self) -> datetime:
        return self._from_date

    @property
    def to_date(self) -> datetime:
        return self._to_date

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def request(self) -> Dict[str, any]:
        return self._request

    @property
    def keys(self) -> List[str]:
        return self._keys

    @property
    def triggers(self) -> List[Dict[str, any]]:
        return self._triggers

    @property
    def listener_schema(self) -> Dict[str, any]:
        return self._listener_schema

    @property
    def trigger_factory(self) -> tf.TriggerFactory:
        return self._trigger_factory

    def key_expansion(self, request: Dict[str, any]) -> List[str]:
        """
        This functions composes the keys to watch using the listener request dictionary
        :param request:
        :return: List of keys
        """
        # read the key format from the schema
        key_base = EventListener._key_base_format(self.listener_schema, self.engine.engine_type)
        try:
            key: str = key_base.format(**request)
        except KeyError as e:
            raise KeyError(f"Wrong listener file: {','.join(e.args)} required")

        # compose multiple keys from the list values
        keys: List[str] = []
        template = r"\[[^\[\]]*\]"
        matches = re.findall(template, key)
        if len(matches) == 0:
            keys.append(key)
        else:
            # Build a list of the possible substitutions
            ldests = []
            for m in matches:
                ldests.append(eval(m))
            # Generate the various pairings
            for lproduct in itertools.product(*ldests):
                k = key
                for src, dest in itertools.zip_longest(matches, lproduct):
                    # Replace each term (you could optimise this using a single re.sub)
                    k = k.replace(src, dest)
                keys.append(k)
        return keys

    def filter_expansion(self, request: Dict[str, any]) -> Dict[str, List[any]]:
        """
        This method builds from the request the filter used in the post-notification phase
        :param request:
        :return: filter as a dictionary
        """
        # initialise the filter
        request_filter: Dict[str, List[any]] = {}
        # get the request schema
        assert "request" in self.listener_schema, "Wrong schema structure, 'request' could not be located"
        request_schema = self.listener_schema["request"]

        # validate and canonize the request
        EventListener._validate(request, request_schema)

        # scan through the request to create the filter object
        for r in request.keys():
            request_filter[r] = []
            value = request[r]
            if type(value) is list:
                for v in value:
                    request_filter[r].append(v)
            else:
                request_filter[r].append(value)

        return request_filter

    def parse_key(self, key: str) -> Dict[str, any]:
        """
        This function parses the key string received as part of the notification and create a dictionary out of it
        :param key:
        :return:
        """
        # read the key format from the schema
        key_put_format = EventListener._key_base_format(
            self.listener_schema, self.engine.engine_type
        ) + EventListener._key_stem_format(self.listener_schema, self.engine.engine_type)

        try:
            notification: Dict[str, any] = parse.parse(key_put_format, key, extra_types=[str]).named
        except AttributeError as e:
            logger.debug("", exc_info=True)
            raise EventListenerException(f"Key {key} failed validation, exception: {e}")
        return notification

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
            notification: Dict[str, any] = {"event": self.event_type, "request": not_request}
            if value != "None":
                notification[self.payload_key] = value
            # execute all the triggers defined in the EventListener
            logger.info("A valid notification has been received, executing triggers...")
            logger.debug(f"{notification}")
            self.execute_triggers(notification)

    def listen(self) -> bool:
        """
        This method is used to turn a EventListener object to an active notification request to the underlying
        notification mechanism. This method relies on the specific implementation of Engine class to activate the
        listener.

        :return: True if the listener is in execution, False otherwise
        """
        return self._engine.listen(self.keys, self.callback, self.from_date, self.to_date)

    def stop(self) -> bool:
        """
        This method is used to stop an active notification listener running on the underlying notification mechanism.

        :return: True if the listener has been cancelled
        """
        if self._engine.stop():
            logger.debug(f"{self} has been stopped")
            return True
        else:
            logger.warning(f"{self} not currently in execution")
            return False

    def execute_triggers(self, notification: Dict[str, any]):
        """
        This function is used to execute the triggers associated with this EventListener.
        :param notification:
        :return:
        """
        # execute all the triggers defined in the EventListener in order
        for t in self.triggers:
            try:
                # create the trigger
                trigger = self.trigger_factory.create_trigger(notification, t)
            except Exception as e:
                logger.error(f"Trigger {t} could not be created, {type(e)}: {e}")
                logger.debug("", exc_info=True)
                break  # the whole triggers execution stop
            else:  # run the trigger
                try:
                    trigger.execute()
                except Exception as e:
                    logger.error(f"Trigger {t} could not be executed,  {e}")
                    logger.debug("", exc_info=True)
                    break  # the whole triggers execution stop

    @staticmethod
    def derive_notification_keys(params: Dict[str, any], schema: Dict[str, any], engine_type: EngineType):
        """
        This function compose all the keys needed for a notification to the server using the parameters passed and
        the schema
        :param params:
        :param schema:
        :param engine_type
        :return: stem_key, base_key, admin_key
        """
        # get the request schema
        assert "request" in schema, "Wrong schema structure, 'request' could not be located"
        request_schema = schema["request"]
        # validate and canonize parameters
        EventListener._validate(params, request_schema)

        # read the base key format from the schema
        key_base_format = EventListener._key_base_format(schema, engine_type)
        try:
            # create the base key
            base_key: str = key_base_format.format(**params)
        except KeyError as e:
            raise KeyError(f"Wrong parameters: {','.join(e.args)} required")

        # read the stem key format from the schema
        key_stem_format = key_base_format + EventListener._key_stem_format(schema, engine_type)
        try:
            # create the stem key
            stem_key: str = key_stem_format.format(**params)
        except KeyError as e:
            raise KeyError(f"Wrong parameters: {','.join(e.args)} required")

        # read the admin key format from the schema
        key_admin_format = EventListener._key_admin_format(schema, engine_type)
        if key_admin_format:
            try:
                # create the admin key
                admin_key = key_admin_format.format(**params)
            except KeyError as e:
                raise KeyError(f"Wrong parameters: {','.join(e.args)} required")
        else:
            admin_key = None

        return stem_key, base_key, admin_key

    def _is_expected(self, notification: Dict) -> bool:
        """
        Helper method used to validate the notification received against the filters defined
        :param notification:
        :return:
        """
        expected = True
        for f_key, f_values in self._filter.items():
            assert f_key in notification, "Filter attribute not present in the notification"
            n_value = notification[f_key]
            # infer the type of the attributes from the filter type, the default is string
            if type(f_values[0]) is int:
                n_value = int(n_value)
            # now check if it matches the filters
            if n_value not in f_values:
                # notification does NOT complies with this filter attribute
                expected = False
                logger.debug(
                    f"Notification {notification} failed filter {f_key} with value {n_value} therefore it "
                    f"will be ignored"
                )
                break
        return expected

    @staticmethod
    def _key_base_format(schema, engine_type: EngineType) -> str:
        """
        Helper method used to extract the key base format from the schema
        :param schema:
        :param engine_type:
        :return: key base format
        """
        base_key_f = None
        assert "endpoint" in schema, "Wrong schema structure, 'endpoint' could not be located"
        endpoints = schema["endpoint"]
        assert len(endpoints) > 0, "Wrong schema structure, 'endpoint' should be a non empty list"
        for endpoint in endpoints:
            assert "engine" in endpoint, "Wrong schema structure, 'engine' in 'endpoint' could not be located"
            if engine_type.name.lower() in endpoint["engine"]:
                assert "base" in endpoint, "Wrong schema structure, 'base' in 'endpoint' could not be located"
                base_key_f = endpoint["base"]
                if not base_key_f.endswith("/"):
                    base_key_f = base_key_f + "/"
                break
        if base_key_f is None:
            raise EventListenerException("Key base could bot be located in the schema")
        return base_key_f

    @staticmethod
    def _key_stem_format(schema, engine_type: EngineType) -> str:
        """
        Helper method used to extract the key stem format from the schema
        :param schema:
        :param engine_type:
        :return: key stem format
        """
        stem_key_f = None
        assert "endpoint" in schema, "Wrong schema structure, 'endpoint' could not be located"
        endpoints = schema["endpoint"]
        assert len(endpoints) > 0, "Wrong schema structure, 'endpoint' should be a non empty list"
        for endpoint in endpoints:
            assert "engine" in endpoint, "Wrong schema structure, 'engine' in 'endpoint' could not be located"
            if engine_type.name.lower() in endpoint["engine"]:
                assert "stem" in endpoint, "Wrong schema structure, 'stem' in 'endpoint' could not be located"
                stem_key_f = endpoint["stem"]
                if stem_key_f.startswith("/"):
                    stem_key_f = stem_key_f[1 : len(stem_key_f)]
                break
        if stem_key_f is None:
            raise EventListenerException("Key base could bot be located in the schema")
        return stem_key_f

    @staticmethod
    def _key_admin_format(schema, engine_type: EngineType) -> str:
        """
        Helper method used to extract the key admin format from the schema
        :param schema:
        :param engine_type:
        :return: admin key format
        """
        admin_key_f = None
        assert "endpoint" in schema, "Wrong schema structure, 'endpoint' could not be located"
        endpoints = schema["endpoint"]
        assert len(endpoints) > 0, "Wrong schema structure, 'endpoint' should be a non empty list"
        for endpoint in endpoints:
            assert "engine" in endpoint, "Wrong schema structure, 'engine' in 'endpoint' could not be located"
            if engine_type.name.lower() in endpoint["engine"]:
                admin_key_f = endpoint.get("admin")
                break
        return admin_key_f

    @staticmethod
    def _validate(params, schema):
        """
        This private method validates and canonises the parameters passed using the schema.
        Note that the old params values are overwritten by the canonised values.
        :param params:
        :param schema:
        :return:
        """
        for p in params.keys():
            # check if this attribute is defined in the schema
            assert p in schema.keys(), f"Key {p} is not allowed"
            type_list = schema[p]
            valid = False
            for p_schema in type_list:
                try:
                    assert "type" in p_schema, f"Wrong schema structure, 'type' could not be located for {p}"
                    p_schema_c = p_schema.copy()
                    validator_class = p_schema_c.pop("type")
                    validator: TypeHandler = eval(f"{validator_class}(key=p, **p_schema_c)")  # noqa: F405
                    # format the values associated to this attribute
                    value = params[p]
                    if type(value) is list:
                        params[p] = []
                        for v in value:
                            params[p].append(validator.process(v))
                    else:
                        params[p] = validator.process(value)
                    # if no ValueError have been generated exit and don't valid against the other type handlers
                    valid = True
                    break
                except ValueError as e:
                    logger.debug(f"{e}")
            # check if at least one type handler was valid
            if not valid:
                raise ValueError(f"Value {params[p]} is not valid for key {p}")
