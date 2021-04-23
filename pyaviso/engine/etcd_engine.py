# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import fcntl
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from queue import Queue
from typing import Any, Tuple

from .. import HOME_FOLDER, logger
from ..authentication.auth import Auth
from ..custom_exceptions import EngineException, EngineHistoryNotAvailableError
from ..user_config import EngineConfig
from .engine import DATE_FORMAT, Engine

MAX_KV_RETURNED = 10000
LOCAL_STATE_FOLDER = "etcd/last"
LAST_REVISION_FILE = "revision.json"


class EtcdEngine(Engine, ABC):
    """
    This class is a specialisation of the Engine class but it is still abstract. It provides common functions for the
    Etcd specialisation.
    """

    def __init__(self, config: EngineConfig, auth: Auth):
        super(EtcdEngine, self).__init__(config, auth)

    @abstractmethod
    def _latest_revision(self, key: str) -> int:
        """
        :param: key used for the server request
        :return: latest revision of the notification server.
        """
        pass

    @abstractmethod
    def _lease(self, ttl) -> str:
        """
        This method requests a Lease for the TTL specified
        :param ttl: Lease TTL
        :return: lease id
        """
        pass

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

        def trigger_callback(notifications):
            for notification in notifications:
                v = notification["value"].decode()
                k = notification["key"]
                logger.debug(f"Notification received for key {k}")
                try:
                    callback(k, v)
                except Exception as err:
                    logger.error(f"Error with notification trigger: {err}")
                    logger.debug("", exc_info=True)

        try:
            # initialise the revisions
            final_rev = None

            # check start date
            if from_date is None:  # no start date defined
                if self.catchup is None:
                    raise EngineException("catchup not defined for notification engine")
                if self.catchup:  # we start from the saved one
                    saved_rev = self._last_saved_revision()
                    if saved_rev != -1:
                        logger.info("Starting from last notification received")
                        next_rev = saved_rev
                    else:  # if it's the first time we start from now
                        next_rev = self._latest_revision(key) + 1
                else:  # delete the saved state
                    self._delete_saved_revision()
                    # we start from now
                    next_rev = self._latest_revision(key) + 1

            else:  # start date defined
                logger.info("Searching for past notifications...")
                next_rev, final_rev = self._from_to_revisions(key, from_date=from_date, to_date=to_date)
                if next_rev == -1 and final_rev == -1:
                    logger.warning("No history available in the time period selected")
                    channel.put(True)
                    return
                elif next_rev:
                    logger.info("Search completed, retrieving...")
                else:
                    logger.error("Error in one of the listening process")
                    channel.put(False)
                    return

            # check end date
            if to_date:  # end date defined, retrieve only past notifications
                if final_rev:
                    kvs = self.pull(key, min_rev=next_rev, max_rev=final_rev)
                    # remove the status from the result
                    for kv in kvs:
                        if kv["key"] == key:  # this is the status
                            kvs.remove(kv)
                            break
                    # trigger the callback
                    trigger_callback(kvs)
                # de-register this pooling thread as we have finished
                self.stop(key)
                logger.info("Search and retrieval completed")
                if len(self._listeners) == 0:  # this is the last pooling thread
                    # terminate the main execution
                    channel.put(True)
                    return

            else:  # no end date defined, start the polling for new notifications
                while key in self._listeners:  # this is the stop condition
                    # retrieve any change since the last revision
                    kvs = self.pull(key, min_rev=next_rev)
                    # remove the status from the result
                    for kv in kvs:
                        if kv["key"] == key:  # this is the status
                            kvs.remove(kv)
                            break
                    if len(kvs) > 0:
                        # update the current revision
                        for kv in kvs:
                            if next_rev < kv["mod_rev"] + 1:
                                next_rev = kv["mod_rev"] + 1
                        # save current rev
                        self._save_last_revision(next_rev)
                        # trigger the callback
                        trigger_callback(kvs)
                    # wait the polling interval before trying again
                    time.sleep(self._polling_interval)

        except Exception as e:
            logger.error(f"Error while listening to key {key}: {e}")
            logger.debug("", exc_info=True)
            channel.put(False)

    def _last_saved_revision(self) -> int:
        """
        This method is used to read the last revision saved to file in the home folder
        :return: last revision or -1 if no revision could be read
        """
        # build the path where the last revision is saved
        full_home_path = os.path.expanduser(HOME_FOLDER)
        full_rev_path = os.path.join(full_home_path, LOCAL_STATE_FOLDER, LAST_REVISION_FILE)
        if os.path.exists(full_rev_path):
            try:
                with open(full_rev_path, "r") as f:
                    # acquire a file lock to avoid concurrency among processes
                    fcntl.lockf(f, fcntl.LOCK_SH)
                    rev_dict = json.loads(f.read())
                    last_rev = rev_dict["last_revision"]
                    # release file lock
                    fcntl.lockf(f, fcntl.LOCK_UN)
                logger.debug(f"Last revision saved is {last_rev}")
                return last_rev
            except Exception as e:
                logger.warning(f"Error occurred while reading the last revision saved: {e}")
                logger.debug("", exc_info=True)

        # default return
        return -1

    def _delete_saved_revision(self):
        """
        This method is used to delete the file where the last revision is saved
        """
        # build the path where the last revision is saved
        full_home_path = os.path.expanduser(HOME_FOLDER)
        full_state_path = os.path.join(full_home_path, LOCAL_STATE_FOLDER)
        full_rev_path = os.path.join(full_state_path, LAST_REVISION_FILE)

        with self._state_lock:  # multiple listing threads could access this simultaneously
            if os.path.exists(full_rev_path):
                try:
                    # delete the file
                    os.remove(full_rev_path)
                    logger.debug("Last revision file has been successfully deleted")
                except Exception:
                    logger.warning(f"Deleting the last revision file has failed: {full_rev_path}")
                    logger.debug("", exc_info=True)
                    return False

    def _save_last_revision(self, rev: int) -> bool:
        """
        This method is used to save to file the revision passed as the last revision pulled
        :param rev: last revision to save
        :return: True if saved otherwise False
        """
        if rev is not None:
            rev_dict = {
                "last_revision": rev,
                "date_time": datetime.utcnow().strftime(DATE_FORMAT),
                "server_host": self.host,
                "server_port": self.port,
            }
            # build the path where the last revision will be saved
            full_home_path = os.path.expanduser(HOME_FOLDER)
            full_state_path = os.path.join(full_home_path, LOCAL_STATE_FOLDER)

            with self._state_lock:  # multiple listing threads could access this simultaneously
                if not os.path.exists(full_state_path):
                    try:
                        os.makedirs(full_state_path, exist_ok=True)
                    except OSError:
                        logger.warning(f"Cannot create the directory for the last revision: {full_state_path}")
                        logger.debug("", exc_info=True)
                        return False
                try:
                    full_rev_path = os.path.join(full_state_path, LAST_REVISION_FILE)
                    with open(full_rev_path, "w") as f:
                        # acquire a file lock to avoid concurrency among processes
                        fcntl.lockf(f, fcntl.LOCK_EX)
                        # write the revision in the file
                        json.dump(rev_dict, f)
                        # release file lock
                        fcntl.lockf(f, fcntl.LOCK_UN)
                    logger.debug(f"Last revision pulled {rev} has been successfully saved")
                except Exception:
                    logger.warning(f"Saving of the last revision has failed: {full_state_path}")
                    logger.debug("", exc_info=True)
                    return False
        return True

    def _retrieve_status_history(self, key, rev=None) -> Tuple[int, Any, int, Any]:
        """
        :param key: key for which to return the status
        :param rev: revision of the status requested
        :return: a tuple: status's revision, status's date, previous status's revision,
        revision of the last status of the previous day
        """
        try:
            kvs = self.pull(key=key, prefix=False, rev=rev)
        # in case of retrieving a compacted revision we will get a 400 error with a proper reason
        except EngineHistoryNotAvailableError:
            logger.debug(f"Revision {rev} too old for current history")
            return rev, None, rev, None  # return in a way that is clear that we arrived at the end of the history

        # look inside what returned
        if len(kvs) == 0:
            return -1, None, -1, None
        assert len(kvs) == 1, f"Error in finding revision for {key}, more then one kv found or none"
        s_rev = kvs[0]["mod_rev"]
        s = json.loads(kvs[0]["value"].decode())
        if "prev_rev" in s:
            s_prev_rev = s["prev_rev"]
        else:
            s_prev_rev = -1  # this means that this is the first revision of the status. We cannot go further back
        s_date = datetime.strptime(s["date_time"], DATE_FORMAT)
        s_last_prev_day_rev = s.get("last_prev_day_rev")
        return s_rev, s_date, s_prev_rev, s_last_prev_day_rev

    def _from_to_revisions(self, key: str, from_date: datetime, to_date: datetime = None) -> Tuple[Any, Any]:
        """
        This methods search for revisions corresponding to the interval (from_date, to_date)
        :param key:
        :param from_date:
        :param to_date:
        :return: a tuple: revision just after from_date, revision just before to_date
        """
        logger.debug(f"Querying notification server to find historic revisions for key {key}")

        # first retrieve the current status
        to_rev = None
        status_rev, status_date, status_prev_rev, status_last_prev_day_rev = self._retrieve_status_history(key)

        # check all limit cases first
        # limit case - check if there is no status
        if status_rev == -1:
            logger.debug("No status available")
            return None, None
        # limit case - check if this revision is before from_date and to_date
        if status_date <= from_date:
            # return the revisions as this is the last point
            from_rev = status_rev + 1
            to_rev = from_rev
            return from_rev, to_rev
        else:
            # limit case - check if this revision is after from_date and to_date and it's the only point
            if status_prev_rev == -1 and to_date and status_date >= to_date:
                # return the revisions as this is the only point
                from_rev = status_rev - 1
                to_rev = from_rev
                return from_rev, to_rev
            # limit case - check if this revision is inside from_date and to_date and it's the only point
            elif status_prev_rev == -1:
                # return the revisions as this is the only point
                from_rev = status_rev
                to_rev = from_rev
                return from_rev, to_rev

        # if we have not returned yet search for older status revisions

        # check if we are inside the interval
        if to_date and status_date < to_date:
            to_rev = status_rev

        # start navigating the history
        while status_date > from_date and status_prev_rev != -1:
            if status_date.date() == from_date.date():  # same day
                # go back one revision
                status_rev, status_date, status_prev_rev, status_last_prev_day_rev = self._retrieve_status_history(
                    key, status_prev_rev
                )
            elif status_last_prev_day_rev:
                # go back to the revision of the last of the previous day -> we skip a day
                status_rev, status_date, status_prev_rev, status_last_prev_day_rev = self._retrieve_status_history(
                    key, status_last_prev_day_rev
                )
            elif status_last_prev_day_rev is None:  # it is the last point of history
                logger.warning("Reached the end of history available")
                break

            if status_date is None:  # if we reached a compacted revision status_date will be None,
                logger.warning("Reached the end of history available")
                break
            # check if this revision satisfies to_date and has not been previously saved
            if to_date and status_date < to_date and to_rev is None:
                to_rev = status_rev

        if status_date is None or status_date <= from_date:  # we exit the loop because we went out of the interval
            # save the revision in from_rev but increment it so we stay just inside the interval
            from_rev = status_rev + 1
        else:  # we exit because is the last point but we are inside the interval
            from_rev = status_rev
        if to_date and to_rev is None:  # this means there are no point inside the interval - limit case
            logger.debug("No keys found")
            return -1, -1

        return from_rev, to_rev

    def _incr_last_byte(self, path: str) -> bytes:
        """
        This function determines the end of the range required for a range call with the etcd3 API
        By incrementing the last byte of the input path, it allows to make a range call describing the input
        path as a branch rather than a leaf path.

        :param path: the path representing the start of the range
        :return: the path representing the end of the range
        """
        bytes_types = (bytes, bytearray)
        if not isinstance(path, bytes_types):
            if not isinstance(path, str):
                path = str(path)
            path = path.encode("utf-8")
        s = bytearray(path)
        # increment the last byte
        s[-1] = s[-1] + 1
        return bytes(s)
