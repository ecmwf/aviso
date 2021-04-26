# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Dict, List

import grpc
from etcd3 import Etcd3Client, etcdrpc

from .. import logger
from ..authentication.auth import Auth
from ..authentication.etcd_auth import EtcdAuth
from ..custom_exceptions import EngineException, EngineHistoryNotAvailableError
from ..user_config import EngineConfig
from .etcd_engine import MAX_KV_RETURNED, EtcdEngine


class EtcdGrpcEngine(EtcdEngine):
    """
    This class is a specialisation of the Engine class, able to connect to a etcd3 server directly via the gRPC
    interface. This class is relying on the pythonEtcd3 python module for implementing the gRPC protocol.
    """

    def __init__(self, config: EngineConfig, auth: Auth):
        super(EtcdGrpcEngine, self).__init__(config, auth)
        self._initialise_server()
        self._listening_list = []
        # set base url
        self._base_url = f"http://{self._host}:{self._port}/v3/"

    def _initialise_server(self):
        if type(self.auth) == EtcdAuth:
            self._server = Etcd3Client(
                self.host, self.port, user=self.auth.username, password=self.auth.password, timeout=self.timeout
            )
        else:
            self._server = Etcd3Client(self.host, self.port, timeout=self.timeout)

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

        # determine the range_end
        if prefix:
            range_end = self._incr_last_byte(key)
        else:
            range_end = None

        # call the get range on the ETCD_GRPC sever, order them newest first
        range_request = self._server._build_get_range_request(
            key=key, range_end=range_end, sort_order="descend", sort_target="key", keys_only=key_only
        )

        range_request.limit = MAX_KV_RETURNED
        if rev:
            range_request.revision = rev
        if min_rev:
            range_request.min_mod_revision = min_rev
        if max_rev:
            range_request.max_mod_revision = max_rev
        # make the call
        logger.debug(f"Pull request: {range_request}")
        try_again = True
        while try_again:
            try:
                try_again = False
                range_result = self._server.kvstub.Range(
                    range_request,
                    self._server.timeout,
                    credentials=self._server.call_credentials,
                    metadata=self._server.metadata,
                )
            except grpc._channel._InactiveRpcError as e:
                if e._state.code.name == "UNAUTHENTICATED":
                    # it seems that sometimes the token expires, so re-init the server and try again
                    try_again = True
                    logger.debug(f"Error {e}, trying again", exc_info=True)
                    self._initialise_server()
                elif (
                    e._state.code.name == "OUT_OF_RANGE" and "required revision has been compacted" in e._state.details
                ):
                    raise EngineHistoryNotAvailableError()
                else:
                    raise EngineException(e)
        logger.debug(f"Query for {key} completed")

        # parse the result to return just key-value pairs
        new_kvs: List[Dict[str, bytes]] = []
        logger.debug("Building key-value list")
        for kv in range_result.kvs:
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
        # determine the range_end
        if prefix:
            range_end = self._incr_last_byte(key)
        else:
            range_end = None

        # call the delete range on the ETCD_GRPC sever
        try_again = False
        del_request = self._server._build_delete_request(key=key, range_end=range_end, prev_kv=True)

        # make the call
        logger.debug(f"Deleting key range associated to key {key}")
        try_again = True
        while try_again:
            try:
                try_again = False
                del_result = self._server.kvstub.DeleteRange(
                    del_request,
                    self._server.timeout,
                    credentials=self._server.call_credentials,
                    metadata=self._server.metadata,
                )
            except grpc._channel._InactiveRpcError as e:
                if e._state.code.name == "UNAUTHENTICATED":
                    # it seems that sometimes the token expires, so re-init the server and try again
                    try_again = True
                    logger.debug(f"Error {e}, trying again", exc_info=True)
                    self._initialise_server()
                else:
                    raise e
        logger.debug(f"Delete request for key {key} completed")

        # parse the result to return just key-value pairs of what has been deleted
        del_kvs: List[Dict[str, bytes]] = []
        if hasattr(del_result, "prev_kvs"):
            logger.debug("Building key-value list")
            for kv in del_result.prev_kvs:
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
        logger.debug("Preparing the transaction statement")
        ops = []

        # check if we need to request a lease for the ttl
        if ttl:
            try:
                lease = self._lease(ttl)
            except EngineException:
                raise EngineException("Not able to push keys")

        # first delete the keys requested
        if ks_delete is not None and len(ks_delete) != 0:
            for kd in ks_delete:
                # every key is deleted with prefix=True
                range_end = self._incr_last_byte(kd)
                delete = self._server._build_delete_request(kd, range_end)
                request_op = etcdrpc.RequestOp(request_delete_range=delete)
                ops.append(request_op)

        # Prepare the transaction with a put operation for each KV pair
        for kv in kvs:
            k = kv["key"]
            v = kv["value"]
            put = self._server._build_put_request(k, v)
            if ttl:
                put.lease = lease
            request_op = etcdrpc.RequestOp(request_put=put)
            ops.append(request_op)

        transaction_request = etcdrpc.TxnRequest(success=ops)

        # commit transaction
        # logger.debug(f"Committing the transaction statement: {ops}")
        try_again = True
        while try_again:
            try:
                try_again = False
                txn_response = self._server.kvstub.Txn(
                    transaction_request,
                    self._server.timeout,
                    credentials=self._server.call_credentials,
                    metadata=self._server.metadata,
                )
            except grpc._channel._InactiveRpcError as e:
                if e._state.code.name == "UNAUTHENTICATED":
                    # it seems that sometimes the token expires, so re-init the server and try again
                    try_again = True
                    logger.debug(f"Error {e}, trying again", exc_info=True)
                    self._initialise_server()
                else:
                    raise e
        assert txn_response.succeeded, "Not able to execute the transaction"
        logger.debug("Transaction completed")
        # read the header
        if hasattr(txn_response, "header"):
            h = txn_response.header
            rev = int(h.revision)
            logger.debug(f"New server revision {rev}")

        return True

    def lock(self, lock_id: str):
        """
        Acquire a lock identified by the id
        :param lock_id: Lock id
        :return: Lock if acquired otherwise exception if not acquired by the time the timeout expires
        """
        logger.debug("Calling lock...")
        try_again = True
        while try_again:
            try:
                try_again = False
                lock = self._server.lock(lock_id)
                res = lock.acquire(timeout=10)
            except grpc._channel._InactiveRpcError as e:
                if e._state.code.name == "UNAUTHENTICATED":
                    # it seems that sometimes the token expires, so re-init the server and try again
                    try_again = True
                    logger.debug(f"Error {e}, trying again", exc_info=True)
                    self._initialise_server()
                else:
                    raise e
            except Exception as e:
                raise EngineException(f"Not able to acquire lock {id}, {e}")
        if res:
            logger.debug(f"Lock {id} acquired")
            return lock
        else:
            raise EngineException(f"Not able to acquire lock {id}, timeout expired")

    def unlock(self, lock: any):
        """
        Acquire a lock identified by the id
        :param lock: Lock to release
        :return: True once released
        """
        logger.debug("Calling unlock...")
        try_again = True
        while try_again:
            try:
                try_again = False
                res = lock.release()
            except grpc._channel._InactiveRpcError as e:
                if e._state.code.name == "UNAUTHENTICATED":
                    # it seems that sometimes the token expires, so re-init the server and try again
                    try_again = True
                    logger.debug(f"Error {e}, trying again", exc_info=True)
                    self._initialise_server()
                else:
                    raise e

        logger.debug("Lock released")
        return res

    def _latest_revision(self, key: str) -> int:
        """
        :return: latest revision of the notification server.
        """
        logger.debug("Querying notification server for latest revision")

        # we need just the header back from the server
        range_request = self._server._build_get_range_request(key=key, keys_only=True)

        # make the call
        try_again = True
        while try_again:
            try:
                try_again = False
                range_result = self._server.kvstub.Range(
                    range_request,
                    self._server.timeout,
                    credentials=self._server.call_credentials,
                    metadata=self._server.metadata,
                )
            except grpc._channel._InactiveRpcError as e:
                if e._state.code.name == "UNAUTHENTICATED":
                    # it seems that sometimes the token expires, so re-init the server and try again
                    try_again = True
                    logger.debug(f"Error {e}, trying again", exc_info=True)
                    self._initialise_server()
                else:
                    raise e
        logger.debug("Query for latest revision completed")

        # read the header
        if hasattr(range_result, "header"):
            h = range_result.header
            rev = int(h.revision)
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

        # create request
        lease_grant_request = etcdrpc.LeaseGrantRequest(TTL=ttl, ID=None)

        # make the call
        try_again = True
        while try_again:
            try:
                try_again = False
                res = self._server.leasestub.LeaseGrant(
                    lease_grant_request,
                    self._server.timeout,
                    credentials=self._server.call_credentials,
                    metadata=self._server.metadata,
                )
            except grpc._channel._InactiveRpcError as e:
                if e._state.code.name == "UNAUTHENTICATED":
                    # it seems that sometimes the token expires, so re-init the server and try again
                    try_again = True
                    logger.debug(f"Error {e}, trying again", exc_info=True)
                    self._initialise_server()
                else:
                    raise e
        if res:
            logger.debug(f"Lease {res.ID} acquired")
            return res.ID
        else:
            raise EngineException("Not able to acquire lease")

    def _parse_raw_kv(self, kv, key_only: bool = False) -> Dict[str, any]:
        """
        Internal method to translate the kv pair coming from the etcd server into a dictionary that fits better this
        application
        :param kv: raw kv pair from the etcd server
        :param key_only:
        :return: translated kv pair as dictionary
        """
        new_kv = {}
        if not key_only:
            new_kv["value"] = kv.value  # leave it as binary
        new_kv["key"] = kv.key.decode()
        new_kv["version"] = int(kv.version)
        new_kv["create_rev"] = int(kv.create_revision)
        new_kv["mod_rev"] = int(kv.mod_revision)
        return new_kv
