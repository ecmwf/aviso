# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import random
import time

import jwt
import requests
from aviso_auth.custom_exceptions import InternalSystemError, TokenNotValidException
from aviso_monitoring.collector.time_collector import TimeCollector
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthMetricType

logger = logging.getLogger("aviso-auth")
MAX_N_TRIES = 25


class Authenticator:
    UNAUTHORISED_RESPONSE_HEADER = {"WWW-Authenticate": "Bearer realm='auth-o-tron',info='Provide a valid token'"}

    def __init__(self, config, cache=None):
        """
        Initialize the Authenticator.
        Loads authentication server settings from the configuration.
        Uses Flask-Caching if 'cache' is provided to memoize token validation.
        If monitoring is enabled (authentication_server["monitor"] = True),
        wraps the authentication method in a TimeCollector.
        """
        logger.debug("Initializing Authenticator with config: %s", config)
        self.config = config
        self.url = config.authentication_server.get("url", "")
        self.req_timeout = config.authentication_server.get("req_timeout", 10)
        logger.debug("Authentication server URL: %s, timeout: %s", self.url, self.req_timeout)

        self._cached_providers = None

        self.cache = cache

        if config.authentication_server.get("monitor"):
            self.timer = TimeCollector(
                config.monitoring, tlm_type=AvisoAuthMetricType.auth_resp_time.name, tlm_name="att"
            )
            logger.debug("Monitoring enabled for authentication; using timed_authenticate")
            self.authenticate = self.timed_authenticate
        else:
            self.authenticate = self.authenticate_impl

        if self.cache:
            logger.debug(
                "Using memoized token validator with cache timeout = %s",
                config.authentication_server.get("cache_timeout", 300),
            )
            # Wrap _validate_token_uncached with memoize
            self.validate_token_cached = self.cache.memoize(
                timeout=config.authentication_server.get("cache_timeout", 300)
            )(self._validate_token_uncached)
        else:
            logger.debug("No cache provided; validation calls are uncached.")
            self.validate_token_cached = self._validate_token_uncached

    def timed_authenticate(self, request):
        """
        Wraps the authenticate_impl with a time collector.
        """
        logger.debug("timed_authenticate: Starting timed authentication")
        return self.timer(self.authenticate_impl, args=(request,))

    def authenticate_impl(self, request):
        """
        Main authentication flow.

        Steps:
          1. Extract the Authorization and X-Auth-Type headers.
          2. Map the X-Auth-Type value to the expected provider type.
          3. Ensure a matching provider exists (via get_providers).
          4. Extract the token from the Authorization header.
          5. Validate the token (cached).
          6. Extract user information (username, realm).
          7. Return the username.
        """
        logger.debug("authenticate_impl: Starting authentication process")

        # Step 1: Extract headers.
        auth_header, x_auth_type = self.extract_auth_headers(request)

        # Step 2: Map incoming auth type.
        expected_provider_type = self.map_auth_type(x_auth_type)

        # Step 3: Ensure a matching provider exists.
        self.get_matching_provider(expected_provider_type)

        # Step 4: Extract the token from the Authorization header.
        token = self.extract_token(auth_header, x_auth_type)

        # Optionally, gather client IP for logging:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"

        # Step 5: Validate the token. (NEW: using the memoized version!)
        resp = self.validate_token_cached(token, x_auth_type, client_ip=client_ip)

        # Step 6: Extract user information.
        username, realm = self._token_to_username_impl(resp)

        # Step 7: Return the username.
        logger.debug("authenticate_impl: Returning username: %s", username)
        return username

    def extract_auth_headers(self, request):
        """
        Extracts the Authorization header and the X-Auth-Type header.
        """
        if not hasattr(request, "environ"):
            logger.error("Request missing environ attribute")
            raise TokenNotValidException("Invalid request: no environ attribute")
        auth_header = request.environ.get("HTTP_AUTHORIZATION")
        if not auth_header:
            logger.error("Missing Authorization header in request")
            raise TokenNotValidException("Missing Authorization header")
        logger.debug("Extracted Authorization header: %s", auth_header)

        x_auth_type = request.headers.get("X-Auth-Type")
        if not x_auth_type:
            logger.error("Missing X-Auth-Type header in request")
            raise TokenNotValidException("Missing X-Auth-Type header")
        logger.debug("Extracted X-Auth-Type header: %s", x_auth_type)

        return auth_header, x_auth_type

    def map_auth_type(self, x_auth_type):
        """
        Maps the X-Auth-Type to the expected provider type.
        """
        mapping = {"ecmwf": "ecmwf-api", "plain": "plain", "openid": "openid-offline"}
        expected = mapping.get(x_auth_type.lower())
        if not expected:
            logger.error("Unknown X-Auth-Type value: %s", x_auth_type)
            raise TokenNotValidException(f"Unknown auth type: {x_auth_type}")
        logger.debug("Mapped X-Auth-Type '%s' to expected provider type '%s'", x_auth_type, expected)
        return expected

    def get_providers(self):
        """
        Retrieves providers from auth-o-tron /providers, caches them locally.
        """
        if self._cached_providers is not None:
            logger.debug("Using cached providers data: %s", self._cached_providers)
            return self._cached_providers

        providers_url = f"{self.url}/providers"
        logger.debug("Querying providers from auth-o-tron at: %s", providers_url)
        try:
            resp = requests.get(providers_url, timeout=self.req_timeout)
            logger.debug("Received providers response, status: %s", resp.status_code)
            resp.raise_for_status()
            providers_data = resp.json()
            logger.debug("Providers data: %s", providers_data)
            self._cached_providers = providers_data
            return providers_data
        except Exception as e:
            logger.error("Error querying providers endpoint: %s", e, exc_info=True)
            raise InternalSystemError("Failed to retrieve providers from auth-o-tron")

    def get_matching_provider(self, expected_provider_type):
        """
        Check if the retrieved providers contain the given expected_provider_type.
        """
        providers = self.get_providers()
        for provider in providers.get("providers", []):
            p_type = provider.get("type", "").lower()
            logger.debug("Checking provider: %s", provider)
            if p_type == expected_provider_type:
                logger.debug("Matched provider: %s", provider)
                return provider
        logger.error("No provider found for expected auth type: %s", expected_provider_type)
        raise TokenNotValidException(f"No provider available for auth type matching '{expected_provider_type}'")

    def extract_token(self, auth_header, x_auth_type):
        """
        Splits the Authorization header and ensures the correct scheme based on x_auth_type.
        """
        try:
            scheme, token = auth_header.split(" ", 1)
        except Exception as e:
            logger.error("Failed to parse Authorization header: %s", e, exc_info=True)
            raise TokenNotValidException("Invalid Authorization header format")

        expected_scheme = "basic" if x_auth_type.lower() == "plain" else "bearer"
        if scheme.lower() != expected_scheme:
            logger.error("Expected '%s' scheme, got: %s", expected_scheme.capitalize(), scheme)
            raise TokenNotValidException("Unsupported authorization scheme")
        logger.debug("extract_token: Extracted token: %s", token)
        return token

    def _validate_token_uncached(self, token, x_auth_type, client_ip="unknown"):
        """
        The real token validation logic that calls auth-o-tron /authenticate.
        This method is NOT decorated. The memoized version wraps it if caching is set.
        """
        if x_auth_type.lower() in ["ecmwf", "openid"]:
            auth_header = f"Bearer {token}"
        elif x_auth_type.lower() == "plain":
            auth_header = f"Basic {token}"
        else:
            logger.warning("validate_token: Unknown auth type: %s", x_auth_type)
            raise TokenNotValidException(f"Unknown auth type: {x_auth_type}")

        headers = {"Authorization": auth_header}
        auth_url = f"{self.url}/authenticate"
        logger.debug(
            "Calling auth-o-tron /authenticate at %s [auth_type=%s, client_ip=%s]", auth_url, x_auth_type, client_ip
        )

        n_tries = 0
        while n_tries < MAX_N_TRIES:
            logger.debug("validate_token: Attempt %d [auth_type=%s, ip=%s]", n_tries + 1, x_auth_type, client_ip)
            try:
                resp = requests.get(auth_url, headers=headers, timeout=self.req_timeout)
                logger.debug("validate_token: Received response with status %d", resp.status_code)
                if resp.status_code == 429:
                    logger.debug("validate_token: Rate limited (429), sleeping")
                    time.sleep(random.uniform(1, 5))
                    n_tries += 1
                    continue

                resp.raise_for_status()  # 4xx or 5xx => HTTPError
                logger.debug(
                    "validate_token: Token validated successfully [auth_type=%s, ip=%s]", x_auth_type, client_ip
                )
                return resp

            except requests.exceptions.HTTPError:
                status_code = resp.status_code
                if status_code in [401, 403]:
                    logger.warning(
                        "validate_token: %d Unauthorized/forbidden [auth_type=%s, ip=%s, reason=%.200s]",
                        status_code,
                        x_auth_type,
                        client_ip,
                        resp.text,
                    )
                    raise TokenNotValidException("Invalid credentials or unauthorized token")
                if status_code == 408 or (500 <= status_code < 600):
                    logger.warning(
                        "validate_token: Temporary HTTP error %d [auth_type=%s, ip=%s], reason=%s, retrying",
                        status_code,
                        x_auth_type,
                        client_ip,
                        resp.reason,
                    )
                    n_tries += 1
                    time.sleep(random.uniform(1, 5))
                else:
                    logger.error(
                        "validate_token: Unexpected HTTP error %d [auth_type=%s, ip=%s], reason=%s",
                        status_code,
                        x_auth_type,
                        client_ip,
                        resp.reason,
                    )
                    raise InternalSystemError("Unexpected HTTP error during token validation")

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
                logger.warning(
                    "validate_token: Connection/Timeout error on attempt %d [auth_type=%s, ip=%s]: %s",
                    n_tries + 1,
                    x_auth_type,
                    client_ip,
                    err,
                )
                n_tries += 1
                time.sleep(random.uniform(1, 5))

            except Exception as e:
                logger.error(
                    "validate_token: Unexpected error on attempt %d [auth_type=%s, ip=%s]: %s",
                    n_tries + 1,
                    x_auth_type,
                    client_ip,
                    e,
                )
                raise InternalSystemError("Unexpected error during token validation")

        logger.error(
            "validate_token: Exceeded maximum attempts (%d) [auth_type=%s, ip=%s]", MAX_N_TRIES, x_auth_type, client_ip
        )
        raise InternalSystemError("Exceeded maximum token validation attempts")

    def validate_token(self, token, x_auth_type, client_ip="unknown"):
        """
        Public wrapper that calls the memoized validation function (if caching is enabled)
        or the uncached version if no cache. This function name is the one
        used in authenticate_impl for consistency.
        """
        return self.validate_token_cached(token, x_auth_type, client_ip=client_ip)

    def _token_to_username_impl(self, resp):
        """
        Extracts user info from the auth-o-tron /authenticate response.
        Decodes a JWT from the response header "authorization".
        Logs an INFO message for successful authentication.
        """
        auth_header = resp.headers.get("authorization")
        if not auth_header:
            logger.error("auth-o-tron response missing 'authorization' header")
            raise InternalSystemError("Invalid response from auth-o-tron: missing authorization header")

        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.error("Invalid authorization header format: %s", auth_header)
            raise InternalSystemError("Invalid response from auth-o-tron: incorrect authorization header format")

        jwt_token = parts[1].strip()
        if not jwt_token:
            logger.error("JWT token is empty in authorization header")
            raise InternalSystemError("Invalid response from auth-o-tron: empty JWT token")

        logger.debug("Extracted JWT token from response header: %s", jwt_token)
        try:
            payload = jwt.decode(jwt_token, options={"verify_signature": False})
            logger.debug("Decoded JWT payload: %s", payload)
        except Exception as e:
            logger.error("Failed to decode JWT token. Raw token: '%s'. Error: %s", jwt_token, e)
            raise InternalSystemError("Invalid JWT returned from auth-o-tron")

        username = payload.get("username")
        if not username:
            logger.error("JWT payload missing 'username': %s", payload)
            raise InternalSystemError("Token validation error: username missing")

        realm = payload.get("realm", "unknown")
        logger.info("User '%s' successfully authenticated with realm '%s'", username, realm)
        return username, realm
