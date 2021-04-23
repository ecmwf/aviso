# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import functools
import json
import sys

import click

from . import __version__, logger
from .cli_aviso import KNOWN_EXCEPTION, user_config_setup
from .service_config_manager import ServiceConfigManager
from .user_config import UserConfig

# main ServiceConfigManager object, we can use this for all commands

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def configuration_server_setup(f):
    @click.option("--host", "-H", help="Configuration server host.")
    @click.option("--port", "-P", help="Configuration server port.", type=int)
    @functools.wraps(f)
    def functor(*args, **kwargs):
        if kwargs["host"] is not None:
            kwargs["configuration"].configuration_engine.host = kwargs["host"]
        kwargs.pop("host")
        if kwargs["port"] is not None:
            kwargs["configuration"].configuration_engine.port = kwargs["port"]
        kwargs.pop("port")

        return f(*args, **kwargs)

    return functor


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
def cli():
    pass


@click.command(
    help="Push all files from the directory selected to the service defined, respecting the " "subdirectory structure."
)
@user_config_setup
@configuration_server_setup
@click.argument("service", required=True)
@click.option("--dir", "-D", help="Directory to push.", required=True)
@click.option("--message", "-m", help="Message to associate to the push.", required=True)
@click.option(
    "--delete", help="Allows delete of files on server if they don`t exist locally.", is_flag=True, default=False
)
def push(service: str, dir: str, message: str, delete: bool, configuration: UserConfig):
    config_manager = ServiceConfigManager(configuration)
    # call the push method of the ServiceConfigManager
    try:
        pushed_files = config_manager.push(service, dir, message, delete)
        for f in pushed_files:
            print(f)
        if len(pushed_files) > 0:
            logger.info(f"Push operation for service {service} successfully executed")
        else:
            logger.info(f"No file found to push for service {service}")

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while pushing the directory {dir} to the service {service}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


@click.command(help="Pull all files associated with the service defined.")
@user_config_setup
@configuration_server_setup
@click.argument("service", required=True)
@click.option("--dir", "-D", help="Directory to push.", default=".")
@click.option(
    "--delete", help="Allows delete of local files if they don`t exist on server.", is_flag=True, default=False
)
def pull(service: str, dir: str, delete: bool, configuration: UserConfig):
    config_manager = ServiceConfigManager(configuration)
    # call the pull_and_save method of the ServiceConfigManager
    try:
        pulled_files = config_manager.pull_and_save(service, dir, delete)
        for f in pulled_files:
            print(f)
        if len(pulled_files) > 0:
            logger.info(f"Pull operation for service {service} successfully executed")
        else:
            logger.info(f"No files found for service {service}")

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while pull the service {service}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


@click.command(help="Remove all files associated with the service defined.")
@user_config_setup
@configuration_server_setup
@click.argument("service", required=True)
@click.option("--doit", "-f", help="Remove without prompt.", is_flag=True, default=None)
def remove(service: str, doit: bool, configuration: UserConfig):
    config_manager = ServiceConfigManager(configuration)
    try:
        if not doit:
            # call the pull method of the ServiceConfigManager
            kvs = config_manager.pull(service, key_only=True)
            for kv in kvs:
                file_name = kv["key"]
                print(file_name)
            if len(kvs) > 0:
                logger.info("remove --doit to delete these files")
            else:
                logger.info(f"No files found for service {service}")
        else:  # delete all
            files_deleted = config_manager.remove(service)
            for f in files_deleted:
                print(f)
            if len(files_deleted) > 0:
                logger.info(f"Remove operation for service {service} successfully executed")
            else:
                logger.info(f"No files found for service {service}")

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while removing all files associated to the service {service}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


@click.command(help="Revert all files associated with the service defined to the previous version.")
@user_config_setup
@configuration_server_setup
@click.argument("service", required=True)
def revert(service: str, configuration: UserConfig):
    config_manager = ServiceConfigManager(configuration)
    # call the revert method of the ServiceConfigManager
    try:
        reverted_files = config_manager.revert(service)
        for f in reverted_files:
            print(f)
        if len(reverted_files) > 0:
            logger.info(f"Revert operation for service {service} successfully executed")
        else:
            logger.info(f"No files found for service {service}")

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while reverting the service {service}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


@click.command(help="Retrieve the status of the service defined.")
@user_config_setup
@configuration_server_setup
@click.argument("service", required=True)
def status(service: str, configuration: UserConfig):
    config_manager = ServiceConfigManager(configuration)
    # call the status method of the ServiceConfigManager
    try:
        s = config_manager.status(service)
        if s != {}:
            print(json.dumps(s, indent=4, sort_keys=True))

    except KNOWN_EXCEPTION as e:
        logger.error(f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)
    except Exception as e:
        logger.error(f"Error occurred while retrieving version for the service {service}, " f"{e}")
        logger.debug("", exc_info=True)
        sys.exit(-1)


cli.add_command(push)
cli.add_command(pull)
cli.add_command(remove)
cli.add_command(revert)
cli.add_command(status)

if __name__ == "__main__":
    cli()
