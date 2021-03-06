# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


class InvalidInputError(Exception):
    pass


class ForbiddenDestinationException(Exception):
    pass


class TokenNotValidException(Exception):
    pass


class InternalSystemError(Exception):
    pass


class UserNotFoundException(Exception):
    pass


class AuthenticationUnavailableException(Exception):
    pass


class AuthorisationUnavailableException(Exception):
    pass


class BackendUnavailableException(Exception):
    pass
