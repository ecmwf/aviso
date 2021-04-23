# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import subprocess
from typing import Dict

from .. import logger
from ..custom_exceptions import TriggerException
from . import trigger
from .trigger import TriggerType


class CommandTrigger(trigger.Trigger):
    """
    This class implements the 'Shell' trigger by executing an external shell script defined by the user.
    This class expects the params to contain the path of the script to run.
    Moreover this classes passes all the arguments defined together with NOTIFICATION_KEY and NOTIFICATION_VALUE as
    local variables.
    """

    def __init__(self, notification: Dict[str, any], params: Dict[str, any]):
        trigger.Trigger.__init__(self, notification, params)
        assert params.get("command") is not None, "command is a mandatory field"
        self.command: str = params.get("command")
        self.trigger_type = TriggerType.command

    def execute(self):
        logger.info("Starting Command Trigger...'")

        # prepare the variables passed as local variables
        my_env = os.environ.copy()  # don't change the caller environment
        if "environment" in self.params:
            envs = self.params.get("environment")
            for k in envs.keys():
                my_env[k] = self.replace_template(envs[k])

        # prepare command
        final_command = self.replace_template(self.command)
        # add working dir
        if "working_dir" in self.params:
            final_command = "cd " + self.params.get("working_dir") + ";" + final_command

        # create an independent process for the command
        logger.debug(f"Calling command {final_command}...")
        out = subprocess.Popen(final_command, env=my_env, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        # log the results
        stdout, stderr = out.communicate()
        if stdout is not None and stdout.decode() != "":
            logger.info(stdout.decode())
        if stderr is not None and stderr.decode() != "":
            raise TriggerException(stderr.decode())

        logger.debug("Command Trigger completed")
