.. _echo_examples:

Echo
=================

Below find an example of an event listener for ``mars`` events that will execute a ``echo`` trigger 
in case of notifications.

.. literalinclude:: mars_echo_listener.yaml
   :language: yaml

Below find an example of an event listener for ``dissemination`` events that will execute a ``echo`` trigger 
in case of notifications. Note the ``destination`` and ``target`` fields.

.. literalinclude:: diss_echo_listener.yaml
   :language: yaml