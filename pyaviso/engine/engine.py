# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import getpass
import json
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from queue import Queue
from typing import Dict, List

from .. import __version__, exit_channel, logger
from ..authentication.auth import Auth
from ..user_config import EngineConfig
from . import EngineType

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class Engine(ABC):
    """
    This class implements the interface to the notification server. It is abstract to separate the interface from the
    specific notification server
    """

    def __init__(self, config: EngineConfig, auth: Auth):
        super(Engine, self).__init__()
        self._host = config.host
        self._port = config.port
        self._polling_interval = config.polling_interval
        self._engine_type = config.type
        self.timeout = config.timeout
        self.catchup = config.catchup
        self._auth = auth
        self._https = config.https
        self.automatic_retry_delay = config.automatic_retry_delay
        self._listeners = []
        # this is used to synchronise multiple listening threads accessing the state
        self._state_lock = threading.Lock()
        # this is used to synchronise multiple listening threads accessing the listeners list
        self._listeners_lock = threading.Lock()

    @property
    def engine_type(self) -> EngineType:
        return self._engine_type

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def auth(self) -> Auth:
        return self._auth

    @property
    def https(self) -> bool:
        return self._https

    @abstractmethod
    def pull(
        self,
        key: str,
        key_only: bool = False,
        rev: int = None,
        prefix: bool = True,
        min_rev: int = None,
        max_rev: int = None,
    ) -> List[Dict[str, any]]:
        """
        Abstract method to query the notification server for all the key-values associated to the key as input.
        This key can be a prefix, it can therefore return a set of key-values
        :param key: input in the query
        :param key_only: if True no values are returned
        :param rev: revision to pull
        :param prefix: if true the function will retrieve all the KV pairs starting with the key passed
        :param min_rev: if provided it filters for only KV pairs with mod_revision >= to min_rev
        :param max_rev: if provided it filters for only KV pairs with mod_revision <= to max_rev
        :return: List of key-value pairs formatted as dictionary
        """
        pass

    @abstractmethod
    def push(self, kvs: List[Dict[str, any]], ks_delete: List[str] = None, ttl: int = None) -> bool:
        """
        Abstract method to submit a list of key-value pairs and delete a list of keys from the server as a
        single transaction
        :param kvs: List of KV pair
        :param ks_delete: List of keys to delete before the push of the new ones. Note that each key is read as a folder
        :param ttl: time to leave of the keys pushed, once expired the keys will be deleted
        :return: True if successful
        """
        pass

    @abstractmethod
    def delete(self, key) -> List[Dict[str, bytes]]:
        """
        This method deletes all the keys associated to this prefix
        :param key: key prefix to delete
        :return: kvs deleted
        """
        pass

    @abstractmethod
    def _polling(
        self,
        key: str,
        callback: callable([str, str]),
        channel: Queue,
        from_date: datetime = None,
        to_date: datetime = None,
    ):
        """
        This method implements the active polling
        :param key: key to watch as a prefix
        :param callback: function to call if any change happen
        :param channel: global communication channel among threads
        :param from_date: date from when to request notifications, if None it will be from now
        :param to_date: date until when to request notifications, if None it will be until now
        :return:
        """
        pass

    def listen(
        self, keys: List[str], callback: callable([str, str]), from_date: datetime = None, to_date: datetime = None
    ) -> bool:
        """
        This method allows to listen for changes to specific keys. Note that the key is always considered as a prefix.
        The listening is implemented with a background thread doing a active polling. Multiple listening threads can
        be created by calling this method multiple times.

        :param keys: keys to watch
        :param callback: function to trigger in case of changes
        :param from_date: date from when to request notifications, if None it will be from now
        :param to_date: date until when to request notifications, if None it will be until now
        :return: True if the listener is in execution, False otherwise
        """
        logger.debug("Calling listen...")
        for key in keys:
            try:
                # create a background thread for the polling
                t = threading.Thread(target=self._polling, args=(key, callback, exit_channel, from_date, to_date))
                t.setDaemon(True)
                # adding the thread to the global list
                logger.debug(f"Starting thread to listen to {key}")
                self._add_listener(key)
                t.start()
                logger.debug(f"Thread {t.ident} started to listen to {key}")
            except Exception as e:
                logger.error(f"Error in listening to {key}: {e}")
                logger.debug("", exc_info=True)
                self._remove_listener(key)
                return False
        return True

    def stop(self, key: str = None) -> bool:
        """
        This method is used to stop a listening thread. if no key is provided all the listening thread will be stopped

        :param key: the key associated to the listening thread
        :return: True if the listener is cancelled, False otherwise
        """
        logger.debug("Calling stop...")
        if len(self._listeners) > 0:
            if key is None:  # if not key is defined we simply stop all the listeners
                # by removing its entry from this list the thread will automatically stop
                logger.debug("Stopping all the polling")
                self._remove_all_listeners()
                return True
            elif key in self._listeners:
                # stop the polling
                logger.debug(f"Stopping the polling for key {key}")
                # by removing its entry from this list the thread will automatically stop
                self._remove_listener(key)
                return True
            else:
                logger.debug(f"Cannot find polling of key {key}")
                return False
        return True

    def push_with_status(
        self,
        kvs: List[Dict[str, any]],
        base_key: str,
        message: str = "",
        admin_key: str = None,
        ks_delete: List[str] = None,
        ttl: int = None,
    ) -> bool:
        """
        Method to submit a list of key-value pairs and delete a list of keys from the server as a
        single transaction. This method also updates the status of the base key.
        :param kvs: List of KV pair
        :param base_key: base key where to push the status
        :param message: message to be part of the status update
        :param admin_key: admin key to push together with the status
        :param ks_delete: List of keys to delete before the push of the new ones. Note that each key is read as a folder
        :param ttl: time to leave of the keys pushed, once expired the keys will be deleted
        :return: True if successful
        """
        # create the status payload
        status = {
            "etcd_user": self.auth.username,
            "message": message,
            "unix_user": getpass.getuser(),
            "aviso_version": __version__,
            "engine": self._engine_type.name,
            "hostname": os.uname().nodename,
            "date_time": datetime.utcnow().strftime(DATE_FORMAT),
        }

        # update the status with the revision of the current status. This helps creating a linked list
        old_status_kvs = self.pull(base_key, prefix=False)
        if len(old_status_kvs) == 1:
            self._status_as_linked_list(status, old_status_kvs)

        status_kv = {"key": base_key, "value": json.dumps(status)}  # push it as a json
        kvs.append(status_kv)

        if admin_key:
            # prepare the admin key value pair
            admin_kv = {"key": admin_key, "value": "None"}
            kvs.append(admin_kv)

        return self.push(kvs, ks_delete, ttl)

    def _status_as_linked_list(self, new_status, old_status_kvs):
        if "mod_rev" in old_status_kvs[0]:  # test engine does not have it
            new_status["prev_rev"] = old_status_kvs[0]["mod_rev"]

            # update the status with date and rev of the last_prev_day. This helps creating a linked list across days
            old_status = json.loads(old_status_kvs[0]["value"].decode())
            old_date_time = datetime.strptime(old_status["date_time"], DATE_FORMAT)
            new_date_time = datetime.strptime(new_status["date_time"], DATE_FORMAT)

            # compare status dates
            if old_date_time.date() == new_date_time.date():
                # we are still on the same day
                if "last_prev_day_rev" in old_status:
                    new_status["last_prev_day_rev"] = old_status["last_prev_day_rev"]
            else:
                # new day -> use the previous status as last_prev_day
                new_status["last_prev_day_rev"] = new_status["prev_rev"]

    def _add_listener(self, key: str):
        with self._listeners_lock:
            self._listeners.append(key)

    def _remove_all_listeners(self):
        with self._listeners_lock:
            self._listeners.clear()

    def _remove_listener(self, key: str):
        with self._listeners_lock:
            self._listeners.remove(key)
