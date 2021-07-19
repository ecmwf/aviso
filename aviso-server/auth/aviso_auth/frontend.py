# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import logging

import aviso_auth.custom_exceptions as custom
import gunicorn.app.base
from aviso_auth import __version__, logger
from aviso_auth.authentication import Authenticator
from aviso_auth.authorisation import Authoriser
from aviso_auth.backend_adapter import BackendAdapter
from aviso_auth.config import Config
from aviso_monitoring import __version__ as monitoring_version
from aviso_monitoring.collector.count_collector import UniqueCountCollector
from aviso_monitoring.collector.time_collector import TimeCollector
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthMetricType
from flask import Flask, Response, request
from flask_caching import Cache
from gunicorn import glogging
from six import iteritems


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
        self.authenticator = Authenticator(self.config, self.handler.cache)
        self.authoriser = Authoriser(self.config, self.handler.cache)
        self.backend = BackendAdapter(self.config)
        # this is a time collector for the whole request
        self.timer = TimeCollector(self.config.monitoring, tlm_type=AvisoAuthMetricType.auth_resp_time.name)
        self.user_counter = UniqueCountCollector(
            self.config.monitoring, tlm_type=AvisoAuthMetricType.auth_users_counter.name
        )

    def create_handler(self) -> Flask:
        handler = Flask(__name__)
        handler.title = "aviso-auth"
        # We need to bind the logger of aviso to the one of app
        logger.handlers = handler.logger.handlers

        def json_response(m, code, header=None):
            h = {"Content-Type": "application/json"}
            if header:
                h.update(header)
            return json.dumps({"message": str(m)}), code, h

        @handler.errorhandler(custom.InvalidInputError)
        def invalid_input(e):
            logger.debug(f"Request malformed: {e}")
            return json_response(e, 400)

        @handler.errorhandler(custom.TokenNotValidException)
        def token_not_valid(e):
            logger.debug(f"Authentication failed: {e}")
            return json_response(e, 401, self.authenticator.UNAUTHORISED_RESPONSE_HEADER)

        @handler.errorhandler(custom.ForbiddenDestinationException)
        def forbidden_destination(e):
            logger.debug(f"Destination not authorised: {e}")
            return json_response(e, 403)

        @handler.errorhandler(custom.UserNotFoundException)
        def user_not_found(e):
            return json_response(e, 404)

        @handler.errorhandler(custom.InternalSystemError)
        def internal_error(e):
            return json_response(e, 500)

        @handler.errorhandler(custom.AuthenticationUnavailableException)
        def authentication_unavailable(e):
            return json_response("Service currently unavailable, please try again later", 503, {"Retry-After": 30})

        @handler.errorhandler(custom.AuthorisationUnavailableException)
        def authorisation_unavailable(e):
            return authentication_unavailable(e)  # same behaviour

        @handler.errorhandler(custom.BackendUnavailableException)
        def backend_unavailable(e):
            return authentication_unavailable(e)  # same behaviour

        @handler.errorhandler(Exception)
        def default_error_handler(e):
            logger.exception(f"Request: {request.json} raised the following error: {e}")
            return (
                json.dumps({"message": "Server error occurred", "details": str(e)}),
                getattr(e, "code", 500),
                {"Content-Type": "application/json"},
            )

        @handler.route(self.config.backend["route"], methods=["POST"])
        def root():
            logger.info(f"New request received from {request.remote_addr}, content: {request.data}")

            resp_content = timed_process_request()

            # forward back the response
            return Response(resp_content)

        def process_request():
            # authenticate request and count the users
            username = self.user_counter(self.authenticator.authenticate, args=request)
            logger.debug("Request successfully authenticated")

            # authorise request
            valid = self.authoriser.is_authorised(username, request)
            if not valid:
                raise custom.ForbiddenDestinationException("User not allowed to access to the resource")
            logger.debug("Request successfully authorised")

            # forward request to backend
            resp_content = self.backend.forward(request)
            logger.info("Request completed")

            return resp_content

        def timed_process_request():
            """
            This method allows time the process_request function
            """
            return self.timer(process_request)

        return handler

    def run_server(self):
        logger.info(
            f"Running aviso-auth - version {__version__} on server {self.config.frontend['server_type']}, \
                aviso_monitoring module v.{monitoring_version}"
        )
        logger.info(f"Configuration loaded: {self.config}")

        if self.config.frontend["server_type"] == "flask":
            # flask internal server for non-production environments
            # should only be used for testing and debugging
            self.handler.run(
                debug=self.config.debug,
                host=self.config.frontend["host"],
                port=self.config.frontend["port"],
                use_reloader=False,
            )
        elif self.config.frontend["server_type"] == "gunicorn":
            options = {
                "bind": f"{self.config.frontend['host']}:{self.config.frontend['port']}",
                "workers": self.config.frontend["workers"],
                "post_worker_init": self.post_worker_init,
            }
            GunicornServer(self.handler, options).run()
        else:
            logger.error(f"server_type {self.config.frontend['server_type']} not supported")
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
        config = dict(
            [(key, value) for key, value in iteritems(self.options) if key in self.cfg.settings and value is not None]
        )
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

        # this approach does not support custom filters, therefore it's better to disable it
        # self.cfg.set('logger_class', GunicornServer.CustomLogger)

    def load(self):
        return self.application

    class CustomLogger(glogging.Logger):
        """Custom logger for Gunicorn log messages."""

        def setup(self, cfg):
            """Configure Gunicorn application logging configuration."""
            super().setup(cfg)

            formatter = logging.getLogger().handlers[0].formatter

            # Override Gunicorn's `error_log` configuration.
            self._set_handler(self.error_log, cfg.errorlog, formatter)


# when running directly from this file
if __name__ == "__main__":
    main()
