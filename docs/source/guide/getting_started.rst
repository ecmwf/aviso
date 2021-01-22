.. _getting_started:

Getting Started
===============
Aviso Client can be used as a Python API or as Command-Line Interface (CLI) application. Below find a few steps to quickly get a working configuration, able to listen to notifications.

.. note::

   The following quick start shows how to connect to local file-based key-value store part of Aviso client itself. However, this store is normally used in test mode and is not designed for real applications. Aviso is a client application and for real applications is meant to be connected to a etcd_ store. See :ref:`configuration` on how to connect to a etcd_ store. 

.. _etcd: https://etcd.io/

Installing
----------

.. warning::
  Aviso requires Python 3.6 or above.


To install Aviso, simply run the following command:

.. code-block:: console

   % python3 -m pip install --upgrade git+https://git.ecmwf.int/scm/aviso/aviso.git@{tag_name}

.. note::

   Once on PyPI
   
   .. code-block:: console

      % pip install pyaviso


Configuring
-----------------

1. Create a configuration file in the default location `~/.aviso/config.yaml` with the following settings:

   .. code-block:: yaml

      notification_engine:
         type: file_based
      remote_configuration: False
      listeners:
      - event: generic1
         request:
            key1: value1
            key2: 20210101
            key3: a
         triggers:
            - type: echo

   This file defines how to run Aviso, the event to listen to and the triggers to execute in case of notifications. 
   The file above shows a basic example of a generic listener to event of type ``generic1``. 
   The block ``request`` describes for which events the user wants to execute the triggers. It is made by a list of keys. The users have to specify only the keys that they want to use to identify the events they are interested into. Only the notifications complying with all the keys defined will execute the triggers. These keys are defined by the listener schema file explained at the next step.

   The trigger in this example is ``echo``. This will simply print out the notification to the console output.

   More information is available in the :ref:`configuration`.

2. Copy the following schema file to the default location `~/.aviso/service_configuration/event_listener_schema.json`

   .. code-block:: json

      {
         "version": 0.1, 
         "generic1": {
            "endpoint": [
               {
                  "engine": ["etcd_rest", "etcd_grpc", "file_based"], 
                  "base": "/tmp/aviso/generic1/{key1}", 
                  "stem": "{key2}/{key3}"
               }
            ], 
            "request": {
               "key3": [{"type": "EnumHandler", "values": ["a", "b", "c"]}], 
               "key2": [{"type": "DateHandler", "canonic": "%Y%m%d"}], 
               "key1": [{"type": "StringHandler"}]
            }
         }
      }

   This schema defines the type of event accepted by the system, in this case ``generic1``, the keys required and the relative type.

Check :ref:`defining_my_listener` for more information on how the listeners and the schema.

Launching
-----------------

1. Launch Aviso application by running the following:

   .. code-block:: console

      % aviso listen

   Once in execution this command will create a process waiting for notifications compliant with the listener defined above.
      
   The user can terminate the application by pressing the key combination ``CTRL`` + ``C``

   .. note::
      The configuration file is only read at start time, therefore every time users make changes to it they need to restart the listening process.

2. Submit a notification, from another terminal:

   .. code-block:: console

      % aviso notify event=generic1,key1=value1,key2=20210101,key3=a,location=xxxx


3. After a few seconds, the trigger defined should be executed. The terminal where the listening process is running should display the following:

   .. code-block:: console

      "event": "generic1",
      "request": {
         "key1": "value1",
         "key2": "20210101",
         "key3": "a"
      },
      "location":xxxx

.. note::

   ``location`` is used to assign a value to the specific event notified. As Aviso is used for data availability a `location` URL is normally associated to the event. It is, however, optional. If not given the value will be `None`. This last case is used when only an acknowledgement that something happened is needed, i.e. a data has been produced and users know how access to it independently.
   
More information on the available commands can be found in :ref:`notification_cli`