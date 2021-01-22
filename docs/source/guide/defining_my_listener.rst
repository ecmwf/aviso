.. _defining_my_listener:

Defining my listener
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

All aspect of what kind of events can be used and which keys to use in a request are defined by the event lister schema.

Event Listener Schema
---------------------

The events accepted by Aviso are defined in the event listener schema, below an example:

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
      "generic2":{...}

Below each part of the schema is briefly explained.

Event Type
^^^^^^^^^^

``generic1`` and ``generic2`` are event types. More event types can be defined in sequence in the same schema file.

Endpoint
^^^^^^^^

On the server side events are stored in a key-value store. This means that each event is associated to a unique key. ``endpoint`` defines how to map the event to a unique key. This unique key is the result of ``base``/``stem`` The parameters in ``{}`` will be substituted at runtime for the specific event. Using the example schema above, the following event:

.. code-block:: console

   % aviso notify event=generic1,key1=value1,key2=20210101,key3=a

would be associated to ``/tmp/aviso/generic1/value1/20210101/a`` in the store.
What to put in ``base`` and what in ``stem`` is a design choice as each of them plays a different role as explained below:

* ``engine`` defines for which engine adapter the configuration applies. Different engine adapter may require different key representation to match the specific store technology. In the example above the configuration chosen is applied to all the engine adapter available

* ``base`` is used during the listening process to define to which set of events to listen, i.e. which key prefix to query. In the examples above, aviso would listen to ``/tmp/aviso/generic1/value1``

* ``stem`` is used during the listening process to further select which events, among the ones received, will execute the triggers

Request
^^^^^^^

A listener request is composed by a subset of the keys defined in the ``request`` of the listener schema. Each key is used to identify the events the user wants to be notified. The more keys are used the narrower the selection would be. 

When Aviso reads a listener request each key value is validated and formatted accordingly with the schema. Each key is associated to a type that provides a number of properties used during its validation. The table below provides the full list of key types and the corresponding properties that can be used.

+-------------+----------+--------------+-----------+-----------+--------+-------+
|type         |required  | canonic      | values    |  default  |  range | regex |
+=============+==========+==============+===========+===========+========+=======+
|StringHandler| |check|  |[lower, upper]|           |           |        |       |
+-------------+----------+--------------+-----------+-----------+--------+-------+
|EnumHandler  | |check|  |              ||check|    ||check|    |        |       |
+-------------+----------+--------------+-----------+-----------+--------+-------+
|DateHandler  | |check|  ||check|       |           |           |        |       |
+-------------+----------+--------------+-----------+-----------+--------+-------+
|TimeHandler  | |check|  | |check|      ||check|    |           |        |       |
+-------------+----------+--------------+-----------+-----------+--------+-------+
|IntHandler   | |check|  | |check|      |           |           ||check| |       |
+-------------+----------+--------------+-----------+-----------+--------+-------+
|FloatHandler | |check|  | |check|      |           |           |        |       |
+-------------+----------+--------------+-----------+-----------+--------+-------+
|RegexHandler | |check|  |              |           |           |        ||check||
+-------------+----------+--------------+-----------+-----------+--------+-------+
.. |check| unicode:: U+2611 .. checked sign
.. |cross| unicode:: U+2612 .. cross sign

* ``required``- if specified the key would become mandatory. Note that keys used in ``base`` are mandatory by defaults
* ``canonic`` - Format to apply to the key value after validation
* ``values`` - List of valid values accepted for this key
* ``default`` - Value given to the key if not specified
* ``range`` - Validity interval
* ``regex`` - Regex pattern to use during validation

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