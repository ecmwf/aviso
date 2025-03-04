# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json

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
from flask import Flask, Response, render_template, request
from flask_caching import Cache


class Frontend:
    def __init__(self, config: Config):
        self.config = config
        self.handler = self.create_handler()
        self.handler.cache = Cache(self.handler, config=config.cache)

        # For direct runs (e.g. Flask "server_type"):
        # We'll initialize the app-level components now.
        self.init_components()

    def init_components(self):
        """
        Initializes the Authenticator, Authoriser, BackendAdapter,
        and sets up time-collectors or counters as needed.
        """
        # Create the authenticator (with caching if provided)
        self.authenticator = Authenticator(self.config, self.handler.cache)
        self.authoriser = Authoriser(self.config, self.handler.cache)
        self.backend = BackendAdapter(self.config)

        # A time collector for measuring entire request durations (via timed_process_request()).
        self.timer = TimeCollector(self.config.monitoring, tlm_type=AvisoAuthMetricType.auth_resp_time.name)

        # A UniqueCountCollector for counting user accesses. This is used in process_request().
        self.user_counter = UniqueCountCollector(
            self.config.monitoring, tlm_type=AvisoAuthMetricType.auth_users_counter.name
        )

        logger.debug("All components initialized: Authenticator, Authoriser, BackendAdapter, timers, counters")

    def create_handler(self) -> Flask:
        handler = Flask(__name__)
        handler.title = "aviso-auth"

        # Bind aviso_auth logger to the Flask app logger.
        logger.handlers = handler.logger.handlers

        def json_response(m, code, header=None):
            """
            Utility for building JSON response.
            """
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
            """
            Return a 401 and attach the
            "WWW-Authenticate" header from Authenticator.
            """
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

        @handler.route("/", methods=["GET"])
        def index():
            """
            Simple index route that renders an index.html template
            (if shipping a front-end).
            Otherwise, can return a basic message.
            """
            return render_template("index.html")

        @handler.route(self.config.backend["route"], methods=["POST"])
        def root():
            """
            The main route for your proxying or backend forwarding logic.
            """
            logger.info(
                f"New request received from {request.headers.get('X-Forwarded-For')}, " f"content: {request.data}"
            )
            resp_content = timed_process_request()
            return Response(resp_content)

        def process_request():
            """
            The main request processing flow:
             1. Authenticate
             2. Authorise
             3. Forward to backend
            """
            # (1) Authenticate request and increment user counter
            username = self.user_counter(self.authenticator.authenticate, args=request)
            logger.debug("Request successfully authenticated")

            # (2) Authorise request
            valid = self.authoriser.is_authorised(username, request)
            if not valid:
                raise custom.ForbiddenDestinationException("User not allowed to access the resource")
            logger.debug("Request successfully authorised")

            # (3) Forward request to backend
            resp_content = self.backend.forward(request)
            logger.info("Request completed")
            return resp_content

        def timed_process_request():
            """
            Wraps process_request in a time collector (self.timer).
            """
            return self.timer(process_request)

        return handler

    def run_server(self):
        """
        Launches the server using either Flask's built-in server or Gunicorn.
        """
        logger.info(
            f"Running aviso-auth - version {__version__} on server {self.config.frontend['server_type']}, "
            f"aviso_monitoring module v.{monitoring_version}"
        )
        logger.info(f"Configuration loaded: {self.config}")

        if self.config.frontend["server_type"] == "flask":
            # Not recommended for production, but good for dev/test
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
        Called just after a worker initializes the application in Gunicorn.
        Re-initializes any components that need a separate instance per worker process.
        """
        logger.debug("Initialising components per worker")
        self.init_components()


class GunicornServer(gunicorn.app.base.BaseApplication):
    """
    Gunicorn server wrapper.
    """

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        from six import iteritems

        config = dict(
            [(key, value) for key, value in iteritems(self.options) if key in self.cfg.settings and value is not None]
        )
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main():
    config = Config()
    frontend = Frontend(config)
    frontend.run_server()


if __name__ == "__main__":
    main()
