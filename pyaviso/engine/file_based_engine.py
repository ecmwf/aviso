# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import _thread
import os
import threading
import time
from datetime import datetime
from queue import Queue
from shutil import rmtree
from typing import Dict, List

import pyinotify

from .. import logger
from ..authentication.auth import Auth
from ..user_config import EngineConfig
from .engine import Engine


class FileBasedEngine(Engine):
    """
    This class is a specialisation of the Engine class. It implements a file-based server to be used for testing
    """

    def __init__(self, config: EngineConfig, auth: Auth):
        super(FileBasedEngine, self).__init__(config, auth)
        self._listening_list = []
        logger.warning("TEST MODE")
        self._polling_interval = 1  # for testing we can do a much faster polling time
        self._host = "localhost"
        self._port = ""

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
        This method implements a query to the notification server for all the key-values associated to the key as input.
        This key by default is a prefix, it can therefore return a set of key-values
        :param key: input in the query
        :param key_only: ignored for TestEngine
        :param rev: ignored for TestEngine
        :param prefix: if true the function will retrieve all the KV pairs starting with the key passed
        :param min_rev: ignored for TestEngine
        :param max_rev: ignored for TestEngine
        :return: List of key-value pairs formatted as dictionary
        """
        if key_only:
            logger.warning("key_only option is disabled in TestMode")
        if rev:
            logger.warning("rev option is disabled in TestMode")
        if min_rev:
            logger.warning("min_rev option is disabled in TestMode")
        if max_rev:
            logger.warning("max_rev option is disabled in TestMode")

        def read_key(k):
            try:
                with open(k, "r") as f:
                    v = f.read()
            except Exception:
                logger.warning(f"Reading of the {k} has failed")
                logger.debug("", exc_info=True)
                return
            new_kv = {"key": k, "value": v.encode()}
            new_kvs.append(new_kv)
            logger.debug(f"Key: {k} pulled successfully")

        logger.debug(f"Calling pull for {key}...")
        new_kvs: List[Dict[str, bytes]] = []
        if os.path.exists(key):
            if os.path.isdir(key):
                # first list the directory
                for x in os.walk(key):
                    for fp in x[2]:  # any file
                        kk: str = os.path.join(x[0], fp)
                        read_key(kk)
                    if not prefix:  # we only look at the current directory, nothing deeper
                        break
            else:
                read_key(key)

        logger.debug(f"Query for {key} completed")
        logger.debug(f"{len(new_kvs)} keys found")
        return new_kvs

    def delete(self, key: str, prefix: bool = True) -> List[Dict[str, bytes]]:
        """
        This method deletes all the keys associated to this key, the key is a prefix as default
        :param key: key prefix to delete
        :param prefix: if true the function will delete all the KV pairs starting with the key passed
        :return: kvs deleted
        """
        logger.debug(f"Calling delete for {key}...")

        del_kvs: List[Dict[str, bytes]] = []
        if os.path.exists(key):
            if os.path.isdir(key):
                # first list the directory
                for x in os.walk(key):
                    for fp in x[2]:  # any file
                        k: str = os.path.join(x[0], fp)
                        new_kv = {"key": k}
                        del_kvs.append(new_kv)
            else:
                new_kv = {"key": key}
                del_kvs.append(new_kv)

            # now the delete the directory or file
            try:
                if os.path.isdir(key):
                    rmtree(key)
                else:
                    os.remove(key)
            except Exception as e:
                logger.warning(f"Cannot delete the key {key},  {e}")
                logger.debug("", exc_info=True)

        logger.debug(f"Delete request for key {key} completed")

        return del_kvs

    def push(self, kvs: List[Dict[str, any]], ks_delete: List[str] = None, ttl: int = None) -> bool:
        """
        Method to submit a list of key-value pairs and delete a list of keys from the server as a single transaction
        :param kvs: List of KV pair
        :param ks_delete: List of keys to delete before the push of the new ones. Note that each key is read as a folder
        :param ttl: Not supported in this implementation
        :return: True if successful
        """
        logger.debug("Calling push...")

        # first delete the keys requested
        if ks_delete is not None and len(ks_delete) != 0:
            for kd in ks_delete:
                if os.path.exists(kd):
                    try:
                        if os.path.isdir(kd):
                            rmtree(kd)
                        else:
                            os.remove(kd)
                    except Exception as e:
                        logger.warning(f"Cannot delete the key {kd},  {e}")
                        logger.debug("", exc_info=True)

        # save the keys to files
        for kv in kvs:
            k = kv["key"]
            v = kv["value"]
            file_name: str = k.split("/").pop()
            if not file_name == "":
                folder_path = k[: -len(file_name)]
            else:  # if k ends in / it means it the base directory, this is used to saved the status
                folder_path = k
                k += "status"
            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path, exist_ok=True)
                except OSError:
                    logger.warning(f"Cannot create the directory: {folder_path}")
                    logger.debug("", exc_info=True)
                    return False
            try:
                with open(k, "w+") as f:
                    f.write(v)
            except Exception:
                logger.warning(f"Saving of the {k} has failed")
                logger.debug("", exc_info=True)
                return False

        logger.debug("Transaction completed")

        return True

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
        :param from_date: ignored for TestMode
        :param to_date: ignored for TestMode
        :return:
        """
        if from_date:
            logger.warning("from_date option is disabled in TestMode")
        if to_date:
            logger.warning("to_date option is disabled in TestMode")
        try:
            # first create the directory to watch
            if not os.path.exists(key):
                try:
                    os.makedirs(key, exist_ok=True)
                except OSError:
                    logger.warning(f"Cannot create the directory: {key}")
                    logger.debug("", exc_info=True)
                    return False

            # create a watch manager
            wm = pyinotify.WatchManager()  # Watch Manager
            mask = pyinotify.IN_CLOSE_WRITE  # watched events

            # define a class to handle the new events
            class EventHandler(pyinotify.ProcessEvent):
                def __init__(self, engine):
                    super(EventHandler, self).__init__()
                    self._engine = engine

                def process_IN_CLOSE_WRITE(self, event):
                    if not os.path.isdir(event.pathname):
                        kvs = self._engine.pull(key=event.pathname)
                        for kv in kvs:
                            k = kv["key"]
                            v = kv["value"].decode()
                            # skip the status
                            if kv["key"].endswith("status"):
                                continue
                            logger.debug(f"Notification received for key {k}")
                            try:
                                # execute the trigger
                                callback(k, v)
                            except Exception as ee:
                                logger.error(f"Error with notification trigger, exception: {type(ee)} {ee}")
                                logger.debug("", exc_info=True)

            # add the handler to the watch manager and define the watching task
            handler = EventHandler(engine=self)
            notifier = pyinotify.Notifier(wm, handler, read_freq=self._polling_interval)
            wm.add_watch(key, mask, rec=True, auto_add=True)

            # encapsulate the watcher in a daemon thread so we can stop it
            def t_run():
                notifier.loop()

            t = threading.Thread(target=t_run)
            t.setDaemon(True)
            t.start()

            # this is the stop condition
            while key in self._listeners:
                time.sleep(0.1)
            notifier.stop()

        except Exception as e:
            logger.error(f"Error while listening to key {key}, {e}")
            logger.debug("", exc_info=True)
            _thread.interrupt_main()
