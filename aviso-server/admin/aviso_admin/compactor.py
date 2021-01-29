# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import json

import requests

from . import logger
from .custom_exceptions import ServerException
from .utils import encode_to_str_base64, decode_to_bytes

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class Compactor:

    def __init__(self, config):
        self.url = config["url"]
        self.req_timeout = config["req_timeout"]
        self.history_path = config["history_path"]
        self.retention_period = config["retention_period"]
        self.enabled = config["enabled"]

    def get_current_server_rev(self):
        """
        :return: the latest revision on the server
        """
        logger.debug(f"Getting current server revision")

        url = self.url + "/v3/kv/range"

        # we need just the header back from the server
        encoded_key = encode_to_str_base64("/")
        body = {
            "key": encoded_key,
            "keys_only": True
        }
        # make the call
        resp = requests.post(url, json=body, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Not able to request current revision, status {resp.status_code}, ' \
            f'{resp.reason}, {resp.content.decode()}'
        logger.debug(f"Query for current revision completed")
        resp_body = resp.json()
        # read the header
        if 'header' in resp_body:
            h = resp_body["header"]
            rev = int(h["revision"])
        else:
            raise ServerException("Error in reading server revision. Response does not contain header")
        logger.debug(f"Current server revision {rev}")
        return rev

    def get_history(self):
        """
        :return: the history saved on the server
        """
        logger.debug(f"Getting the history...")

        url = self.url + "/v3/kv/range"

        body = {
            "key": encode_to_str_base64(self.history_path),
        }
        # make the call
        resp = requests.post(url, json=body, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Not able to request history, status {resp.status_code}, ' \
            f'{resp.reason}, {resp.content.decode()}'
        logger.debug(f"Query for current history completed")

        # decode the value and load it as yaml
        resp_body = resp.json()
        if 'kvs' in resp_body:
            assert len(resp_body["kvs"]) == 1, f"Retrieved more than a key on history path, {resp_body['kvs']}"
            kv = resp_body["kvs"][0]
            history_s = decode_to_bytes(kv["value"]).decode()
            history = json.loads(history_s)
            logger.debug(f"Current history retrieved {history}")
        else:
            logger.debug("No history found")
            history = []
        return history

    def save_history(self, history):
        """
        Save the history to the server
        :param history:
        :return: True if successful
        """
        logger.debug(f"Saving the history...")

        url = self.url + "/v3/kv/put"
        history_s = json.dumps(history)

        body = {
            "key": encode_to_str_base64(self.history_path),
            "value": encode_to_str_base64(history_s)
        }
        # make the call
        resp = requests.post(url, json=body, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Not able to save history, status {resp.status_code}, ' \
            f'{resp.reason}, {resp.content.decode()}'
        logger.debug(f"Saving history completed")

        # check the save was successful
        resp_body = resp.json()
        # read the header
        if 'header' in resp_body:
            h = resp_body["header"]
            rev = int(h["revision"])
            logger.debug(f"New server revision {rev}")
        return True

    def save_rev(self, rev: int, date: datetime):
        """
        Save the revision passed to the history stored
        :param rev: revision to save
        :param date: date associated to this revision, to save with
        :return: True if successful
        """
        logger.debug(f"Saving revision {rev} for date {date}...")

        # get the history from the store
        history = self.get_history()

        # new entry to add to history
        hist_e = {"revision": rev, "timestamp": date.strftime(DATE_FORMAT)}
        history.append(hist_e)

        # save the history back to the store
        self.save_history(history)
        logger.debug(f"Revision {rev} has been successfully saved")
        return True

    def clean_history(self, ret_per_start):
        """
        Clean the history from revisions that are outside of the retention period
        :param ret_per_start: start of the retention period
        :return: the newest revision among the one outside the retention period
        """
        logger.debug(f"Looking for revisions older than {ret_per_start}")

        # read from the history all the revisions older than date
        history = self.get_history()
        old_revs = list(filter(
            lambda he: datetime.datetime.strptime(he.get("timestamp"), DATE_FORMAT) <= ret_per_start, history))

        # remove all the old revisions and save the history
        new_hist = [h for h in history if h not in old_revs]
        self.save_history(new_hist)

        # find the newest among the old revisions
        new_old_rev = None
        for old_rev in old_revs:
            if new_old_rev:
                if new_old_rev["timestamp"] < old_rev["timestamp"]:
                    new_old_rev = old_rev
            else:
                new_old_rev = old_rev

        logger.debug(f"The newest revision older than {ret_per_start} found is {new_old_rev}")

        # return only the revision
        if new_old_rev:
            new_old_rev = new_old_rev["revision"]
        return new_old_rev

    def compact(self, rev):
        """
        Compact the server to the revision passed
        :param rev: revision to compact
        :return: True if successful
        """
        logger.debug(f"Compacting server to revision {rev}...")

        url = self.url + "/v3/kv/compaction"

        body = {
            "revision": rev,
            "physical": True
        }
        # make the call
        resp = requests.post(url, json=body, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Not able to compact revision {rev}, status {resp.status_code}, ' \
            f'{resp.reason}, {resp.content.decode()}'
        logger.debug(f"Compacting revision completed")

        # check the save was successful
        resp_body = resp.json()
        # read the header
        if 'header' in resp_body:
            h = resp_body["header"]
            rev = int(h["revision"])
            logger.debug(f"Compacted revision {rev}")
        return True

    def defrag(self):
        """
        Defragment the the store space for each member
        :return: True if successful
        """
        logger.debug(f"Defragmenting server ...")

        url = self.url + "/v3/maintenance/defragment"

        # TBD make the call for each member
        resp = requests.post(url, data={}, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Error returned from defragmentation call on {url}, ' \
            f'status {resp.status_code}, {resp.reason}, {resp.content.decode()}'
        logger.debug(f"Defragmentation completed")
        return True

    def run(self, sec_ret_per=None):
        """
        Execute the compactor workflow:
         - retrieving and storing the latest revision
         - cleaning the history outside the retention period
         - performing compaction for old revision
        :param sec_ret_per: if True the retention period is interpreted in seconds rather than days, useful for testing
        :return: True if successful
        """
        logger.debug("Running compactor...")

        # check the current server revision
        curr_rev = self.get_current_server_rev()

        now = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        # save the rev to file with now as date
        self.save_rev(curr_rev, now)

        logger.debug(f"Revision {curr_rev} saved to history at date {now}")

        # move the retention period
        if sec_ret_per:  # this is used for testing
            retention_start_date = now - datetime.timedelta(seconds=self.retention_period)
        else:
            retention_start_date = now - datetime.timedelta(days=self.retention_period)
        # remove all the revision that are no longer in the retention period
        old_rev = self.clean_history(retention_start_date)

        if old_rev:
            # compact revision
            self.compact(old_rev)
            logger.info(f"Server compacted at revision {old_rev}")

        logger.debug("Compactor execution completed.")
        return True
