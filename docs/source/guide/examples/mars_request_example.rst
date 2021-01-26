.. _mars_request_example:

Accessing to ECMWF archive
==========================

This section shows some real-life examples of how to use event listeners to be notified of ECMWF real-time data availability, ``mars`` events, and to promptly retrieve this data.  The retrieval is performed using the MARS_ API, that allows to access to ECMWF archive.

Below find an example of a listener triggering the script mars_script.sh.

.. literalinclude:: mars_command_listener.yaml
   :language: yaml

Here the shell script executed by the trigger above. Note how the parameters are passed 
from the trigger to the script.

.. literalinclude:: mars_script.sh
   :language: sh

Equivalent operation can be done using the Aviso and MARS_ Python API. Note how easy is to construct the `MARS` request from the notification, they both speak the `MARS` language thanks to the MARS keys used in the listener schema. See :ref:`aviso_ecmwf` for more info.

.. literalinclude:: mars_python_api.py
   :language: python

.. _MARS: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets