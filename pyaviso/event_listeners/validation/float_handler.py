# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from .type_handler import TypeHandler


class FloatHandler(TypeHandler):
    def __init__(self, key, required=False, canonic=None):
        super(FloatHandler, self).__init__(key, required)
        self._canonic = canonic

    @property
    def canonic(self) -> str:
        return self._canonic

    def valid(self, value: any) -> bool:
        try:
            value = float(value)
        except ValueError as e:
            raise ValueError(f"Key {self.key} has to be a float", e)
        return True

    def canonise(self, value: any) -> str:
        value = float(value)
        if self.canonic is not None:
            return self.canonic.format(value)
        else:
            return str(value)
