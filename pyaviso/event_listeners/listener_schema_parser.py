# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import os
from enum import Enum
from typing import Dict

from .. import HOME_FOLDER, SYSTEM_FOLDER, logger
from ..custom_exceptions import ServiceConfigException

LOCAL_SCHEMA_FOLDER = "service_configuration"
LISTENER_SCHEMA_FILE_NAME = "event_listener_schema.json"
DEFAULT_SCHEMA_FILE_NAME = "default_listener_schema.json"


class ListenerSchemaParserType(Enum):
    """
    This Enum describes the various notification mechanism currently available. This identifies the type of server
    this client is connecting to.
    """

    GENERIC = "ListenerSchemaParser"
    ECMWF = "EcmwfSchemaParser"

    def parser(self):
        return eval(self.value + "()")


class ListenerSchemaParser:
    def load(self, config):
        """
        This method implements the workflow regarding loading the listener schema file
        from a remote location or local location or default.

        Args:
            config (UserConfig): main configuration

        Returns:
            Dict: Event Listener schema
        """
        logger.debug("Updating schema configurations...")
        local_schema_file_paths = []
        remote_schema_files = []
        if config.remote_schema:
            # Pull the latest event listeners configuration files
            from ..service_config_manager import ServiceConfigManager

            config_manager = ServiceConfigManager(config)
            remote_schema_files = config_manager.pull(config.notification_engine.service)
        else:
            # First the system config file
            system_path = os.path.join(SYSTEM_FOLDER, LOCAL_SCHEMA_FOLDER)
            # Check the directory exist
            if not os.path.exists(system_path):
                local_schema_file_paths = self._scan_folder(system_path)
            else:
                logger.debug(f"Schema folder in {system_path} not found")

            # Second the Home config file
            home_path = os.path.join(os.path.expanduser(HOME_FOLDER), LOCAL_SCHEMA_FOLDER)
            # Check the directory exist
            if os.path.exists(home_path):
                local_schema_file_paths = self._scan_folder(home_path)
            else:
                logger.debug(f"Schema folder in {home_path} not found")

        # parse the file loaded
        return self.parse(local_schema_file_paths, remote_schema_files)

    def _scan_folder(self, directory):
        files = []
        for x in os.walk(directory):
            for fp in x[2]:
                files.append(os.path.join(directory, fp))
        return files

    def _load_default_schema(self):
        default_path = os.path.join(os.path.dirname(__file__), DEFAULT_SCHEMA_FILE_NAME)
        with open(default_path) as evl_json:
            evl_schema = json.load(evl_json)
        return evl_schema

    def _load_event_listener_schema(self, local_schema_file_paths, remote_schema_files):
        # first check if we have remote schema. This takes priority
        if len(remote_schema_files) == 0:
            logger.debug("No remote schema file found")

            # then check if we have local schema
            if len(local_schema_file_paths) == 0:
                logger.warning("Not local listener schema file found, using default schema")
                # load the default schema
                evl_schema = self._load_default_schema()
            else:
                # search for the schema in the local folder
                evl_schema_file_path = list(
                    filter(lambda esfp: LISTENER_SCHEMA_FILE_NAME in esfp, local_schema_file_paths)
                )
                if len(evl_schema_file_path) != 1:
                    raise ServiceConfigException("No local event listener schema file found")
                with open(evl_schema_file_path[0]) as evl_json:
                    evl_schema = json.load(evl_json)
        else:
            # search for the schema among the remote schema
            evl_schema_file_s = list(filter(lambda esf: LISTENER_SCHEMA_FILE_NAME in esf["key"], remote_schema_files))
            if len(evl_schema_file_s) != 1:
                raise ServiceConfigException("No remote event listener schema file found")
            evl_schema_file = evl_schema_file_s[0]
            evl_schema = json.loads(evl_schema_file["value"].decode())

        return evl_schema

    def parse(self, local_schema_file_paths, remote_schema_files):
        """
        This methods takes all schema files found and parse them to create the final schema file.
        Custom parser should re-implement this method.

        Args:
            local_schema_file_paths (List): List of file paths to the
            remote_schema_files (List): [description]

        Returns:
            Dict: Event Listener schema
        """
        evl_schema = self._load_event_listener_schema(local_schema_file_paths, remote_schema_files)

        return evl_schema


class EcmwfSchemaParser(ListenerSchemaParser):
    MARS_SCHEMA_FILE_NAME = "language.json"

    def parse(self, local_schema_file_paths, remote_schema_files):
        """
        This re-implements the parent parse method to include the enum values from the MARS language schema
        """

        # load event listener schema
        evl_schema = self._load_event_listener_schema(local_schema_file_paths, remote_schema_files)

        # load mars schema
        mars_schema = self._load_mars_schema(remote_schema_files)

        # merge the schemas
        listener_schema = self._update_schema(mars_schema, evl_schema)
        return listener_schema

    def _load_mars_schema(self, schema_files):
        mars_schema_file_s = list(filter(lambda mf: self.MARS_SCHEMA_FILE_NAME in mf["key"], schema_files))
        if len(mars_schema_file_s) != 1:
            raise ServiceConfigException("No MARS language schema file found")
        mars_schema_file = mars_schema_file_s[0]
        mars_schema = json.loads(mars_schema_file["value"].decode())

        return mars_schema

    def _update_schema(self, mars_schema, evl_schema) -> Dict[str, any]:
        """
        This method is used to update the aviso schema with values from the mars schema and the ones from the custom
        schema defined in the config file.
        :param mars_schema - this is the MARS language schema
        :param evl_schema - this is the Event Listener schema to update
        :return: aviso schema updated
        """
        # search for all the enum keys in all event listener types and add the mars values to it
        logger.debug("Parsing mars language schema...")
        for e in evl_schema.items():
            if type(e[1]) == dict and e[1].get("request"):
                request = e[1].get("request")
                for k in request:
                    for t in request[k]:
                        if t["type"] == "EnumHandler":
                            if "values" not in t:
                                t["values"] = []
                            # check the mars schema
                            mars_enums = mars_schema["_field"][k]["values"]
                            for me in mars_enums:
                                if type(me) == list:
                                    for en in me:
                                        t["values"].append(en)
                                else:
                                    t["values"].append(me)
                logger.debug("Parsing completed")

        return evl_schema
