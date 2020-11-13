# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import os

import requests

from . import logger
from .utils import encode_to_str_base64, decode_to_bytes, incr_last_byte

DATE_FORMAT = "%Y%m%d"


class Cleaner:

    def __init__(self, config):
        self.url = config["url"]
        self.req_timeout = config["req_timeout"]
        self.dest_path = config["dest_path"]
        self.diss_path = config["diss_path"]
        self.mars_path = config["mars_path"]
        self.retention_period = config["retention_period"]
        self.enabled = config["enabled"]

    def get_destinations(self, date):
        """
        :param date:
        :return: destinations associated to the date passed
        """
        logger.debug(f"Getting destinations for {date}")

        url = self.url + "/v3/kv/range"

        # build the key with the date
        date_s = date.strftime(DATE_FORMAT)
        key = os.path.join(self.dest_path, date_s)
        encoded_key = encode_to_str_base64(key)
        encoded_end_key = encode_to_str_base64(str(incr_last_byte(key), "utf-8"))
        body = {
            "key": encoded_key,
            "range_end": encoded_end_key,
            "keys_only": True
        }
        # make the call
        resp = requests.post(url, json=body, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Not able to request destinations for {date_s}, status {resp.status_code}, ' \
            f'{resp.reason}, {resp.content.decode()}'
        logger.debug(f"Query for destinations completed")
        resp_body = resp.json()

        # read the body and extract the destinations
        destinations = []
        if 'kvs' in resp_body:
            for kv in resp_body["kvs"]:
                k = decode_to_bytes(kv["key"]).decode()
                destinations.append(k.replace(key+"/", ""))

        logger.debug(f"Number of destinations retrieved: {len(destinations)}")
        return destinations

    def delete_destination_keys(self, date):
        """
        Delete the keys used to associate the destinations to the date passed
        :param date:
        :return: number of keys deleted
        """
        logger.debug(f"Deleting destinations for {date}")

        url = self.url + "/v3/kv/deleterange"

        # build the key with the date
        date_s = date.strftime(DATE_FORMAT)
        key = os.path.join(self.dest_path, date_s)
        encoded_key = encode_to_str_base64(key)
        encoded_end_key = encode_to_str_base64(str(incr_last_byte(key), "utf-8"))
        body = {
            "key": encoded_key,
            "range_end": encoded_end_key
        }
        # make the call
        resp = requests.post(url, json=body, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Not able to delete destinations for {date_s}, status {resp.status_code}, ' \
            f'{resp.reason}, {resp.content.decode()}'

        logger.debug(f"Deleting destinations completed")

        # check how many keys have been deleted
        resp_body = resp.json()
        if "deleted" in resp_body:
            return int(resp_body["deleted"])
        return 0

    def delete_keys(self, date, destination=None):
        """
        Delete all keys associated to the date passed, dissemination if destination!=None or MARS keys
        :param date:
        :param destination: if None MARS key will be deleted otherwise the dissemination keys associated to the
        destination passed
        :return: Number of keys deleted
        """
        if destination:
            logger.debug(f"Deleting {destination} keys for {date}")
        else:
            logger.debug(f"Deleting MARS keys for {date}")

        url = self.url + "/v3/kv/deleterange"

        # build the key with the date
        date_s = "date="+date.strftime(DATE_FORMAT)
        if destination:  # Dissemination keys
            key = os.path.join(self.diss_path, destination, date_s)
        else:  # MARS keys
            key = os.path.join(self.mars_path, date_s)
        encoded_key = encode_to_str_base64(key)
        encoded_end_key = encode_to_str_base64(str(incr_last_byte(key), "utf-8"))
        body = {
            "key": encoded_key,
            "range_end": encoded_end_key
        }
        # make the call
        resp = requests.post(url, json=body, timeout=self.req_timeout)
        assert resp.status_code == 200, f'Not able to delete keys for {date_s}, status {resp.status_code}, ' \
            f'{resp.reason}, {resp.content.decode()}'
        logger.debug(f"Deleting keys completed")

        # check how many keys have been deleted
        resp_body = resp.json()
        if "deleted" in resp_body:
            return int(resp_body["deleted"])
        return 0

    def run(self):
        """
        Execute the cleaner workflow:
         - determine the date to delete
         - delete all the dissemination keys for this date:
            - retrieve the destinations for the date
            - delete the dissemination key for each destination
            - delete the destinations keys
         - delete all the MARS keys for this date
        :return: True if successful
        """

        logger.info("Running cleaner...")

        # determine the retention period
        now = datetime.datetime.utcnow()
        retention_start_date = now - datetime.timedelta(days=self.retention_period)

        # Dissemination keys
        # retrieve destinations
        destinations = self.get_destinations(retention_start_date)

        # for each destination delete all the key that are for that day
        for dest in destinations:
            self.delete_keys(retention_start_date, dest)
        logger.info(f"Dissemination keys deleted for {retention_start_date}")

        # delete destination keys for that day
        self.delete_destination_keys(retention_start_date)
        logger.info(f"Destination keys deleted for {retention_start_date}")

        # MARS keys
        self.delete_keys(retention_start_date)
        logger.info(f"MARS keys deleted for {retention_start_date}")

        logger.info("Cleaner execution completed.")
        return True


