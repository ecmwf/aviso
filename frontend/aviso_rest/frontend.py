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

# from flask_swagger_ui import get_swaggerui_blueprint
from pyaviso.notification_manager import NotificationManager
from pyaviso import logger, VERSION
from pyaviso.custom_exceptions import InvalidInputError
from pyaviso.user_config import UserConfig

SWAGGER_URL = '/openapi'
API_URL = 'frontend/web/openapi.yaml'


class Frontend:

    def __init__(self, config: UserConfig):
        self.config = config
        # initialise the handler
        self.handler = self.create_handler()
        self.notification_manager = NotificationManager()

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
                welcome_title=f"Aviso v. {VERSION} homepage",
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
                notification = self._parse_cloud_event(body)

                # send the notification
                self.notification_manager.notify(notification, config=self.config)
            except InvalidInputError as e:
                return bad_request(e)
            logger.debug("Notification successfully submitted")
            return ok("Notification successfully submitted")

        return handler

    def run_server(self):
        logger.debug(f"Running AVISO Frontend - version {VERSION} on server {self.config.frontend['server_type']}")
        logger.debug(f"Configuration loaded: {self.config}")

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

    def _parse_cloud_event(self, message) -> Dict[str, any]:
        """
        This helper method parses cloud event messagge, validate it and return the notification associated to it
        :param message: cloud event
        :return: notification as dictionary
        """
        try:
            # validate all mandatory fields
            assert "id" in message and message.get("id") is not None, "Invalid notification, 'id' could not be located"
            assert "source" in message and message.get("source") is not None, \
                "Invalid notification, 'source' could not be located"
            assert "specversion" in message and message.get("specversion") is not None, \
                "Invalid notification, 'specversion' could not be located"
            assert "type" in message and message.get("type") is not None, \
                "Invalid notification, 'type' could not be located"
            # extract the notification
            assert "data" in message and message.get("data") is not None, \
                "Invalid notification, 'data' could not be located"
            notification = message.get("data")
            assert "request" in notification and notification.get("request") is not None, \
                "Invalid notification, 'request' could not be located"
            req = notification.pop("request")
            for k, v in req.items():
                notification[k] = v
            return notification
        except AssertionError as e:
            raise InvalidInputError(e)


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
