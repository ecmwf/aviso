.. _python_api_guide:

Aviso as a Python API
=====================

Aviso can be used as a Python API. This is intended for users that want to integrate Aviso in a bigger workflow written in Python or that simply have their trigger 
defined as a Python function. Below find an example of a python script that defines a function to be executed once a notification is received, 
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
   request = {"class": "od", "stream": "oper", "expver": 1, "domain": "g", "step": 1}
   listeners = {"listeners": [{"event": "mars", "request": request, "triggers": [trigger]}]}

   # run it
   aviso = NotificationManager()
   aviso.listen(listeners=listeners)

.. note::
   The example is assuming the default configuration file ~/aviso/config.yaml is defined for authentication purposes as explained in :ref:`getting_started`.