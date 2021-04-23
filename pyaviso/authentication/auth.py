# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod

from ..user_config import UserConfig


class Auth(ABC):
    """
    Abstraction for the authentication mechanism used to talk with the aviso server.
    """

    @staticmethod
    def get_auth(config: UserConfig):
        """Static method return a instance of the authenticator"""
        return config.auth_type.get_class()(config)

    def __init__(self):
        super(Auth, self).__init__()

    @property
    def username(self):
        return None

    @property
    def password(self):
        return None

    @abstractmethod
    def header(self):
        """
        :return: the header to add to the REST calls to comply with the authentication protocol
        """
        pass
