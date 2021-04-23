# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from ..user_config import UserConfig
from .etcd_auth import EtcdAuth


class EcmwfAuth(EtcdAuth):
    """
    This class set the authentication credentials for the ECMWF SSO authentication
    """

    def __init__(self, config: UserConfig):
        super(EcmwfAuth, self).__init__(config)
        self._password = config.password
        self._username = config.username

    def header(self):
        header = {"Authorization": f"EmailKey {self.username}:{self.password}"}
        return header
