# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import base64

class PlainAuth:
    """
    PlainAuth implements Basic authentication.
    """
    def __init__(self, config):
        self.config = config

    def header(self):
        credentials = f"{self.config.username}:{self.config.password}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded}",
            "X-Auth-Type": "plain"
        }
