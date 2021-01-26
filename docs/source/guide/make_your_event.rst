.. _make_your_event:

Make Your Own Event
====================

The events accepted by Aviso are defined in the event listener schema; all the examples presented in this guide are based on an example schema that is loaded by Aviso as default. Here it is:

.. code-block:: json

   {
      "version": 0.1, 
      "flight": {
         "endpoint": [{
            "engine": ["etcd_rest", "etcd_grpc", "file_based"], 
            "base": "/tmp/aviso/flight/", 
            "stem": "{date}/{country}/{airport}/{number}"
         }], 
         "request": {
            "date": [{"type": "DateHandler", "canonic": "%Y%m%d"}], 
            "country": [{"type": "StringHandler", "canonic": "lower"}], 
            "airport": [{"type": "StringHandler", "canonic": "upper"}], 
            "number": [{"type": "StringHandler"}]
         }
      }
   }

The schema is valid JSON file. Below each part of the schema is briefly explained.

Event type
----------

``flight`` is an event type. More event types can be defined in sequence in the same schema file.

Endpoint
--------

On the server side events are stored in a key-value store. This means that each event is associated to a unique key. ``endpoint`` defines how to map the event to a unique key. This unique key is the result of ``base``/``stem`` The parameters in ``{}`` will be substituted at runtime for the specific event. Using the example schema above, the following event:

.. code-block:: console

   aviso notify event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Landed

would be associated to the key ``/tmp/aviso/flight/20210101/italy/FCO/AZ203`` in the store.
What to put in ``base`` and what in ``stem`` is a design choice as each of them plays a different role as explained below:

* ``engine`` defines for which engine adapter the configuration applies. Different engine adapter may require different key representation to match the specific store technology. In the example above the configuration chosen is applied to all the engine adapter available

* ``base`` is used during the listening process to define to which set of events to listen, i.e. which key prefix to query. In the examples above, aviso would listen to ``/tmp/aviso/flight/``

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

.. |check| unicode:: U+2714 .. HEAVY CHECK MARK

* ``required``- if specified the key would become mandatory. Note that keys used in ``base`` are mandatory by defaults
* ``canonic`` - Format to apply to the key value after validation
* ``values`` - List of valid values accepted
* ``default`` - Value given to the key if not specified
* ``range`` - Validity interval
* ``regex`` - Regex pattern to use during validation

How to customise the schema
---------------------------

Users can create their own schema following the syntax shown above. The new schema should be place in the default location `~/.aviso/service_configuration/event_listener_schema.json` . By doing so Aviso will only read this file ignoring the example provided above.

Alternatively, schema can be retrieved dynamically from a remote location. This can be activated using the 
``remote_schema`` flag. See :ref:`config_manage` for more info.

Finally, a different schema parser can be indicated using the settings ``schema_parser``, see :ref:`configuration`. This can be used to extend the creation and loading of the schema according to users needs. An example of this is the ``EcmwfSchemaParser`` part of the ``listener_schema_parser`` module. See :ref:`aviso_ecmwf` for more info.

