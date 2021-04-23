# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import List

from .type_handler import TypeHandler


class IntHandler(TypeHandler):
    def __init__(self, key, required=False, canonic=None, range=None):
        super(IntHandler, self).__init__(key, required)
        self._canonic = canonic
        self._range = range

    @property
    def canonic(self) -> str:
        return self._canonic

    @property
    def range(self) -> List[int]:
        return self._range

    def valid(self, value: any) -> bool:
        try:
            value = int(value)
        except ValueError as e:
            raise ValueError(f"Key {self.key} has to be an integer", e)
        if self.range is not None:
            assert len(self.range) == 2, "Wrong schema structure, range can only have 2 elements"
            if value < self.range[0] or value > self.range[1]:
                raise ValueError(f"Value {value} for key {self.key} is outside the range defined")
        return True

    def canonise(self, value: any) -> str:
        value = int(value)
        if self.canonic is not None:
            return self.canonic.format(value)
        else:
            return str(value)
