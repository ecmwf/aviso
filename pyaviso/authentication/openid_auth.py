# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


class OpenidAuth:
    """
    OpenidAuth implements an OpenID authentication flow.

    It returns a Bearer header (using the shared secret from config.password) and adds
    an extra header "X-Auth-Type" with the value "openid".
    """

    def __init__(self, config):
        self.config = config

    def header(self):
        return {"Authorization": f"Bearer {self.config.password}", "X-Auth-Type": "openid"}
