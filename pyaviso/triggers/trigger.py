# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import importlib
import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict

TEMPLATE = r"\${[\w|\.]+}"
JSON_FOLDER = "/tmp/aviso"


class TriggerType(Enum):
    """
    Enum for the various triggers accepted by the system
    """

    log = ("log_trigger", "LogTrigger")
    function = ("function_trigger", "FunctionTrigger")
    command = ("command_trigger", "CommandTrigger")
    echo = ("echo_trigger", "EchoTrigger")
    post = ("post_trigger", "PostTrigger")

    def get_class(self):
        module = importlib.import_module("pyaviso.triggers." + self.value[0])
        return getattr(module, self.value[1])


class Trigger(ABC):
    """
    This class is an abstract class providing:
        - a common abstraction for the various type of triggers
    """

    def __init__(self, notification: Dict[str, any], params: Dict[str, any]):
        """
        :param notification: dictionary containing the attributes characterising a notification
        :param params: dictionary containing the attributes characterising the trigger as defined in the listener
        """
        self._params = params
        self._notification = notification

    @property
    def notification(self) -> Dict[str, any]:
        return self._notification

    @property
    def params(self) -> Dict[str, any]:
        return self._params

    @abstractmethod
    def execute(self):
        """
        Abstract method called by the thread in the run() method. This forces any child class to implement
        what is required for the execution of the specific trigger through a common interface.
        """
        pass

    def replace_template(self, text: str) -> str:
        """
        This method scans the text as input looking for the template pattern and replace it each match with the relative
        parameter taken from the notification dictionary
        :param text:
        :return:
        """
        matches = re.findall(TEMPLATE, text)
        for match in matches:
            assert len(match) > 3, "Wrong format for the variable templating, variable name must be specified"
            variable = match[2 : (len(match) - 1)]
            sub_pattern = f"\\{match}"
            if variable == "json":  # special case where we dump the whole notification dictionary
                json_dump = f"'{json.dumps(self.notification)}'"
                text = re.sub(sub_pattern, json_dump, text)
            elif variable == "jsonpath":  # special case where we save the notification dictionary to a json file
                if not os.path.exists(JSON_FOLDER) and not os.path.isdir(JSON_FOLDER):
                    os.makedirs(JSON_FOLDER, exist_ok=True)  # create folder first
                dtime = datetime.now().__str__().replace(" ", "")
                file_name = f"{JSON_FOLDER}/{dtime}.json"
                with open(file_name, "w") as file:
                    file.write(json.dumps(self.notification))
                text = re.sub(sub_pattern, file_name, text)
            else:
                # the variable may contain namespaces inside our nested dictionary
                split_variable = variable.split(".")
                string_to_eval = "self.notification"
                for v in split_variable:
                    string_to_eval += f"['{v}']"
                text = re.sub(sub_pattern, eval(string_to_eval), text)

        return text
