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
    # Following is the fallback response header in case of an unauthorized response
    # from the authentication server does not provide a WWW-Authenticate header.
    UNAUTHORISED_RESPONSE_HEADER = {"WWW-Authenticate": 'Bearer realm="auth-o-tron"'}

    def __init__(self, config, cache=None):
        """
        Initialize the Authenticator.
        - Loads the authentication server URL and request timeout from the configuration.
        - If a cache is provided, token validation is memoized to avoid repeated calls.
        - If monitoring is enabled (authentication_server["monitor"] is True),
        wraps the authenticate method with a TimeCollector.
        """
        logger.debug("Initializing Authenticator with config: %s", config)
        self.config = config
        self.url = config.authentication_server.get("url", "")
        self.req_timeout = config.authentication_server.get("req_timeout", 10)
        logger.debug("Authentication server URL: %s, timeout: %s", self.url, self.req_timeout)

        self.cache = cache

        # Setup monitoring if enabled.
        if config.authentication_server.get("monitor"):
            self.timer = TimeCollector(
                config.monitoring, tlm_type=AvisoAuthMetricType.auth_resp_time.name, tlm_name="att"
            )
            logger.debug("Monitoring enabled; using timed_authenticate")
            self.authenticate = self.timed_authenticate
        else:
            self.authenticate = self.authenticate_impl

        # Wrap the token validation function with caching if available.
        if self.cache:
            logger.debug(
                "Using memoized token validator with cache timeout = %s",
                config.authentication_server.get("cache_timeout", 300),
            )
            self.validate_token_cached = self.cache.memoize(
                timeout=config.authentication_server.get("cache_timeout", 300)
            )(self._validate_token_uncached)
        else:
            logger.debug("No cache provided; using uncached token validation")
            self.validate_token_cached = self._validate_token_uncached

    def timed_authenticate(self, request):
        """
        Wraps the authenticate_impl method with a TimeCollector.
        """
        logger.debug("timed_authenticate: Starting timed authentication")
        return self.timer(self.authenticate_impl, args=(request,))

    def authenticate_impl(self, request):
        """
        Main authentication flow:
          1. Extract the Authorization and X-Auth-Type headers.
          2. Extract the token from the Authorization header.
          3. Gather the client IP (for logging).
          4. Validate the token (cached).
          5. Decode the JWT from the validation response to extract username and realm.
          6. Return the username.
        """
        logger.debug("authenticate_impl: Starting authentication process")

        # Step 1: Extract headers.
        auth_header, x_auth_type = self.extract_auth_headers(request)

        # Step 2: Extract the token from the Authorization header.
        token = self.extract_token(auth_header, x_auth_type)

        # Step 3: Get the client IP.
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"

        # Step 4: Validate the token (cached).
        resp = self.validate_token_cached(token, x_auth_type, client_ip=client_ip)

        # Step 5: Decode the JWT to extract user information.
        username, realm = self._token_to_username_impl(resp)

        logger.debug("authenticate_impl: Returning username: %s", username)
        return username

    def extract_auth_headers(self, request):
        """
        Extracts the HTTP_AUTHORIZATION header from request.environ and the custom X-Auth-Type header.
        If Authorization header uses EmailKey scheme, X-Auth-Type is assumed to be "ecmwf" even if missing.
        """
        if not hasattr(request, "environ"):
            logger.error("Request missing environ attribute")
            raise TokenNotValidException("Invalid request: no environ attribute")

        auth_header = request.environ.get("HTTP_AUTHORIZATION")
        if not auth_header:
            logger.error("Missing Authorization header")
            raise TokenNotValidException("Missing Authorization header")
        logger.debug("Extracted Authorization header: %s", auth_header)

        # Check if this is an EmailKey authorization before requiring X-Auth-Type
        if auth_header.lower().startswith("emailkey "):
            # For EmailKey, assume X-Auth-Type is "ecmwf" if not provided
            x_auth_type = request.headers.get("X-Auth-Type", "ecmwf")
            logger.debug("EmailKey detected: Using X-Auth-Type '%s'", x_auth_type)
        else:
            # For other auth schemes, X-Auth-Type is required
            x_auth_type = request.headers.get("X-Auth-Type")
            if not x_auth_type:
                logger.error("Missing X-Auth-Type header")
                raise TokenNotValidException("Missing X-Auth-Type header")
            logger.debug("Extracted X-Auth-Type header: %s", x_auth_type)

        return auth_header, x_auth_type

    def extract_token(self, auth_header, x_auth_type):
        """
        Parses the Authorization header to extract the token.
        For "plain" auth, expects a Basic scheme; for all other auth types, expects Bearer.
        Legacy clients sending "EmailKey" are automatically mapped to "Bearer" and
        X-Auth-Type is assumed to be "ecmwf".
        """
        try:
            scheme, token = auth_header.split(" ", 1)
        except Exception as e:
            logger.error("Failed to parse Authorization header: %s", e, exc_info=True)
            raise TokenNotValidException("Invalid Authorization header format")

        # Map legacy "EmailKey" scheme to "Bearer" and ensure X-Auth-Type is "ecmwf"
        if scheme.lower() == "emailkey":
            logger.debug("Mapping legacy 'EmailKey' scheme to 'Bearer'")
            scheme = "Bearer"
            # Ensure X-Auth-Type is "ecmwf" when EmailKey is used
            if x_auth_type.lower() != "ecmwf":
                logger.debug("EmailKey detected but X-Auth-Type is '%s', overriding to 'ecmwf'", x_auth_type)
                x_auth_type = "ecmwf"
                token = token.split(":")[-1]

        expected_scheme = "basic" if x_auth_type.lower() == "plain" else "bearer"
        if scheme.lower() != expected_scheme:
            logger.error("Expected '%s' scheme, got: %s", expected_scheme.capitalize(), scheme)
            raise TokenNotValidException("Unsupported authorization scheme")
        logger.debug("extract_token: Extracted token: %s", token)
        return token

    def _validate_token_uncached(self, token, x_auth_type, client_ip="unknown"):
        """
        Implements the actual token validation by calling auth-o-tron /authenticate.
        For "ecmwf" and "openid", a Bearer header is used.
        For "plain", a Basic header is used.
        Retries on temporary errors.
        """
        if x_auth_type.lower() in ["ecmwf", "openid"]:
            auth_header = f"Bearer {token}"
        elif x_auth_type.lower() == "plain":
            auth_header = f"Basic {token}"
        else:
            logger.warning("Unknown auth type: %s", x_auth_type)
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

                resp.raise_for_status()  # Raises HTTPError for 4xx/5xx statuses
                logger.debug(
                    "validate_token: Token validated successfully [auth_type=%s, ip=%s]", x_auth_type, client_ip
                )
                return resp

            except requests.exceptions.HTTPError:
                status_code = resp.status_code
                # Use dynamic www-authenticate from the response header.
                www_authenticate = resp.headers.get("www-authenticate", "Not provided")
                if status_code in [401, 403]:
                    logger.warning(
                        "validate_token: %d Unauthorized [auth_type=%s, ip=%s, www-authenticate=%s, reason=%.200s]",
                        status_code,
                        x_auth_type,
                        client_ip,
                        www_authenticate,
                        resp.text,
                    )
                    raise TokenNotValidException(
                        f"Invalid credentials or unauthorized token; www-authenticate: {www_authenticate}"
                    )
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
        Public wrapper that calls the memoized token validation function (if caching is enabled),
        or the uncached version otherwise.
        """
        return self.validate_token_cached(token, x_auth_type, client_ip=client_ip)

    def _token_to_username_impl(self, resp):
        """
        Extracts user info from the auth-o-tron /authenticate response.
        Expects a JWT in the "authorization" header (format: "Bearer <jwt_token>"),
        decodes the JWT without signature verification, and extracts the "username" and "realm".
        Logs an INFO-level message on successful authentication.
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
