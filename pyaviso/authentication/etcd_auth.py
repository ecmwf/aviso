# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from .. import logger
from ..user_config import UserConfig
from .auth import Auth


class EtcdAuth(Auth):
    """
    This class set the authentication credentials for the basic etcd authentication where username and password are
    needed and once authenticated only the token is needed.
    """

    def __init__(self, config: UserConfig):
        super(EtcdAuth, self).__init__()
        logger.debug("Setting password from key file")
        self._password = config.password
        self._username = config.username
        logger.debug(f"Username: {self.username}")
        self._token = None  # this will be set once authenticated

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    @property
    def token(self) -> str:
        return self._token

    @token.setter
    def token(self, token: str):
        self._token = token

    def header(self):
        header = {}
        if self.token:
            header["Authorization"] = self.token
        return header
