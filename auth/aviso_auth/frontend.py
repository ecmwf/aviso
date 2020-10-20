# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import logging

import gunicorn.app.base
from aviso_auth import logger, __version__
from aviso_auth.authentication import Authenticator
from aviso_auth.authorisation import Authoriser
from aviso_auth.backend_adapter import BackendAdapter
from aviso_auth.config import UserConfig
from aviso_auth.custom_exceptions import InvalidInputError, NotFoundException, InternalSystemError, \
    AuthenticationException, ForbiddenRequestException
from flask import Flask
from flask import Response
from flask import request
from flask_caching import Cache
from gunicorn import glogging
from six import iteritems


class Frontend:

    def __init__(self, config: UserConfig):
        self.config = config
        self.handler = self.create_handler()
        self.handler.cache = Cache(self.handler, config=config.cache)
        self.authenticator = Authenticator(config.authentication_server, self.handler.cache)
        self.authoriser = Authoriser(config.authorisation_server, self.handler.cache)
        self.backend = BackendAdapter(config.backend)

    def create_handler(self) -> Flask:
        handler = Flask(__name__)
        handler.title = "aviso-auth"
        # We need to bind the logger of aviso to the one of app
        logger.handlers = handler.logger.handlers

        def json_response(m, code, header={}):
            h = {'Content-Type': 'application/json'}
            h.update(header)
            return json.dumps({"message": str(m)}), code, h

        @handler.errorhandler(InvalidInputError)
        def bad_request(e):
            logger.debug(f"Request malformed: {e}")
            return json_response(e, 400)

        @handler.errorhandler(AuthenticationException)
        def not_authenticated(e):
            logger.debug(f"Authentication failed: {e}")
            return json_response(e, 401, self.authenticator.UNAUTHORISED_RESPONSE_HEADER)

        @handler.errorhandler(ForbiddenRequestException)
        def forbidden_request(e):
            logger.debug(f"Request not authorised: {e}")
            return json_response(e, 403)

        @handler.errorhandler(NotFoundException)
        def not_found(e):
            logger.debug(f"Backend could not find resource requested: {e}")
            return json_response(e, 404)

        @handler.errorhandler(InternalSystemError)
        def internal_error(e):
            return json_response(e, 500)

        @handler.errorhandler(Exception)
        def default_error_handler(e):
            logging.exception(str(e))
            return json_response(e, 500)

        @handler.route(self.config.backend['route'], methods=["POST"])
        def root():
            logger.debug("New request received")

            # authenticate request
            username = self.authenticator.authenticate(request)
            logger.debug("Request successfully authenticated")

            # authorise request
            valid = self.authoriser.is_authorised(username, request)
            if not valid:
                return forbidden_request("User not allowed to access to the resource")
            logger.debug("Request successfully authorised")

            # forward request to backend
            resp_content = self.backend.forward(request)
            logger.debug("Request successfully forwarded to Aviso server")

            # forward back the response
            return Response(resp_content)

        return handler

    def run_server(self):
        logger.info(f"Running aviso-auth - version { __version__} on server {self.config.frontend['server_type']}")
        logger.info(f"Configuration loaded: {self.config}")

        if self.config.frontend["server_type"] == "flask":
            # flask internal server for non-production environments
            # should only be used for testing and debugging
            self.handler.run(debug=self.config.debug, host=self.config.frontend["host"],
                             port=self.config.frontend["port"], use_reloader=False)
        elif self.config.frontend["server_type"] == "gunicorn":
            options = {"bind": f"{self.config.frontend['host']}:{self.config.frontend['port']}",
                       "workers": self.config.frontend['workers']}
            GunicornServer(self.handler, options).run()
        else:
            logging.error(f"server_type {self.config.frontend['server_type']} not supported")
            raise NotImplementedError


def main():
    # initialising the user configuration configuration
    config = UserConfig()

    # create the frontend class and run it
    frontend = Frontend(config)
    frontend.run_server()


class GunicornServer(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(GunicornServer, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

        self.cfg.set('logger_class', GunicornServer.CustomLogger)

    def load(self):
        return self.application

    class CustomLogger(glogging.Logger):
        """Custom logger for Gunicorn log messages."""

        def setup(self, cfg):
            """Configure Gunicorn application logging configuration."""
            super().setup(cfg)

            formatter = logging.getLogger().handlers[0].formatter

            # Override Gunicorn's `error_log` configuration.
            self._set_handler(
                self.error_log, cfg.errorlog, formatter
            )


# when running directly from this file
if __name__ == "__main__":
    main()
