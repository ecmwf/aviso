# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

__all__ = ["engine", "engine_factory", "etcd_grpc_engine", "etcd_rest_engine", "file_based_engine", "EngineType"]

import importlib
from enum import Enum


class EngineType(Enum):
    """
    This Enum describes the various notification mechanism currently available. This identifies the type of server
    this client is connecting to.
    """

    ETCD_GRPC = ("etcd_grpc_engine", "EtcdGrpcEngine")
    ETCD_REST = ("etcd_rest_engine", "EtcdRestEngine")
    FILE_BASED = ("file_based_engine", "FileBasedEngine")

    def __str__(self):
        return self.name.lower()

    def get_class(self):
        module = importlib.import_module("pyaviso.engine." + self.value[0])
        return getattr(module, self.value[1])
