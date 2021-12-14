# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod


class TypeHandler(ABC):
    def __init__(self, key, required=False):
        super(TypeHandler, self).__init__()
        self._key = key
        self._required = required

    @property
    def key(self) -> str:
        return self._key

    @property
    def required(self) -> bool:
        return self._required

    def process(self, value: any = None) -> str:
        if self.required and value is None:
            raise KeyError(f"{self.key} is a mandatory key")
        elif not self.required and value is None:
            return None
        else:
            # validate the key
            if self.valid(value):
                return self.canonise(value)
            else:
                raise ValueError(f"Value {value} is not valid for key {self.key}")

    @abstractmethod
    def valid(self, value: any) -> bool:
        pass

    @abstractmethod
    def canonise(self, value: any) -> str:
        pass
