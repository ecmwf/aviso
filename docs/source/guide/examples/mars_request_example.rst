.. _mars_request_example:

MARS Request
=================

Below find a real-life example of an event listener for ``mars`` events that will execute a ``MARS`` request 
in case of notifications.

.. literalinclude:: mars_command_listener.yaml
   :language: yaml

Below find the shell script executed by the trigger above. Note how the parameters are passed 
from the trigger to the script.

.. literalinclude:: mars_script.sh
   :language: sh