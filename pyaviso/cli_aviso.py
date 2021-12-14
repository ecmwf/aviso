# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import functools
import signal
import sys
import threading
import time
from typing import Dict, List

import click

from pyaviso import __version__, logger
from pyaviso import user_config as conf
from pyaviso.custom_exceptions import (
    EngineException,
    EventListenerException,
    InvalidInputError,
    TriggerException,
)
from pyaviso.engine import EngineType
from pyaviso.notification_manager import NotificationManager
from pyaviso.service_config_manager import ServiceConfigException

# Create the listener manager
manager: NotificationManager = NotificationManager()

# set of known exceptions
KNOWN_EXCEPTION = (
    ServiceConfigException,
    EventListenerException,
    TriggerException,
    EngineException,
    InvalidInputError,
    AssertionError,
    KeyError,
)


def catch_all_exceptions(cls, handler):
    """
    This function is used to pass a child of the click.command class to the click CLI initialisation.
    This new class overrides the default error handling by allowing to intercept keyboard interruption and EOF errors.
    :param cls: click.command
    :param handler: function in charge of error handling
    :return:
    """

    class Cls(cls):

        _original_args = None

        def make_context(self, info_name, args, parent=None, **extra):

            # grab the original command line arguments
            self._original_args = " ".join(args)

            try:
                return super(Cls, self).make_context(info_name, args, parent=parent, **extra)
            except Exception:
                # call the handler
                handler()

                # let the user see the original error
                raise

        def invoke(self, ctx):
            try:
                return super(Cls, self).invoke(ctx)
            except Exception:
                # call the handler
                handler()

                # let the user see the original error
                raise

    return Cls


def ignore_signal(signum, frame):
    """
    This is used to ignore a specific signal sent to this process
    :param signum:
    :param frame:
    :return:
    """
    pass


def ignore_signal_and_sleep(signum, frame, time_sec=0.1):
    """
    This is used to ignore and sleep when a specific signal is sent to this process.
    The sleep is required when the signal is sent multiple times like the SIGTTIN in case of CLICK running in the
    background and trying to read from the stdin.
    :param time_sec: time in second to sleep
    :param signum:
    :param frame:
    :return:
    """
    time.sleep(time_sec)


def stop_listeners(signum=None, frame=None):
    """
    This function takes care of gracefully stopping the listeners.
    :param signum:
    :param frame:
    :return:
    """
    # Stop gracefully the notification listeners
    try:
        logger.debug("Stopping listeners...")
        manager.listener_manager.cancel_listeners()
        logger.info("Listeners stopped")
    except Exception as e:
        logger.error(f"Error while stopping the listeners, {e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


def stop_listeners_and_exit(signum=None, frame=None):
    """
    This function takes care of gracefully stopping the listeners and then exit
    propagates the exception.
    :param signum:
    :param frame:
    :return:
    """
    # Stop gracefully the notification listeners and exit
    stop_listeners()
    sys.exit()


def notification_server_setup(f):
    @click.option("--host", "-H", help="Notification server host.")
    @click.option("--port", "-P", help="Notification server port.", type=int)
    @click.option("--test", help="Activate TestMode.", is_flag=True, default=False)
    @functools.wraps(f)
    def functor(*args, **kwargs):
        if kwargs["host"]:
            kwargs["configuration"].notification_engine.host = kwargs["host"]
        kwargs.pop("host")
        if kwargs["port"]:
            kwargs["configuration"].notification_engine.port = kwargs["port"]
        kwargs.pop("port")
        if kwargs["test"]:
            kwargs["configuration"].notification_engine.type = EngineType.FILE_BASED
        kwargs.pop("test")

        return f(*args, **kwargs)

    return functor


def user_config_setup(f):
    @click.option("--config", "-c", help="User configuration file path.")
    @click.option("--log", "-l", help="Logging configuration file path.")
    @click.option("--debug", "-d", help="Enable the debug log.", is_flag=True, default=False)
    @click.option(
        "--quiet", "-q", help="Suppress non-error messages from the console output.", is_flag=True, default=False
    )
    @click.option("--no-fail", help="Suppress any error exit code.", is_flag=True, default=False)
    @click.option("--username", "-u", help="Username required to authenticate to the server.")
    @click.option("--key", "-k", help="File path to the key required to authenticate to the server.")
    @functools.wraps(f)
    def functor(*args, **kwargs):
        # CLIK automatically sets the flags, put back None values like for the other parameters
        kwargs["debug"] = None if not kwargs["debug"] else True
        kwargs["quiet"] = None if not kwargs["quiet"] else True
        kwargs["no_fail"] = None if not kwargs["no_fail"] else True

        # create the configuration object
        configuration = conf.UserConfig(
            conf_path=kwargs["config"],
            logging_path=kwargs["log"],
            debug=kwargs["debug"],
            quiet=kwargs["quiet"],
            no_fail=kwargs["no_fail"],
            username=kwargs["username"],
            key_file=kwargs["key"],
        )

        # pass it as a option in the same dictionary but remove the fields used for the configuration
        kwargs["configuration"] = configuration
        kwargs.pop("config")
        kwargs.pop("log")
        kwargs.pop("debug")
        kwargs.pop("quiet")
        kwargs.pop("no_fail")
        kwargs.pop("username")
        kwargs.pop("key")

        logger.debug(f"Running Aviso v.{__version__}")
        logger.debug(f"Configuration loaded: {configuration}")

        return f(*args, **kwargs)

    return functor


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
def cli():
    pass


@click.command(cls=catch_all_exceptions(click.Command, handler=stop_listeners), context_settings=CONTEXT_SETTINGS)
@user_config_setup
@notification_server_setup
@click.argument("listener_files", nargs=-1)
@click.option(
    "--from",
    "from_date",
    type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S.%fZ"]),
    help="Replay notification from this date.",
)
@click.option(
    "--to", "to_date", type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S.%fZ"]), help="Replay notification to this date."
)
@click.option("--now", "now", is_flag=True, default=False, help="Ignore missed notifications, only listen to new ones.")
@click.option("--catchup", "catchup", is_flag=True, default=False, help="Retrieve first the missed notifications.")
def listen(listener_files: List[str], configuration: conf.UserConfig, from_date, to_date, now, catchup):
    """
    This method allows the user to execute the listeners defined in the YAML listener file

    :param listener_files: YAML files used to define the listeners
    """
    try:
        """
        UNIX Signal handling
        """

        if threading.current_thread() is threading.main_thread():
            # This is needed to avoid the process to be suspended in case it runs in background, we must sleep
            # because we constantly read from the stdin
            signal.signal(signal.SIGTTIN, ignore_signal_and_sleep)
            # this is sent with CTRL + \
            signal.signal(signal.SIGQUIT, stop_listeners_and_exit)
            # this is sent whit the default kill command
            signal.signal(signal.SIGTERM, stop_listeners_and_exit)

        # call the main listen method
        manager.listen(
            configuration,
            listeners_file_paths=listener_files,
            from_date=from_date,
            to_date=to_date,
            now=now,
            catchup=catchup,
        )

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        stop_listeners()
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while running the listeners: {e}")
        logger.debug("", exc_info=True)
        stop_listeners()
        sys.exit(-1)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("parameters", required=True)
@user_config_setup
@notification_server_setup
def key(parameters: str, configuration: conf.UserConfig):
    """
    Generate the key to send to the notification server according to the current schema using the parameters defined

    :param parameters: key1=value1,key2=value2,...
    """

    try:
        parsed_param = _parse_inline_params(parameters)
        # base_key and maintenance are ignored because not needed here
        key_generated, base_key, maintenance = manager.key(parsed_param, configuration)
        print(key_generated)

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while generating key from {parameters}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("parameters", required=True)
@user_config_setup
@notification_server_setup
def value(parameters: str, configuration: conf.UserConfig):
    """
    Return the value on the server corresponding to the key which is generated according to the current schema and
    the parameters defined

    :param parameters: key1=value1,key2=value2,...
    """

    try:
        parsed_param = _parse_inline_params(parameters)
        v = manager.value(parsed_param, configuration)
        print(v)

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while return value for {parameters}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("parameters", required=True)
@user_config_setup
@notification_server_setup
def notify(parameters: str, configuration: conf.UserConfig):
    """
    Create a notification with the parameters passed and submit it to the notification server
    :param parameters: key1=value1,key2=value2,...
    """

    try:
        parsed_param = _parse_inline_params(parameters)
        manager.notify(parsed_param, config=configuration)
        print("Done")

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while notifying the notification {parameters}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


cli.add_command(listen)
cli.add_command(key)
cli.add_command(value)
cli.add_command(notify)

if __name__ == "__main__":
    listen()


def _parse_inline_params(params: str) -> Dict[str, any]:
    """
    This helper method parses the notification string in a dictionary
    :param params:
    :return: notification as dictionary
    """
    logger.debug("Parsing the inline parameters...")
    parsed_param = {}
    ps = params.split(",")
    assert len(ps) > 1, "Wrong structure for the notification string, it should be <key_name>=<key_value>,..."
    for p in ps:
        pair = p.split("=")
        assert len(pair) == 2, "Wrong structure for the notification string, it should be <key_name>=<key_value>,..."
        parsed_param[pair[0]] = pair[1]
    logger.debug("Notification string successfully parsed")
    return parsed_param
