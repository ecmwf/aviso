.. _getting_started:

Getting Started
===============
Aviso Client can be used as a Python API or as Command-Line Interface (CLI) application. Below find a few steps to quickly get a working configuration.

.. note::

   Currently Aviso supports only etcd_ as key-value store for the server side. The following quick start shows how to connect to a local basic installation of etcd_. See :ref:`configuration` on how to connect to a remote cluster.

.. _etcd: https://etcd.io/

Installing
----------

.. warning::
  Aviso requires Python 3.6 or above.


1. Install Aviso Client, simply run the following command:

.. code-block:: console

   % pip install pyaviso

2. Install etcd_

.. code-block:: console

   % pip install pyaviso


Configuring
-----------------

Create a configuration file in the default location `~/.aviso/config.yaml` with the following settings:

.. code-block:: yaml

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

Check :ref:`defining_my_listener` for more information.

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

      % aviso notify event=generic1,key1=value1,key2=20210101,key3=a,payload=xxxx


3. After a few seconds, the trigger defined should be executed. The terminal where the listening process is running should display the following:

   .. code-block:: console

      "event": "generic1",
      "request": {
         "key1": "value1",
         "key2": "20210101",
         "key3": "a"
      },
      "payload":xxxx

.. note::

   ``payload`` is used to assign a value to the specific event notified. It is, however, optional. If not given the payload will be `None`. This last case is used when only an acknowledgement that something happened is needed.
   
More information on the available commands can be found in :ref:`notification_cli`