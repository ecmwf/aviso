# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Example of python script triggered by a Command trigger
"""
import os
print('Test demonstrating a python script triggered by a Command trigger')
# noinspection PyUnresolvedReferences
print(f"Notification received at {os.environ['TIME']} for step {os.environ['STEP']}")
