Welcome to Aviso's documentation!
=================================

Aviso is a service developed by ECMWF with the aim of notifying users of **data availability** of the time-critical data
produced by ECMWF, such as real-time forecast and derived products.

It allows users to:

* Define events that require notification
* Define triggers to be executed once a notification is received

This enables the creation of automatic workflows, timely triggered as data become available

See :ref:`overview` for more information.


.. toctree::
   :maxdepth: 1
   :caption: User Guide:

   guide/overview
   guide/getting_started
   guide/defining_my_listener
   guide/testing_my_listener
   guide/past_notifications
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

*Aviso* is available under the open source `Apache License`__. In applying this licence, ECMWF does not waive the privileges and immunities 
granted to it by virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.

__ http://www.apache.org/licenses/LICENSE-2.0.html