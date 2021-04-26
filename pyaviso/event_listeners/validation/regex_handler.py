# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import re

from .type_handler import TypeHandler


class RegexHandler(TypeHandler):
    def __init__(self, key, regex, required=False):
        super(RegexHandler, self).__init__(key, required)
        self._regex = regex

    @property
    def regex(self) -> str:
        return self._regex

    def valid(self, value: any) -> bool:
        result = re.match(self.regex, value)
        if result is None:
            return False
        else:
            return True

    def canonise(self, value: any) -> str:
        return value
