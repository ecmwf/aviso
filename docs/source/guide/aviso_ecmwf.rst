.. _aviso_ecmwf:

How Aviso Works at ECMWF
========================

This section presents how Aviso has been configured and deployed at ECMWF. This is a real-life example of usage of Aviso as well as a service users can request to access.


ECMWF Aviso service
-------------------

ECMWF has deployed Aviso as a notification service for the data availability of:

  * Real-Time Model Output Data
  * Products delivered via ECMWF dissemination system

Figure below shows ECMWF data flow; it starts from the data assimilation of observations, it then follows to the generation of the model output, the real-time global forecast. 
This is a time critical step for users' workflows and therefore its completion is notified by Aviso. The data flow continues with the generation of derived products that are then
disseminated via ECMWF dissemination system. The delivery of these products is also notified by Aviso as users depend on custom products for their downstream applications.  

.. image:: ../_static/data_flow.png
   :align: center

This service is based on the Aviso server solution presented in :ref:`aviso_server`. 

.. warning::

   ECMWF Aviso service is currently limited to registered users only. Please contact `ECMWF Service Desk`__ for more details.

__ https://www.ecmwf.int/en/about/contact-us


How to configure Aviso Client
-----------------------------

1. Create a configuration file in the default location `~/.aviso/config.yaml` with the following settings:

   .. code-block:: yaml

      username: <...>
      listeners:
         - event: mars
         request:
            class: od
            expver: 1
            domain: g
            stream: enfo
            step: [1,2,3]
         triggers:
            - type: echo

   This file defines who is running Aviso, the event to listen to and the triggers to execute in case of notifications. 
   This is a basic example of a listener to real-time forecast events, this is identified by the keyword ``mars``. 
   The block ``request`` describes for which events the user wants to execute the triggers. It is made by a list of attributes. The users 
   have to specify only the attributes that they want to use as filters. Only the notifications complying with all the 
   attributes defined will execute the triggers. These attributes are a subset of the ECMWF MARS_ language.

   .. _MARS: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets

   The trigger in this example is ``echo``. This will simply print out the notification to the console output.

   In the default configuration, the authentication have to comply with ECMWF authentication requirements. In this case, the username is the 
   email associated to the user's ECMWF account. The email can be obtained by logging on to https://api.ecmwf.int/v1/key/. Similarly a key 
   is required as shown by next step.

2. Save the ECMWF key in `/etc/aviso/key`. The key can be obtained by logging on to https://api.ecmwf.int/v1/key/ A 
different location can be defined in the configuration file above described. More information is available in the :ref:`configuration`.


ECMWF Event Listeners 
----------------------

Events
^^^^^^^

Aviso is currently offering notifications for the following types of events:

* **dissemination** event is submitted by the ECMWF product dissemination system. The related listener configuration must define the ``destination`` field. A notification related to a dissemination event will have the field ``location`` containing the URL to the product notified
* **mars** event is designed for real-time data from the ECMWF model output. The related listener configuration does not have any mandatory fields. Moreover the related notification will not contain the location field because users will have to access to it by the conventional ECMWF MARS_ API

.. _MARS: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets

These events are ECMWF specific. However, Aviso can be extended to handle different kind of events. The event type defines the translation to go from the event's metadata to the key that will be used as 
key-value pair to store the event in Aviso server. The various translations are defined in a schema file.

Request 
^^^^^^^
The table below shows the full list of fields accepted in a ``request`` block. These fields represent a subset of the ECMWF MARS_ language.

+------------+----------------------+--------------+--------------------+
|Field       |Type                  | Event        | Optional/Mandatory |
+============+======================+==============+====================+
|destination |String, uppercase     |dissemination |Mandatory           |
+------------+----------------------+--------------+--------------------+
|target      |String                |dissemination |Optional            |
+------------+----------------------+--------------+--------------------+
|date        |Date (e.g.20190810)   |All           |Optional            |
+------------+----------------------+--------------+--------------------+
|time        |Values: [0,6,12,18]   |All           |Optional            |
+------------+----------------------+--------------+--------------------+
|class       |Enum                  |All           |Optional            |
+------------+----------------------+--------------+--------------------+
|stream      |Enum                  |All           |Optional            |
+------------+----------------------+--------------+--------------------+
|domain      |Enum                  |All           |Optional            |
+------------+----------------------+--------------+--------------------+
|expver      |Integer               |All           |Optional            |
+------------+----------------------+--------------+--------------------+
|step        |Integer               |All           |Optional            |
+------------+----------------------+--------------+--------------------+


Listener Schema
^^^^^^^^^^^^^^^

.. code-block:: yaml

   dissemination:
   endpoint:
      - engine: [etcd_rest, etcd_grpc]
         base: "/ec/diss/{destination}"
         stem: "date={date},target={target},class={class},expver={expver},domain={domain},time={time},stream={stream},step={step}"
         admin: "/ec/admin/{date}/{destination}"
      - engine: [test]
         base: "/tmp/aviso/diss/{destination}"
         stem: "{target}/{class}/{expver}/{domain}/{date}/{time}/{stream}/{step}"
   request:
      class:
         - type: EnumHandler
      date:
         - type: DateHandler
         canonic: '%Y%m%d'
      destination:
         - type: StringHandler
         required: true
      target:
         - type: StringHandler
      domain:
         - type: EnumHandler
         default: "g"
      expver:
         - type: IntHandler
         canonic: '{0:0>4}'
      step:
         - type: IntHandler
         range:
         - 0
         - 100000
      stream:
         - type: EnumHandler
      time:
         - type: TimeHandler
         canonic: '{0:0>2}'
         values:
         - 0
         - 6
         - 12
         - 18
   mars:
   endpoint:
      - engine: [etcd_rest, etcd_grpc]
         base: "/ec/mars"
         stem: "date={date},class={class},expver={expver},domain={domain},time={time},stream={stream},step={step}"
      - engine: [test]
         base: "/tmp/aviso/mars"
         stem: "{class}/{expver}/{domain}/{date}/{time}/{stream}/{step}"
   request:
      class:
         - type: EnumHandler
      date:
         - type: DateHandler
         canonic: '%Y%m%d'
      domain:
         - type: EnumHandler
      expver:
         - type: IntHandler
         canonic: '{0:0>4}'
      step:
         - type: IntHandler
         range:
         - 0
         - 100000
      stream:
         - type: EnumHandler
      time:
         - type: TimeHandler
         canonic: '{0:0>2}'
         values:
         - 0
         - 6
         - 12
         - 18
      


   attributes defined will execute the triggers. These attributes are a subset of the ECMWF MARS_ language.

   .. _MARS: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets

