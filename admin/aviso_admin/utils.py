# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import base64


def encode_to_str_base64(obj: any) -> str:
    """
    Method to translate the object passed in a field that could be accepted by etcd and the request library
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
    Method to translate what is coming back from the notification server.
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
