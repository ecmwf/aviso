Welcome to Aviso's documentation!
=================================

.. Warning::
   This documentation is work in progress.

Aviso is a service developed at ECMWF with the aim of notifying for **data availability** of the time-critical data
produced at ECMWF, such as the real-time forecast and derived products.

It allows users to:

* Define which events to be notified of.
* Define the triggers to be executed once a notification is received.

This allows the creation of automatic workflows timely triggered as data become available

See :ref:`overview` for more information.


.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   overview
   getting_started
   defining_my_listener
   testing_my_listener
   historical_notifications
   python_api
   running_service
   examples

.. toctree::
   :maxdepth: 2
   :caption: Reference:

   overview


License 
-------

*Aviso* is available under the open source `Apache License`__.

__ http://www.apache.org/licenses/LICENSE-2.0.html