# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from ecmwfapi import ECMWFService

from pyaviso.notification_manager import NotificationManager


# define function to be called
def retrieve_from_mars(notification):
    print(f"Notification for step {notification['request']['step']} received")
    # now do a MARS request with this notification...
    mars_server = ECMWFService("mars")
    request = notification['request']
    # extend the notification with the attributes needed
    request.update({
        "type": "fc",
        "levtype": "sfc",
        "param": 167.128,
        "area": "75/-20/10/60"
    })
    mars_server.execute(request, "my_data.grib")


# define the trigger
trigger = {"type": "function", "function": retrieve_from_mars}

# create a event listener request that uses that trigger
request = {"class": "od", "stream": "oper", "expver": 1, "domain": "g", "step": 1}
listener = {"event": "mars", "request": request, "triggers": [trigger]}
listeners = {"listeners": [listener]}

# run it
aviso = NotificationManager()
aviso.listen(listeners=listeners)
