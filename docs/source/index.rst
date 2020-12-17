Welcome to Aviso's documentation!
=================================

.. Warning::
   This documentation is work in progress.

Aviso is a service developed at ECMWF with the aim of notifying for **data availability** of the time-critical data
produced at ECMWF, such as the real-time forecast and derived products.

It allows users to:

* Define which events to be notified of.
* Define the triggers to be executed once a notification is received.

This enables the creation of automatic workflows timely triggered as data become available

See :ref:`overview` for more information.


.. toctree::
   :maxdepth: 1
   :caption: User Guide:

   guide/overview
   guide/getting_started
   guide/defining_my_listener
   guide/testing_my_listener
   guide/historical_notifications
   guide/python_api
   guide/running_service
   guide/examples

.. toctree::
   :maxdepth: 1
   :caption: Reference:

   reference/configuration
   reference/triggers
   reference/notification_cli
   reference/python_api
   reference/configuration_cli

.. toctree::
   :maxdepth: 1
   :caption: Contributing:

   contributing/how_to
   contributing/aviso_client
   contributing/aviso_server
   


License 
-------

*Aviso* is available under the open source `Apache License`__.

__ http://www.apache.org/licenses/LICENSE-2.0.html