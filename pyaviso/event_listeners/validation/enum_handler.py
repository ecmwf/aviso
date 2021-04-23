# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import List

from .type_handler import TypeHandler


class EnumHandler(TypeHandler):
    def __init__(self, key, values: List[str], required=False, default=None):
        super(EnumHandler, self).__init__(key, required)
        self._valid_values = values
        self._default = default

    @property
    def valid_values(self) -> List[str]:
        return self._valid_values

    def valid(self, value: any) -> bool:
        if value == "" and self._default is not None:
            value = self._default
        # convert the value to the same type of the enums otherwise it will not be able to validate
        try:
            value = type(self.valid_values[0])(value)
        except ValueError as e:
            raise ValueError(f"Key {self.key} is not of a valid type", e)

        if value in self.valid_values:
            return True
        else:
            valid_values_str = ",".join(map(lambda x: str(x), self.valid_values))
            raise ValueError(f"Key {self.key} accepts only the following values: {valid_values_str}")

    def canonise(self, value: any) -> str:
        if value == "" and self._default is not None:
            value = self._default
        return value
