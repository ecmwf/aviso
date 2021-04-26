# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import List

from .enum_handler import EnumHandler


class TimeHandler(EnumHandler):
    def __init__(self, key, values: List[str], canonic, required=False):
        super(TimeHandler, self).__init__(key, values, required)
        self._canonic = canonic

    @property
    def canonic(self) -> str:
        return self._canonic

    def canonise(self, value: any) -> str:
        return self.canonic.format(value)
