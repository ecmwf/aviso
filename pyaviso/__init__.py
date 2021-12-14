# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
from queue import Queue

from .version import __version__  # noqa: F401

# setting application logger - this goes before anything else
logger = logging.getLogger("aviso")
logger.setLevel(logging.DEBUG)

# home folder for configuration, state and log
HOME_FOLDER = "~/.aviso"

# system folder for configuration
SYSTEM_FOLDER = "/etc/aviso"

# This is a thread-safe communication channel. It is used to tell the main thread when to terminate.
exit_channel = Queue()

from .notification_manager import NotificationManager  # noqa: F401, E402
