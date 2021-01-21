# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum
from typing import Dict
import json

from ..custom_exceptions import  ServiceConfigException
from .. import logger

LISTENER_SCHEMA_FILE_NAME = "event_listener_schema.json"

class ListenerSchemaParserType(Enum):
    """
    This Enum describes the various notification mechanism currently available. This identifies the type of server
    this client is connecting to.
    """
    GENERIC = "ListenerSchemaParser"
    ECMWF =  "EcmwfSchemaParser"

    def parser(self):
        return eval(self.value + "()")


class ListenerSchemaParser:
    
    def load_event_listener_schema(self, schema_files):
        evl_schema_file_s = list(filter(lambda esf: LISTENER_SCHEMA_FILE_NAME in esf["key"], schema_files))
        if len(evl_schema_file_s) != 1:
            raise ServiceConfigException("No Event Listener schema file could be found to validate request")
        evl_schema_file = evl_schema_file_s[0]
        evl_schema = json.loads(evl_schema_file["value"].decode())

        return evl_schema

    def parse(self, schema_files, custom_listener_schema):
        evl_schema =  self.load_event_listener_schema(schema_files)

        # merge the schemas
        listener_schema = self.update_schema(evl_schema, custom_listener_schema)
        return listener_schema


    def update_schema(self, evl_schema, custom_schema: Dict = None) -> Dict[str, any]:
        """
        This method is used to update the aviso schema with values from the mars schema and the ones from the custom
        schema defined in the config file.
        :param evl_schema - this is the Event Listener schema to update
        :param custom_schema - this is a extra portion of schema defined in the configuration
        :return: aviso schema updated
        """
        # search for all the enum keys in all event listener types
        for e in evl_schema.items():
            if type(e[1]) == dict and e[1].get("request"):
                request = e[1].get("request")
                for k in request:
                    for t in request[k]:
                        if t["type"] == "EnumHandler":
                            # check the custom schema
                            if custom_schema:
                                if k in list(custom_schema.keys()):
                                    if type(custom_schema[k]) == list:
                                        for en in custom_schema[k]:
                                            t["values"].append(en)
                                    else:
                                        t["values"].append(custom_schema[k])
                logger.debug("Parsing completed")

        return evl_schema


class EcmwfSchemaParser (ListenerSchemaParser):

    MARS_SCHEMA_FILE_NAME = "language.json"
    
    def parse(self, schema_files, custom_listener_schema):

        # load event listener schema
        evl_schema = self.load_event_listener_schema(schema_files)
        
        # load mars schema
        mars_schema = self.load_mars_schema(schema_files)

        # merge the schemas
        listener_schema = self.update_schema(mars_schema, evl_schema, custom_listener_schema)
        return listener_schema

    def load_mars_schema(self, schema_files):
        mars_schema_file_s = list(filter(lambda mf: self.MARS_SCHEMA_FILE_NAME in mf["key"], schema_files))
        if len(mars_schema_file_s) != 1:
            raise ServiceConfigException("No MARS language file could be found to validate request")
        mars_schema_file = mars_schema_file_s[0]
        mars_schema = json.loads(mars_schema_file["value"].decode())

        return mars_schema

    def update_schema(self, mars_schema, evl_schema, custom_schema: Dict = None) -> Dict[str, any]:
        """
        This method is used to update the aviso schema with values from the mars schema and the ones from the custom
        schema defined in the config file.
        :param mars_schema - this is the MARS language schema
        :param evl_schema - this is the Event Listener schema to update
        :param custom_schema - this is a extra portion of schema defined in the configuration
        :return: aviso schema updated
        """
        # search for all the enum keys in all event listener types
        logger.debug("Parsing mars language schema...")
        for e in evl_schema.items():
            if type(e[1]) == dict and e[1].get("request"):
                request = e[1].get("request")
                for k in request:
                    for t in request[k]:
                        if t["type"] == "EnumHandler":
                            if not "values" in t:
                                t["values"] = []
                                # check the mars schema
                                mars_enums = mars_schema["_field"][k]["values"]
                                for me in mars_enums:
                                    if type(me) == list:
                                        for en in me:
                                            t["values"].append(en)
                                    else:
                                        t["values"].append(me)
                            # check the custom schema
                            if custom_schema:
                                if k in list(custom_schema.keys()):
                                    if type(custom_schema[k]) == list:
                                        for en in custom_schema[k]:
                                            t["values"].append(en)
                                    else:
                                        t["values"].append(custom_schema[k])
                logger.debug("Parsing completed")

        return evl_schema