# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import base64
from typing import Dict

import requests

old_etcd = "http://127.0.0.1:2379"
new_etcd = "http://127.0.0.1:2389"
from_revision = 1
to_revision = 9
MAX_KV_RETURNED = 10000


def push_kvpairs(etcd_repo, kvs):
    """
    Submit key-value pairs to the etcd_repo
    :param etcd_repo
    :param kvs
    :return: True if completed
    """

    print(f"Pushing key-value pairs to {etcd_repo} ...")

    url = etcd_repo + "/v3/kv/txn"

    ops = []
    # Prepare the transaction with a put operation for each KV pair
    for kv in kvs:
        k = encode_to_str_base64(kv["key"])
        v = encode_to_str_base64(kv["value"])
        put = {"requestPut": {"key": k, "value": v}}
        ops.append(put)

    body = {"success": ops}

    # commit transaction
    resp = requests.post(url, json=body)
    resp.raise_for_status()

    print("Operation completed")

    resp_body = resp.json()
    # read the header
    if "header" in resp_body:
        h = resp_body["header"]
        rev = int(h["revision"])
        print(f"New server revision {rev}")

    return True


def pull_kvpairs(etcd_repo, revision):
    """
    Retrieve key-value pairs newer than the revision number from the etcd_repo
    :param etcd_repo
    :param revision
    :return: kv pairs as dictionary
    """
    main_key = "f"

    old_etcd_url = etcd_repo + "/v3/kv/range"

    print(f"Getting key-value pairs to {etcd_repo} newer than {revision} ...")

    range_end = encode_to_str_base64(str(incr_last_byte(main_key), "utf-8"))

    # encode key
    encoded_key = encode_to_str_base64(main_key)

    # create the body for the get range on the etcd sever, order them newest first
    body = {
        "key": encoded_key,
        "range_end": range_end,
        "limit": MAX_KV_RETURNED,
        "sort_order": "DESCEND",
        "sort_target": "KEY",
        "revision": revision,
    }
    # make the call
    # print(f"Pull request: {body}")

    resp = requests.post(old_etcd_url, json=body)
    resp.raise_for_status()

    print("Retrival completed")

    # parse the result to return just key-value pairs
    new_kvs = []
    resp_body = resp.json()
    if "kvs" in resp_body:
        print("Building key-value list")
        for kv in resp_body["kvs"]:
            new_kv = parse_raw_kv(kv, False)
            new_kvs.append(new_kv)
            print(f"Key: {new_kv['key']} pulled successfully")

    print(f"{len(new_kvs)} keys found")
    return new_kvs


def parse_raw_kv(kv: Dict[str, any], key_only: bool = False) -> Dict[str, any]:
    """
    Internal method to translate the kv pair coming from the etcd server into a dictionary that fits better this
    application
    :param kv: raw kv pair from the etcd server
    :param key_only:
    :return: translated kv pair as dictionary
    """
    new_kv = {}
    if not key_only:
        new_kv["value"] = decode_to_bytes(kv["value"])  # leave it as binary
    new_kv["key"] = decode_to_bytes(kv["key"]).decode()
    new_kv["version"] = int(kv["version"])
    new_kv["create_rev"] = int(kv["create_revision"])
    new_kv["mod_rev"] = int(kv["mod_revision"])
    return new_kv


def encode_to_str_base64(obj: any) -> str:
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


def decode_to_bytes(string: str) -> any:
    """
    Internal method to translate what is coming back from the notification server.
    The request library returns only string base64 encoded
    :param string:
    :return: the payload decoded from the base64 string representation
    """
    return base64.decodebytes(string.encode())


def incr_last_byte(path: str) -> bytes:
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


################
# main worflow #
################

for rev in range(from_revision, to_revision + 1):

    # first get the key-value pairs from the old repo
    kvs = pull_kvpairs(old_etcd, rev)

    # send them to the new repo
    completed = push_kvpairs(new_etcd, kvs)
