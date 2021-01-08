# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import logging
from typing import Dict

import gunicorn.app.base
from flask import Flask
from flask import request
from gunicorn import glogging
from six import iteritems
from cloudevents.http import from_http
from aviso_rest import logger, __version__
from pyaviso.custom_exceptions import InvalidInputError
# from flask_swagger_ui import get_swaggerui_blueprint
from pyaviso.notification_manager import NotificationManager
from aviso_rest.config import Config
from aviso_monitoring.collector.time_collector import TimeCollector

SWAGGER_URL = '/openapi'
API_URL = 'frontend/web/openapi.yaml'

class Frontend:

    def __init__(self, config):
        self.config = config
        # initialise the handler
        self.handler = self.create_handler()
        self.notification_manager = NotificationManager()
        # we need to create the timer object here if this app runs in Flask, 
        # if instead it runs in Gunicorn the hook post_worker_init will take over, and this timer will not be used
        self.init_timer()

    def init_timer(self):
        """
        This method initialise the timer that is valid globally at application level or per worker
        """
        self.timer = TimeCollector(self.config.monitoring)   

    def create_handler(self) -> Flask:
        handler = Flask(__name__)
        handler.title = "Aviso"
        # We need to bind the logger of aviso to the one of app
        logger.handlers = handler.logger.handlers

        # # setting up swagger
        # SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
        #     SWAGGER_URL,
        #     API_URL,
        #     config={
        #         'app_name': "Aviso"
        #     }
        # )
        # handler.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)

        def bad_request(m):
            logging.error(f"Request: {request.json}")
            return json.dumps({"message": str(m)}), 400, {'Content-Type': 'application/json'}

        def ok(m):
            return json.dumps({"message": str(m)}), 200, {'Content-Type': 'application/json'}

        @handler.errorhandler(Exception)
        def default_error_handler(error):
            logging.exception(str(error))
            logging.error(f"Request: {request.json}")
            return json.dumps(
                {"message": "Internal server error occurred", "details": str(error)}
            ), getattr(error, 'code', 500), {'Content-Type': 'application/json'}

        @handler.route("/", methods=['GET'])
        def root():
            with open("aviso_rest/web/index.html") as fh:
                content = fh.read()
            content = content.format(
                page_title="Aviso",
                welcome_title=f"Aviso v. { __version__} homepage",
                welcome_text="This is the frontend of the Aviso notification system"
            )
            return content

        @handler.route("/api/v1/notification", methods=["POST"])
        def notify():
            logger.debug("New notification received")

            # we expect only JSON body
            body = request.json
            if body is None:
                return bad_request("Invalid notification, Body cannot be empty")
            logger.debug(body)
            try:
                # parse the body as cloud event
                notification = self._parse_cloud_event(request)
                logger.info(f"New event received: {notification}")

                # send the notification and time it
                self.timed_notify(notification, config=self.config.aviso)
            except InvalidInputError as e:
                return bad_request(e)
            logger.debug("Notification successfully submitted")
            return ok("Notification successfully submitted")

        return handler

    def timed_notify(self, notification, config):
        """
        This method allows to submit a notification to the store and to time it
        """
        return self.timer(self.notification_manager.notify, args=(notification, config))

    def run_server(self):
        logger.info(f"Running AVISO Frontend - version { __version__} on server {self.config.server_type}")
        logger.info(f"Configuration loaded: {self.config}")

        if self.config.server_type == "flask":
            # flask internal server for non-production environments
            # should only be used for testing and debugging
            self.handler.run(debug=self.config.debug, host=self.config.host,
                             port=self.config.port, use_reloader=False)
        elif self.config.server_type == "gunicorn":
            options = {"bind": f"{self.config.host}:{self.config.port}",
                       "workers": self.config.workers, "post_worker_init": self.post_worker_init}
            GunicornServer(self.handler, options).run()
        else:
            logging.error(f"server_type {self.config.server_type} not supported")
            raise NotImplementedError

    def _parse_cloud_event(self, request) -> Dict:
        """
        This helper method parses cloud event message, validate it and return the notification associated to it
        :param request: cloud event request
        :return: notification as dictionary
        """
        try:
            cloudevent = from_http(request.headers, request.get_data())

            # extract the notification
            assert cloudevent.data is not None, "Invalid notification, 'data' could not be located"
            notification = cloudevent.data
            assert notification.get("event") is not None, "Invalid notification, 'event' could not be located"
            assert notification.get("request") is not None, "Invalid notification, 'request' could not be located"
            req = notification.pop("request")
            notification.update(req)
            return notification
        except Exception as e:
            raise InvalidInputError(e)

    def post_worker_init(self, worker):
        """
        This method is called just after a worker has initialized the application.
        This method is a Gunicorn server hook. Gunicorn spawns this app over multiple workers as processes.
        This method ensures that there is only one timer and one transmitter thread running per worker. Without this hook a transmitter thread is created at 
        application level but not at worker level and then at every request a timer will be created detached from the transmitter thread.
        This would result in no teletry collected.
        """
        logger.debug("Initialising a tlm collector per worker")
        self.init_timer()

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

