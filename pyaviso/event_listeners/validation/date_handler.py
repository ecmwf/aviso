# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime

from .type_handler import TypeHandler


class DateHandler(TypeHandler):
    def __init__(self, key, canonic, required=False):
        super(DateHandler, self).__init__(key, required)
        self._canonic = canonic

    @property
    def canonic(self) -> str:
        return self._canonic

    def valid(self, value: any) -> bool:
        try:
            self._d_datetime = datetime.datetime.strptime(str(value), self.canonic)
            return True
        except ValueError as e:
            raise ValueError("Date attribute is not complying with the format defined", e)

    def canonise(self, value: any) -> str:
        # strptime tolerates months or days with no leading zero, we need to format it again to be sure they are there
        return self._d_datetime.strftime(self.canonic)
