# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import logging
from flask import Flask
from flask import Response
from flask import request
from flask_caching import Cache
from gunicorn import glogging
from six import iteritems
import gunicorn.app.base
from aviso_auth import logger, __version__
from aviso_auth.authentication import Authenticator
from aviso_auth.authorisation import Authoriser
from aviso_auth.backend_adapter import BackendAdapter
from aviso_auth.config import Config
from aviso_auth.custom_exceptions import InvalidInputError, NotFoundException, InternalSystemError, \
    AuthenticationException, ForbiddenRequestException
from aviso_monitoring.collector.time_collector import TimeCollector


class Frontend:

    def __init__(self, config: Config):
        self.config = config
        self.handler = self.create_handler()
        self.handler.cache = Cache(self.handler, config=config.cache)
        # we need to initialise our components and timer here if this app runs in Flask, 
        # if instead it runs in Gunicorn the hook post_worker_init will take over, and these components will not be used
        self.init_components()

    def init_components(self):
        """
        This method initialise a set of components and timers that are valid globally at application level or per worker
        """
        # noinspection PyUnresolvedReferences
        self.authenticator = Authenticator(self.config, self.handler.cache)
        # noinspection PyUnresolvedReferences
        self.authoriser = Authoriser(self.config, self.handler.cache)
        self.backend = BackendAdapter(self.config)
        # this is a time collector for the whole request
        self.timer = TimeCollector(self.config.monitoring)

    def create_handler(self) -> Flask:
        handler = Flask(__name__)
        handler.title = "aviso-auth"
        # We need to bind the logger of aviso to the one of app
        logger.handlers = handler.logger.handlers

        def json_response(m, code, header=None):
            h = {'Content-Type': 'application/json'}
            if header:
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
            try:
                resp_content = timed_process_request()

                # forward back the response
                return Response(resp_content)
            except ForbiddenRequestException:
                return forbidden_request("User not allowed to access to the resource")

        def process_request():
            # authenticate request
            username = self.authenticator.authenticate(request)
            logger.debug("Request successfully authenticated")

            # authorise request
            valid = self.authoriser.is_authorised(username, request)
            if not valid:
                raise ForbiddenRequestException()
            logger.debug("Request successfully authorised")

            # forward request to backend
            resp_content = self.backend.forward(request)
            logger.debug("Request successfully forwarded to Aviso server")

            return resp_content

        def timed_process_request():
            """
            This method allows time the process_request function
            """
            return self.timer(process_request)

        return handler

    def run_server(self):
        logger.info(f"Running aviso-auth - version {__version__} on server {self.config.frontend['server_type']}")
        logger.info(f"Configuration loaded: {self.config}")

        if self.config.frontend["server_type"] == "flask":
            # flask internal server for non-production environments
            # should only be used for testing and debugging
            self.handler.run(debug=self.config.debug, host=self.config.frontend["host"],
                             port=self.config.frontend["port"], use_reloader=False)
        elif self.config.frontend["server_type"] == "gunicorn":
            options = {"bind": f"{self.config.frontend['host']}:{self.config.frontend['port']}",
                       "workers": self.config.frontend['workers'], "post_worker_init": self.post_worker_init}
            GunicornServer(self.handler, options).run()
        else:
            logging.error(f"server_type {self.config.frontend['server_type']} not supported")
            raise NotImplementedError

    def post_worker_init(self, worker):
        """
        This method is called just after a worker has initialized the application.
        It is a Gunicorn server hook. Gunicorn spawns this app over multiple workers as processes.
        This method ensures that there is only one set of components and timer running per worker. Without this hook
        the components and timers are created at application level but not at worker level and then at every request a
        timers will be created detached from the main transmitter threads.
        This would result in no telemetry collected.
        """
        logger.debug("Initialising components per worker")
        self.init_components()


def main():
    # initialising the user configuration configuration
    config = Config()

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

        #this approach does not support custom filters, therefore it's better to disable it
        #self.cfg.set('logger_class', GunicornServer.CustomLogger)

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
