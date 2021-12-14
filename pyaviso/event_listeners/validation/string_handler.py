# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from .type_handler import TypeHandler


class StringHandler(TypeHandler):
    def __init__(self, key, required=False, canonic=None):
        super(StringHandler, self).__init__(key, required)
        self._canonic = canonic

    @property
    def canonic(self) -> str:
        return self._canonic

    def valid(self, value: any) -> bool:
        return True

    def canonise(self, value: any) -> str:
        value_str = str(value)
        if self.canonic is not None:
            if self.canonic == "lower":
                return value_str.lower()
            elif self.canonic == "upper":
                return value_str.upper()
            else:
                raise AttributeError(f"Case {self.canonic} not recognised")
        else:
            return value_str
