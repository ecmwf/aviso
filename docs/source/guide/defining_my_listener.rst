.. _defining_my_listener:

Defining my Listener
====================
Aviso configuration file allows the definition of multiple listeners. 
Alternatively, the listener configuration can be indicated as an independent file or multiple files.
Regardless of where is defined, each listener is composed of:

* ``event`` - the kind of event to listen to
* ``request`` - a dictionary of keys identifying the specific events to be notified
* ``triggers`` - sequence of processes to be executed once a notification is received

Here is a basic example of listener configuration with one listener:
   .. code-block:: yaml

      listeners:
         - event: generic1
         request:
            key1: value1
            key3: a
         triggers:
            - type: echo

All aspect of what kind of events can be used and which keys to use in a ``request`` are defined by the event lister schema. Each key is used to identify the events the user wants to be notified. The more keys are used the narrower the selection would be. When Aviso reads a listener ``request`` each key value is validated and formatted accordingly with the schema. Each key is associated to a type that provides a number of properties used during its validation. See :ref:`make_your_event` for more info on how to edit the schema and create your own event.

Triggers
--------

The ``triggers`` block accepts a sequence of triggers. Each trigger will result in an independent process executed every time a notification is received. 
These are the triggers currently available:

* **echo** is the simplest trigger as it prints the notification to the console output. It is used for testing
* **log** is useful for recording the received event to a log file
* **command** allows the user to define a shell command to work with the notification
* **post** allows the user to send the notification received as HTTP POST message formatted accordingly to the CloudEvent_ specification

More information are available in the :ref:`triggers`.

.. _CloudEvent: https://cloudevents.io/