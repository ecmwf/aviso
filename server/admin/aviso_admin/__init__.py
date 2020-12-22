# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging

# version number for the application.
__version__ = '0.2.0'

# setting application logger
logger = logging.getLogger("aviso-admin")
logger.setLevel(logging.DEBUG)

# home folder for configuration, state and log
HOME_FOLDER = "~/.aviso-admin"

# system folder for configuration
SYSTEM_FOLDER = "/etc/aviso-admin"
