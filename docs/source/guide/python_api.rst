.. _python_api_guide:

Aviso as a Python API
=====================

Aviso can be used as a Python API. This is intended for users that want to integrate Aviso in a bigger workflow written in Python or that simply have their trigger 
defined as a Python function. Below find an example of a Python script that defines a function to be executed once a notification is received, 
creates a listener that references this function trigger and finally passes it to aviso to execute.

.. code-block:: python

   from pyaviso import NotificationManager

   # define function to be called
   def do_something(notification):
      print(f"Notification for step {notification['request']['step']} received")
      # now do something useful with it ...

   # define the trigger
   trigger = {"type": "function", "function": do_something}

   # create a event listener request that uses that trigger
   request = {"country": "italy"}
   listeners = {"listeners": [{"event": "flight", "request": request, "triggers": [trigger]}]}

   # run it
   aviso = NotificationManager()
   aviso.listen(listeners=listeners)

.. note::
   This example is using the default configuration file in `~/aviso/config.yaml` and the generic listener schema presented in :ref:`getting_started`. Alternatively, a configuration object can be passed to the `NotificationManager`.

See :ref:`python_api_ref` for more info.