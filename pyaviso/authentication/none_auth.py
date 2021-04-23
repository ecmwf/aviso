# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from ..user_config import UserConfig
from .auth import Auth


class NoneAuth(Auth):
    """
    This class disables any authentication
    """

    def __init__(self, config: UserConfig):
        super(NoneAuth, self).__init__()

    def header(self):
        return {}
