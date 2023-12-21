# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import time

import schedule
from aviso_admin import __version__, logger
from aviso_admin.cleaner import Cleaner
from aviso_admin.compactor import Compactor
from aviso_admin.config import Config
from aviso_monitoring import __version__ as monitoring_version
from aviso_monitoring.receiver import Receiver
from aviso_monitoring.reporter.aviso_auth_reporter import AvisoAuthReporter
from aviso_monitoring.reporter.aviso_rest_reporter import AvisoRestReporter
from aviso_monitoring.reporter.etcd_reporter import EtcdReporter
from aviso_monitoring.reporter.prometheus_reporter import PrometheusReporter
from aviso_monitoring.udp_server import UdpServer


def setup_compactor_and_cleaner(config):
    """Sets up the compactor and cleaner with scheduling."""
    compactor = Compactor(config.compactor)
    if compactor.enabled:
        schedule.every().day.at(config.compactor["scheduled_time"]).do(compactor.run)

    cleaner = Cleaner(config.cleaner)
    if cleaner.enabled:
        schedule.every().day.at(config.cleaner["scheduled_time"]).do(cleaner.run)


def setup_udp_server(config, receiver):
    """Initializes and starts the UDP server."""
    try:
        udp_server = UdpServer(config.monitoring.udp_server, receiver)
        udp_server.start()
        return udp_server
    except Exception as e:
        logger.exception("Failed to start UDP Server: %s", e)


def schedule_reporters(config, receiver):
    """Schedules various reporters based on the configuration."""
    for reporter_class in [AvisoRestReporter, AvisoAuthReporter, EtcdReporter]:
        reporter = reporter_class(config.monitoring, receiver)
        if reporter.enabled:
            schedule.every(reporter.frequency).minutes.do(reporter.run)


def start_prometheus_reporter(config, receiver):
    """Starts the Prometheus reporter if enabled."""
    prometheus_reporter = PrometheusReporter(config.monitoring, receiver)
    if prometheus_reporter.enabled:
        prometheus_reporter.start()


def main():
    """Main function to run the application."""
    # Load the configuration
    config = Config()
    logger.info(f"Running Aviso-admin v.{__version__}")
    logger.info(f"aviso_monitoring module v.{monitoring_version}")
    logger.debug(f"Configuration loaded: {config}")

    # Set up compactor and cleaner
    setup_compactor_and_cleaner(config)

    # Create the UDP server
    receiver = Receiver()
    udp_server = setup_udp_server(config, receiver)

    # Schedule reporters
    schedule_reporters(config, receiver)

    # Start Prometheus reporter
    start_prometheus_reporter(config, receiver)

    # Main loop for running scheduled tasks
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Application stopped by user.")
    except Exception as e:
        logger.exception("Unexpected error occurred: %s", e)
    finally:
        if udp_server:
            udp_server.stop()  # Assuming a method to gracefully stop the UDP server
        logger.info("Application shutdown.")


if __name__ == "__main__":
    main()
