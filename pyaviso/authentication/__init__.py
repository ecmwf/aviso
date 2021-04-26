# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import importlib
from enum import Enum


class AuthType(Enum):
    """
    This Enum describes the various authentication currently available.
    """

    ECMWF = ("ecmwf_auth", "EcmwfAuth")
    ETCD = ("etcd_auth", "EtcdAuth")
    NONE = ("none_auth", "NoneAuth")

    def __str__(self):
        return self.name.lower()

    def get_class(self):
        module = importlib.import_module("pyaviso.authentication." + self.value[0])
        return getattr(module, self.value[1])
