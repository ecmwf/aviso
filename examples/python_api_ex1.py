# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pyaviso.notification_manager import NotificationManager


# define function to be called
def do_something(notification):
    print(f"Notification for step {notification['request']['step']} received")
    # now do something useful with it ...


# define the trigger
trigger = {"type": "function", "function": do_something}

# create a event listener request that uses that trigger
request = {"stream": "enfo", "date": 20190810, "time": 0}
listener = {"event": "mars", "request": request, "triggers": [trigger]}
listeners = {"listeners": [listener]}

# run it
aviso = NotificationManager()
aviso.listen(listeners=listeners)