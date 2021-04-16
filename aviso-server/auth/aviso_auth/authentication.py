# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import random
import time

import requests
from aviso_monitoring.collector.time_collector import TimeCollector
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthMetricType

from . import logger
from .custom_exceptions import TokenNotValidException, InternalSystemError, AuthenticationUnavailableException

MAX_N_TRIES = 25


class Authenticator:
    UNAUTHORISED_RESPONSE_HEADER = \
        {"WWW-Authenticate": "EmailKey realm='ecmwf',info='Authenticate with ECMWF API credentials <email>:<key>'"}

    def __init__(self, config, cache=None):
        self.url = config.authentication_server["url"]
        self.req_timeout = config.authentication_server["req_timeout"]

        # assign explicitly a decorator to provide cache for _token_to_username
        if cache:
            self._token_to_username = cache.memoize(timeout=config.authentication_server["cache_timeout"])(
                self._token_to_username_impl)
        else:
            self._token_to_username = self._token_to_username_impl

        # assign explicitly a decorator to monitor the authentication
        if config.authentication_server["monitor"]:
            self.timer = TimeCollector(config.monitoring, tlm_type=AvisoAuthMetricType.auth_resp_time.name, tlm_name="att")
            self.authenticate = self.timed_authenticate
        else:
            self.authenticate = self.authenticate_impl

    def timed_authenticate(self, request):
        """
        This method is an explicit decorator of the authenticate_impl method to provide time performance monitoring
        """
        return self.timer(self.authenticate_impl, args=request)

    def authenticate_impl(self, request):
        """
        This method verifies the token in the request header corresponds to a valid user
        :param request:
        :return:
        - the username if token is valid
        - TokenNotValidException if the server returns 403
        - InternalSystemError for all the other cases
        """
        if request.environ is None or request.environ.get("HTTP_AUTHORIZATION") is None:
            logger.debug(f"Authorization header absent {request.environ}")
            raise TokenNotValidException("Authorization header not found")

        # validate the authorization header
        auth_header = request.environ.get("HTTP_AUTHORIZATION")
        try:
            auth_type, credentials = auth_header.split(' ', 1)
            auth_email, auth_token = credentials.split(':', 1)
        except ValueError:
            logger.debug(f"Authorization header not recognised {auth_header}")
            raise TokenNotValidException(
                "Could not read authorization header, expected 'Authorization: <email>:<key>'")

        # validate the token
        username, email = self._token_to_username(auth_token)

        # validate the email
        if auth_email.casefold() != email.casefold():
            logger.debug(f"Emails not matching {auth_email.casefold()}, {email.casefold()}")
            raise TokenNotValidException("Invalid email associate to the token.")

        return username

    def _token_to_username_impl(self, token):
        """
        This method verifies the token corresponds to a valid user.
        Access this method by self._token_to_username
        :param token:
        :return:
        - the username and email if token is valid
        - InternalSystemError for all the other cases
        """
        logger.debug(f"Request authentication for token {token}")

        resp = self.wait_for_resp(token)

        # just in case requests does not always raise an error
        if resp.status_code != 200:
            message = f'Not able to authenticate token {token} to {self.url}, status {resp.status_code}, ' \
                f'{resp.reason}, {resp.content.decode()}'
            logger.error(message)
            raise InternalSystemError(f'Error in authenticating token {token}, please contact the support team')

        # we got a 200, extract the username and email
        resp_body = resp.json()
        if resp_body.get("uid") is None:
            logger.error(f"Not able to find username in: {resp_body}")
            raise InternalSystemError(f'Error in authenticating token {token}, please contact the support team')
        # get the username
        username = resp_body.get("uid")

        if resp_body.get("email") is None:
            logger.error(f"Not able to find email in: {resp_body}")
            raise InternalSystemError(f'Error in authenticating token {token}, please contact the support team')
        email = resp_body.get("email")

        logger.debug(f"Token correctly validated with user {username}, email {email}")
        return username, email

    def wait_for_resp(self, token):
        """
        This methods helps in cases of 429, too many requests at the same time, by spacing in time the requests
        :param token:
        :return: response to token validation
        - TokenNotValidException if the server returns 403
        - AuthenticationUnavailableException if unreachable
        """
        n_tries = 0
        while n_tries < MAX_N_TRIES:
            try:
                resp = requests.get(self.url, headers={"X-ECMWF-Key": token}, timeout=self.req_timeout)
                if resp.status_code == 429:  # Too many request just retry in a bit
                    time.sleep(random.uniform(1, 5))
                    n_tries += 1
                else:
                    # raise an error for any other case
                    resp.raise_for_status()
                    # or just exit as we have a good result
                    break
            except requests.exceptions.HTTPError as errh:
                message = f'Not able to authenticate token {token} from {self.url}, {str(errh)}'
                if resp.status_code == 403:
                    logger.debug(message)
                    raise TokenNotValidException(f'Token {token} not valid')
                if resp.status_code == 408 or ( resp.status_code >= 500 and resp.status_code < 600):
                    logger.warning(message)
                    raise AuthenticationUnavailableException(f'Error in authenticating token {token}')
                else:
                    logger.error(message)
                    raise InternalSystemError(f'Error in authenticating token {token}, please contact the support team') 
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
                logger.warning(f'Not able to authenticate token {token}, {str(err)}')
                raise AuthenticationUnavailableException(f'Error in authenticating token {token}')
            except Exception as e:
                logger.exception(e)
                raise InternalSystemError(f'Error in authenticating token {token}, please contact the support team')
        # noinspection PyUnboundLocalVariable
        return resp

