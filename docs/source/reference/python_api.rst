.. _python_api_ref:

Python API
==========
Aviso provides a Python API for the key operations that concern the notification workflow: ``listen`` and ``notify``.
This API has the same level of expressiveness as the CLI. Moreover users can create and customise a ``user_config.UserConfig`` object.
This object allows to programmatically define any setting described in in :ref:`configuration`.

This is intended for users that want to integrate Aviso in a workflow or application
written in Python. An example of integration of Aviso in a external Python application is the server component **Aviso REST**, 
described in :ref:`aviso_server`.
This component internally relies on Aviso client to submit notification to the store.


Listen
------
This method is used to start the polling for changes from Aviso client to Aviso server. This allows the user to retrieve new notifications as they are submitted to Aviso server.

Below is an example of a python script that defines a function to be executed once a notification is received, creates a listener that references to this function trigger and finally passes it to Aviso to execute.

.. code-block:: python

   from pyaviso import NotificationManager

   # define function to be called
   def do_something(notification):
      print(f"Notification for step {notification['request']['step']} received")
      # now do something useful with it ...

   # define the trigger
   trigger = {"type": "function", "function": do_something}

   # create a event listener request that uses that trigger
   request = {"key1": "value1", "key2": "20210101", "key3": "a"}
   listeners = {"listeners": [{"event": "generic1", "request": request, "triggers": [trigger]}]}

   # run it
   aviso = NotificationManager()
   aviso.listen(listeners=listeners)

This script will put the main process is busy waiting while polling at regular time the server.
All the various types of triggers presented in :ref:`triggers` can also be defined or manually loaded from file.

The object ``NotificationManager`` can take as parameter a ``UserConfig`` object that the user can create and customise. If not passed the manager object will instantiate a config object that follows the criteria explained in :ref:`configuration`. This example shows the latter, moreover, it using the generic listener schema presented in :ref:`getting_started`.


Notify
------
This method is used to submit notification. 
The example belows shows how to send a generic notification compliant with the generic listener schema presented in :ref:`getting_started`

.. code-block:: python

   from pyaviso import NotificationManager

   aviso = NotificationManager()

   # define the parameters of the notification
   notification = {
      "event":"generic1",
      "key1": "value1",
      "key2": "20210101", 
      "key3": "a", 
      "location": "xxx", 
   }

   # send the notification
   aviso.notify(notification)
