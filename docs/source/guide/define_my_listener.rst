.. _define_my_listener:

Define my Listener
====================
Aviso configuration file allows the definition of multiple listeners. 
Alternatively, the listener configuration can be indicated as an independent file or multiple files.
Regardless of where is defined, each listener is composed of:

* ``event`` - the kind of event to listen to
* ``request`` - a dictionary of keys identifying the specific events to be notified
* ``triggers`` - sequence of processes to be executed once a notification is received

All aspects of what kind of event can be used and which keys to use in a ``request`` are defined by the event lister schema. Each key is used to identify the events the user wants to be notified. The more keys are used the narrower the selection would be. When Aviso reads a listener ``request`` each key value is validated and formatted accordingly with the schema. Each key is associated to a type that provides a number of properties used during its validation. See :ref:`make_your_event` for more info on how to edit the schema and create your own event.

The listener below uses all the keys available for the flight events. In this case the trigger will be executed only for the events regarding flights AZ203 on 01-01-2021 at the Fiumicino(FCO) and Ciampino(CIA) airport in Rome.
Note that each key accepts single or multiple values.

.. code-block:: yaml

   listeners:
      - event: flight
      request:
         country: italy
         airport: [FCO, CIA]
         date: 20210101
         number: AZ203
      triggers:
         - type: echo


Triggers
--------

The ``triggers`` block accepts a sequence of triggers. Each trigger will result in an independent process executed every time a notification is received. 
These are the triggers currently available:

* **echo** is the simplest trigger as it prints the notification to the console output. It is used for testing
* **log** is useful for recording the received event to a log file
* **command** allows the user to define a shell command to work with the notification
* **post** allows the user to send the notification received as HTTP POST message formatted accordingly to the CloudEvents_ specification

More information are available in :ref:`triggers`.

.. _CloudEvents: https://cloudevents.io/


The example below shows how to configure multiple listeners executing scripts for different set of notifications, all flights going to or from italy, all flights AZ203, or all flights concerning Fiumicino(FCO) airport.

.. code-block:: yaml

   listeners:
      - event: flight
      request:
         country: italy
      triggers:
         - type: command
           command: ./my_script_per_country.sh
      - event: flight
      request:
         number: AZ203
      triggers:
         - type: command
           command: ./my_script_per_flight.sh
      - event: flight
      request:
         airport: FCO
      triggers:
         - type: command
           command: ./my_script_per_airport.sh

More examples are available in :ref:`examples` 