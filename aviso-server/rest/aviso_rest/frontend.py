from typing import Dict

import uvicorn
from aviso_monitoring import __version__ as monitoring_version
from aviso_monitoring.collector.time_collector import TimeCollector
from aviso_monitoring.reporter.aviso_rest_reporter import AvisoRestMetricType
from aviso_rest import __version__, logger
from aviso_rest.config import Config
from cloudevents.http import from_http
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from pyaviso.custom_exceptions import InvalidInputError
from pyaviso.notification_manager import NotificationManager
from pyaviso.version import __version__ as aviso_version

app = FastAPI()


class Frontend:
    """Frontend service class to handle API requests and initialize application components."""

    def __init__(self, config: Config):
        """
        Initializes the frontend service with the given configuration.

        :param config: Configuration object for the service.
        """
        self.config = config
        self.notification_manager = NotificationManager()
        # Timer initialization is moved to an app startup event.

    def init_timer(self):
        """Initializes a global timer for the application."""
        self.timer = TimeCollector(self.config.monitoring, tlm_type=AvisoRestMetricType.rest_resp_time.name)

    async def _parse_cloud_event(self, req: Request) -> Dict:
        """
        Parses a cloud event from the request.

        :param req: Request object containing the cloud event.
        :return: A dictionary representation of the notification.
        :raises InvalidInputError: If the cloud event is invalid.
        """
        try:
            cloudevents = from_http(req.headers, await req.body())
            assert cloudevents.data is not None, "Invalid notification, 'data' could not be located"
            notification = cloudevents.data
            assert notification.get("event") is not None, "Invalid notification, 'event' could not be located"
            assert notification.get("request") is not None, "Invalid notification, 'request' could not be located"
            r = notification.pop("request")
            notification.update(r)
            return notification
        except Exception as e:
            raise InvalidInputError(str(e))

    def _skip_request(self, notification: Dict, skips: Dict) -> bool:
        """
        Determines whether a notification should be skipped based on configuration.

        :param notification: The notification to check.
        :param skips: A dictionary of conditions for skipping notifications.
        :return: True if the notification should be skipped, False otherwise.
        """
        for s in skips:
            if s in notification and notification[s] in skips[s]:
                return True
        return False

    def run_server(self):
        logger.info(
            f"Running AVISO Frontend - version {__version__} with Aviso version {aviso_version}, "
            f"aviso_monitoring module v.{monitoring_version} on server {self.config.server_type}"
        )
        logger.info(f"Configuration loaded: {self.config}")

        if self.config.server_type == "uvicorn":
            uvicorn.run(
                "aviso_rest.frontend:app",
                host=self.config.host,
                port=self.config.port,
                log_level="info" if self.config.debug else "warning",
            )
        else:
            logger.error(f"server_type {self.config.server_type} not supported")
            raise NotImplementedError


config = Config()
frontend = Frontend(config)


@app.on_event("startup")
async def startup_event():
    """Event handler for application startup."""
    frontend.init_timer()
    logger.info("Application startup: Timer initialized.")


@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception):
    """Handles unexpected exceptions globally."""
    logger.exception(f"Request raised the following error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Server error occurred", "details": str(exc)},
    )


@app.exception_handler(InvalidInputError)
async def invalid_input_exception_handler(request: Request, exc: InvalidInputError):
    """Handles invalid input exceptions, returning a 400 error."""
    logger.error(f"Invalid input error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serves the homepage."""
    with open("aviso_rest/web/index.html") as fh:
        content = fh.read()
    return content.format(
        page_title="Aviso",
        welcome_title=f"Aviso v. {__version__} homepage",
        welcome_text="This is the RESTful frontend of the Aviso notification system",
    )


@app.post("/api/v1/notification")
async def api_notify(request: Request):
    """
    Receives notifications and processes them accordingly.

    :param request: The incoming HTTP request with the notification.
    :return: A JSON response indicating the result of the notification processing.
    """
    logger.debug("New notification received")
    body = await request.json()
    if body is None:
        raise HTTPException(status_code=400, detail="Invalid notification, Body cannot be empty")
    logger.debug(body)
    try:
        notification = await frontend._parse_cloud_event(request)
        logger.info(f"New event received: {notification}")
        if frontend._skip_request(notification, frontend.config.skips):
            logger.info("Notification skipped")
            return {"message": "Notification skipped"}
        # Implement the notification logic here.
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("Notification successfully submitted")
    return {"message": "Notification successfully submitted"}


def main():
    # create the frontend class and run it
    frontend.run_server()


if __name__ == "__main__":
    main()
