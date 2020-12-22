.. _aviso_client:

Aviso Client Architecture
=========================

Figure below shows the high-level architecture of Aviso client.

.. image:: ../_static/client_architecture.png
   :width: 50%
   :align: center

The whole application is implemented by the project package ``pyaviso``.
Aviso client provides two kinds of interfaces to users, a Python API for integration in user’s applications and a Command Line Interface (CLI) to use it 
as standalone application. The latter uses internally the Python API, implemented by the ```notification_manager`` module.
This module relies on the ``listener_manager`` module to translate the user's listener configuration into requests for the store.

The Listener manager encapsulates the domain-specific MARS_ language semantic and is therefore in charge of the listener validation and the creation of 
the various ``EventListener``.
These entities map users' requests and represent independent listening threads that execute the triggers as independent processes in case of a valid notification is received.

The backend of the application is implemented by the ``engine`` package. The ``Engine`` offers a common interface to the requests arriving from the 
business layer and directed to the key-value store. Different implementations are available depending on the protocol used by the store technology.
Currently the store considered are etcd_ and a file-based store used only in `TestMode`.


.. _MARS: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets
.. _etcd: https://etcd.io/