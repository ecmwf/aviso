# Aviso

Aviso is a notification application developed in Python. It allows users to:
* Define the events for which being notified.
* Define the triggers to be executed once a notification is received.
* Dispatch notifications to the notification server.

Moreover, Aviso can also be used to store and retrieve configuration files for various distributed services. In this 
case it acts as a configuration client application. 

These two functionalities, notification and configuration, share the same server technology and architecture, and 
therefore most of the user options. 
This page gives a quick introduction on the notification functionality only. 

For a detailed description of the notification functionality and of the configuration client application please 
refer to the [user manual](user_manual.md).

For information regarding the installation please refer to the [installation guide](install.md).

For information on how to contribute to the development and to the architectural design please refer to the [development 
guide](development.md).

## Quick start
Aviso can be used as a Python API or as Command-Line Interface (CLI) application.

Here a few steps to quickly get a working configuration listening to notifications. Note that Aviso is a client 
application, this assumes that a notification server is already up and running.

1. Create a configuration file in the default location _~/.aviso/config.yaml_ with the following settings:
    ```
    listeners:
      - event: dissemination
        request:
          destination: FOO
          stream: enfo
          step: [1,2,3]
        triggers:
          - type: echo
    ```
    This file defines the event listeners and the triggers to execute 
    in case of notifications. This is a basic example of a `dissemination` event listener. `request` describes for 
    which dissemination events the user wants to execute the triggers. It is made by a list of attributes. The users 
    have to specify only the attributes that they wants to use as filters. Only the notifications complying with all the 
    attributes defined will execute the triggers. 
    
    The trigger in this example is `echo`. This will simply print out the notification to the console output.
    
1. Save the ECMWF key in _/etc/aviso/key_. The key can be obtained by logging at https://api.ecmwf.int/v1/key/ . A 
different location can be defined in the configuration file above described. 
More information are available in the [user manual](user_manual.md).

1. Launch the aviso application
    ```
    $ aviso listen
    ``` 
    Once in execution this command will create a process waiting for notifications.
    
    The user can terminate the application by typing
    ```
    $ CTRL+C, CTRL+D, CTRL+\
    ```
    
    Note that before starting to listen for new notifications, the application checks what was the last notification 
    received and it will then return immediately all the notifications that have been missed since. It will then start 
    listening for new ones. The first ever time the application runs however no previous notification will be returned. 


## Submitting test notifications
Aviso provides the capability of submitting notifications. This functionality can be used by the user to test the 
listener configuration. 

1. Terminate the aviso application and edit the following setting of the configuration file _~/.aviso/config.yaml_
   ```
   notification_engine:
     type: test 
   ```
   This setting allows to connect to a local file-based notification server, part of the aviso application, that is 
   able to simulate the notification server behaviour.
   
   Alternatively, the user can add the `--test` option to all the commands below.
   
1. Launch again the aviso application.
    ```
    $ aviso listen
    ```
    The console should display a `Test Mode` message.
    
1. Send notifications. From another terminal run the `notifiy` command. Here an example:
    ```
    $ aviso notify event=dissemination,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0,location=xxxxxxxx
    ```
    Note the list of parameters required, the order is not important, but the command requires all of them.
    
1. The console output should display the notification.


## Using Aviso as a Python API
Aviso can be used as a Python API. This is intended for user that wants to integrate Aviso in a bigger workflow written 
in Python or that simply have their trigger defined as a Python function. 
Below an example of a python script that defines a function to be executed once a notification is received, creates a 
listener that references to this function trigger and finally passes it to aviso to execute. 

The listening will happen in a background thread defined as daemon therefore it is responsibility of the user to keep 
the main thread alive.

Please note that the user configuration has not been defined in this example, the system will automatically read the
configuration file defined above.
```
from pyaviso.notification_manager import NotificationManager

# define function to be called
def do_something(notification):
    # do something with the notification
    ...

# define the trigger
trigger = {"type": "function", "function": do_something}

# create a event listener request that uses that trigger
request = {"destination": "FOO", "stream": "enfo", "date": 20190810, "time": 0}
listener = {"event": "dissemination", "request": request, "triggers": [trigger]}
listeners = {"listeners": [listener]}

# run it
aviso = NotificationManager()
aviso.listen(listeners=listeners)

# wait ...
```