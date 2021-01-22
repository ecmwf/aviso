.. _make_your_event:

Make Your Own Event
====================

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
----------

``generic1`` and ``generic2`` are event types. More event types can be defined in sequence in the same schema file.

Endpoint
--------

On the server side events are stored in a key-value store. This means that each event is associated to a unique key. ``endpoint`` defines how to map the event to a unique key. This unique key is the result of ``base``/``stem`` The parameters in ``{}`` will be substituted at runtime for the specific event. Using the example schema above, the following event:

.. code-block:: console

   % aviso notify event=generic1,key1=value1,key2=20210101,key3=a

would be associated to ``/tmp/aviso/generic1/value1/20210101/a`` in the store.
What to put in ``base`` and what in ``stem`` is a design choice as each of them plays a different role as explained below:

* ``engine`` defines for which engine adapter the configuration applies. Different engine adapter may require different key representation to match the specific store technology. In the example above the configuration chosen is applied to all the engine adapter available

* ``base`` is used during the listening process to define to which set of events to listen, i.e. which key prefix to query. In the examples above, aviso would listen to ``/tmp/aviso/generic1/value1``

* ``stem`` is used during the listening process to further select which events, among the ones received, will execute the triggers

Request
-------

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

Payload
--------

