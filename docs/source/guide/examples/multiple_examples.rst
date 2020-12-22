.. _multiple_examples:

Multiple
=================

Below find an example of an event listener for ``dissemination`` events that in case of notifications will 
execute a ``echo``, a ``log`` and a ``command`` trigger. They will be executed in parallel.

.. literalinclude:: multiple_triggers.yaml
   :language: yaml

Below find an example of two event listeners, one for ``dissemination`` events and one for ``mars`` events.

.. literalinclude:: multiple_listeners.yaml
   :language: yaml