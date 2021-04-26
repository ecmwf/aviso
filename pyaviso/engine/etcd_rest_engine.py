# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import base64
import http.client
import logging
import time
from typing import Dict, List

import requests

from .. import logger
from ..authentication.auth import Auth
from ..authentication.etcd_auth import EtcdAuth
from ..custom_exceptions import EngineException, EngineHistoryNotAvailableError
from ..user_config import EngineConfig
from .etcd_engine import MAX_KV_RETURNED, EtcdEngine


class EtcdRestEngine(EtcdEngine):
    """
    This class is a specialisation of the Engine class, able to connect to a etcd3 server via the gRPC gateway by
    relying on the standard REST requests library.
    """

    def __init__(self, config: EngineConfig, auth: Auth):
        super(EtcdRestEngine, self).__init__(config, auth)
        # set base url
        if self.https:
            self._base_url = f"https://{self._host}:{self._port}/v3/"
        else:
            self._base_url = f"http://{self._host}:{self._port}/v3/"

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
        :param key_only: if True no values are returned
        :param rev: revision to pull
        :param prefix: if true the function will retrieve all the KV pairs starting with the key passed
        :param min_rev: if provided it filters for only KV pairs with mod_revision >= to min_rev
        :param max_rev: if provided it filters for only KV pairs with mod_revision <= to max_rev
        :return: List of key-value pairs formatted as dictionary
        """
        logger.debug(f"Calling pull for {key}...")

        url = self._base_url + "kv/range"

        # determine the range_end
        if prefix:
            range_end = self._encode_to_str_base64(str(self._incr_last_byte(key), "utf-8"))
        else:
            range_end = None

        # first authenticate and use the token for the header
        self._authenticate()

        # encode key
        encoded_key = self._encode_to_str_base64(key)

        # create the body for the get range on the etcd sever, order them newest first
        body = {
            "key": encoded_key,
            "range_end": range_end,
            "limit": MAX_KV_RETURNED,
            "sort_order": "DESCEND",
            "sort_target": "KEY",
            "keys_only": key_only,
            "revision": rev,
            "min_mod_revision": min_rev,
            "max_mod_revision": max_rev,
        }
        # make the call
        logger.debug(f"Pull request: {body}")

        # start an infinite loop of request if the server side is unreachable
        while True:
            try:
                resp = requests.post(url, json=body, headers=self.auth.header(), timeout=self.timeout)
                resp.raise_for_status()
            except requests.exceptions.HTTPError as err:
                if resp.status_code == 408 or (resp.status_code >= 500 and resp.status_code < 600):
                    logger.warning(f"Unable to connect to {url}, trying again in {self.automatic_retry_delay}s...")
                    logger.debug(f"Not able to pull key {key}, {str(err)}, trying again...")
                    time.sleep(self.automatic_retry_delay)
                    continue
                elif resp.status_code == 400 and (
                    "History not available" in resp.content.decode()
                    or "required revision has been compacted" in resp.content.decode()
                ):
                    raise EngineHistoryNotAvailableError()
                else:
                    raise EngineException(f"Not able to pull key {key}, {str(err)}")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
                logger.warning(f"Unable to connect to {url}, trying again in {self.automatic_retry_delay}s...")
                logger.debug(f"Not able to pull key {key}, {str(err)}, trying again...")
                time.sleep(self.automatic_retry_delay)
                continue
            except Exception as e:
                logger.exception(e)
                raise EngineException(
                    f"Not able to pull key {key}, status {resp.status_code}, {resp.reason}, " f"{resp.content.decode()}"
                )

            # we got a good responce, exit from the loop
            break

        logger.debug(f"Query for {key} completed")

        # parse the result to return just key-value pairs
        new_kvs: List[Dict[str, bytes]] = []
        resp_body = resp.json()
        if "kvs" in resp_body:
            logger.debug("Building key-value list")
            for kv in resp_body["kvs"]:
                new_kv = self._parse_raw_kv(kv, key_only)
                new_kvs.append(new_kv)
                logger.debug(f"Key: {new_kv['key']} pulled successfully")

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

        url = self._base_url + "kv/deleterange"

        # determine the range_end
        if prefix:
            range_end = self._encode_to_str_base64(str(self._incr_last_byte(key), "utf-8"))
        else:
            range_end = None

        # first authenticate and use the token for the header
        self._authenticate()

        # encode key
        encoded_key = self._encode_to_str_base64(key)

        # create the body for the delete range
        body = {"key": encoded_key, "range_end": range_end, "prev_kv": True}
        # make the call
        logger.debug(f"Deleting key range associated to key {key}")
        try:
            resp = requests.post(url, json=body, headers=self.auth.header(), timeout=self.timeout)
            resp.raise_for_status()
        except Exception as err:
            raise EngineException(f"Not able to delete key {key}, {str(err)}")

        logger.debug(f"Delete request for key {key} completed")

        # parse the result to return just key-value pairs of what has been deleted
        del_kvs: List[Dict[str, bytes]] = []
        resp_body = resp.json()
        if "prev_kvs" in resp_body:
            logger.debug("Building key-value list")
            for kv in resp_body["prev_kvs"]:
                new_kv = self._parse_raw_kv(kv)
                del_kvs.append(new_kv)
                logger.debug(f"Key: {new_kv['key']} deleted successfully")

        return del_kvs

    def push(self, kvs: List[Dict[str, any]], ks_delete: List[str] = None, ttl: int = None) -> bool:
        """
        Method to submit a list of key-value pairs and delete a list of keys from the server as a single transaction
        :param kvs: List of KV pair
        :param ks_delete: List of keys to delete before the push of the new ones. Note that each key is read as a folder
        :param ttl: time to leave of the keys pushed, once expired the keys will be deleted
        :return: True if successful
        """
        logger.debug("Calling push...")
        url = self._base_url + "kv/txn"

        # first authenticate and use the token for the header
        self._authenticate()

        # check if we need to request a lease for the ttl
        if ttl:
            lease = self._lease(ttl)

        logger.debug("Preparing the transaction statement")
        ops = []
        # first delete the keys requested
        if ks_delete is not None and len(ks_delete) != 0:
            for kd in ks_delete:
                # every key is deleted with prefix=True
                range_end = self._encode_to_str_base64(str(self._incr_last_byte(kd), "utf-8"))
                k = self._encode_to_str_base64(kd)
                delete = {"requestDeleteRange": {"key": k, "range_end": range_end}}
                ops.append(delete)

        # Prepare the transaction with a put operation for each KV pair
        for kv in kvs:
            k = self._encode_to_str_base64(kv["key"])
            v = self._encode_to_str_base64(kv["value"])
            put = {"requestPut": {"key": k, "value": v}}
            if ttl:
                put["requestPut"]["lease"] = lease
            ops.append(put)

        body = {"success": ops}
        # commit transaction
        # logger.debug(f"Committing the transaction statement: {body}")
        try:
            resp = requests.post(url, json=body, headers=self.auth.header(), timeout=self.timeout)
            resp.raise_for_status()
        except Exception as err:
            raise EngineException(f"Not able to execute the transaction, {str(err)}")

        logger.debug("Transaction completed")
        resp_body = resp.json()
        # read the header
        if "header" in resp_body:
            h = resp_body["header"]
            rev = int(h["revision"])
            logger.debug(f"New server revision {rev}")

        return True

    def _authenticate(self) -> bool:
        """
        This method authenticates  the user and set the internal token, this is only done for Etcd authentication
        :return: True if successfully authenticated
        """
        if type(self.auth) == EtcdAuth:
            logger.debug(f"Authenticating user {self.auth.username}...")

            url = self._base_url + "auth/authenticate"
            body = {"name": self.auth.username, "password": self.auth.password}
            try:
                resp = requests.post(url, json=body, headers=self.auth.header(), timeout=self.timeout)
                resp.raise_for_status()
            except Exception as err:
                raise EngineException(f"Not able to authenticate {self.auth.username}, {str(err)}")
            assert resp.json().get("token") is not None, "No token found in authentication response"
            self.auth.token = resp.json()["token"]

            logger.debug(f"User {self.auth.username} successfully authenticated")

        return True

    def _latest_revision(self, key: str) -> int:
        """
        :param: key used for the server request
        :return: latest revision of the notification server.
        """
        logger.debug("Querying notification server for latest revision")

        url = self._base_url + "kv/range"

        # first authenticate and use the token for the header
        self._authenticate()

        # we need just the header back from the server
        encoded_key = self._encode_to_str_base64(key)
        body = {"key": encoded_key, "keys_only": True}
        # make the call
        while True:
            try:
                resp = requests.post(url, json=body, headers=self.auth.header(), timeout=self.timeout)
                resp.raise_for_status()
            except requests.exceptions.HTTPError as err:
                if resp.status_code == 408 or (resp.status_code >= 500 and resp.status_code < 600):
                    logger.warning(f"Unable to connect to {url}, trying again in {self.automatic_retry_delay}s...")
                    logger.debug(f"Not able to request latest revision, {str(err)}, trying again...")
                    time.sleep(self.automatic_retry_delay)
                    continue
                else:
                    raise EngineException(f"Not able to request latest revision, {str(err)}")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
                logger.warning(f"Unable to connect to {url}, trying again in {self.automatic_retry_delay}s...")
                logger.debug(f"Not able to request latest revision, {str(err)}, trying again...")
                time.sleep(self.automatic_retry_delay)
                continue
            except Exception as e:
                logger.exception(e)
                raise EngineException(
                    f"Not able to request latest revision, status {resp.status_code}, {resp.reason}, "
                    f"{resp.content.decode()}"
                )

            # we got a good responce, exit from the loop
            break

        logger.debug("Query for latest revision completed")
        resp_body = resp.json()
        # read the header
        if "header" in resp_body:
            h = resp_body["header"]
            rev = int(h["revision"])
        else:
            raise EngineException("Error in reading server revision. Response does not contain header")
        logger.debug(f"Latest revision {rev}")
        return rev

    def _lease(self, ttl) -> str:
        """
        This method requests a Lease for the TTL specified
        :param ttl: Lease TTL
        :return: lease id
        """
        logger.debug(f"Calling lease for ttl {ttl}...")

        url = self._base_url + "lease/grant"

        # first authenticate and use the token for the header
        self._authenticate()

        # create the request body
        body = {"TTL": ttl, "ID": 0}

        # make the call
        try:
            resp = requests.post(url, json=body, headers=self.auth.header(), timeout=self.timeout)
            resp.raise_for_status()
        except Exception as err:
            raise EngineException(f"Not able to request a lease, {str(err)}")

        logger.debug("Lease request completed")
        resp_body = resp.json()
        if "ID" in resp_body:
            logger.debug(f"Lease {resp_body.get('ID')} acquired")
            return resp_body.get("ID")
        else:
            logger.error(f"Not able to read lease id from {resp_body}")
            raise EngineException("Not able to acquire lease")

    def _parse_raw_kv(self, kv: Dict[str, any], key_only: bool = False) -> Dict[str, any]:
        """
        Internal method to translate the kv pair coming from the etcd server into a dictionary that fits better this
        application
        :param kv: raw kv pair from the etcd server
        :param key_only:
        :return: translated kv pair as dictionary
        """
        new_kv = {}
        if not key_only:
            new_kv["value"] = self._decode_to_bytes(kv["value"])  # leave it as binary
        new_kv["key"] = self._decode_to_bytes(kv["key"]).decode()
        new_kv["version"] = int(kv["version"])
        new_kv["create_rev"] = int(kv["create_revision"])
        new_kv["mod_rev"] = int(kv["mod_revision"])
        return new_kv

    def _encode_to_str_base64(self, obj: any) -> str:
        """
        Internal method to translate the object passed in a field that could be accepted by etcd and the request library
        for the key or value. The request library accepts only strings encoded in base64 while etcd wants binaries for
        the key and value fields.
        :param obj:
        :return: a base64 string representation of the binary translation
        """
        if type(obj) is bytes:
            binary = obj
        elif type(obj) is str:
            binary = obj.encode()
        else:
            binary = str(obj).encode()

        return str(base64.b64encode(binary), "utf-8")

    def _decode_to_bytes(self, string: str) -> any:
        """
        Internal method to translate what is coming back from the notification server.
        The request library returns only string base64 encoded
        :param string:
        :return: the payload decoded from the base64 string representation
        """
        return base64.decodebytes(string.encode())


# Enable HTTPConnection debug logging to the logging framework
httpclient_logger = logging.getLogger("http.client")


def httpclient_log(*args):
    to_be_logged = " ".join(args)
    if len(to_be_logged) > 1000:
        to_be_logged = to_be_logged[:1000]
    httpclient_logger.log(logging.DEBUG, to_be_logged)


# mask the print() built-in in the http.client module to use logging instead
http.client.print = httpclient_log
http.client.HTTPConnection.debuglevel = 1
