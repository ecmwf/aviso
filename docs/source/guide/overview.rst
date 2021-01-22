.. _overview:

Overview
========

Aviso is a scalable notification system designed for high-throughput. It is developed by ECMWF - European Centre for Medium-Range Weather Forecasts - with the aim of:

* Notifying **events**
* Triggering users' **workflows**
* Supporting a semantic **When** <this> … **Do** <that> …
* Persistent history and replay ability
* **Independent** of HPC or Cloud environments
* **Protocol agnostic**
* Highly reliable - built for **time-critical** applications.

Aviso is a client-server application. We refer to the notification server as Aviso Server while to the client application as Aviso Client or just Aviso. 
This user guide and the reference are focused on Aviso client. See more info on its architecture in :ref:`aviso_client`.

The server system is based on a persistent key-value store where the events are stored, the key represents the product's metadata while the value, the product's location.
See more info on the server solution and its components in :ref:`aviso_server`.


What could I use Aviso for?
---------------------------

Aviso is developed with the intention of being generic and applicable to various domains and architectures, 
also independently of ECMWF software systems.
Aviso can be used for:

* Automating users' workflows requiring notifications based on user-defined events.
* Automating users' workflows requiring ECMWF notifications on data availability. See :ref:`aviso_ecmwf` for more details on this service
* Automating multi-domain workflows across different Clouds and HPC centres. Aviso client can be extended to connect to various general purpose notification systems; similarly 
  Aviso server can be extended to store generic events and integrate with legacy architectures
* Configuration Management. This functionality goes beyond Aviso's main aim but it is part of the notification workflow and can also be used independently. See :ref:`configuration_cli` for more info


Aviso General Workflow
----------------

Figure below represents the general workflow of the Aviso system:

1. Aviso client allows an End-User to subscribe to an event and to program a trigger
2. Aviso client polls Aviso server for changes to the defined event
3. A notification provider submits a notification to Aviso server
4. The subscriber is notified with a new event
5. The event triggers the user’s workflow


.. image:: ../_static/workflow.png
   :width: 50%
   :align: center
