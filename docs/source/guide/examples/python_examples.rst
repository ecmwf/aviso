.. _python_examples:

Python API
=================

Below find a Python example of a basic event listener for ``mars`` events that will execute a ``function`` trigger 
in case of notifications.

.. literalinclude:: python_api_basic.py
   :language: python

Below find a real-life Python example of an event listener for ``mars`` events that will execute a MARS_ request in
case of notifications. Note how easy is to construct the `MARS` request from the notification, they 
both speak the `MARS` language.

.. _MARS: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets

.. literalinclude:: python_api_mars.py
   :language: python