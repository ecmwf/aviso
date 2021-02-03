.. _post_examples:

Post
=================

Below find an example of an event listener for ``flight`` events that will execute a ``post`` trigger 
in case of notifications. Specifically, this trigger will format the notification according to the CloudEvents_ 
specification and will send it to the endpoint defined by the user.

.. _CloudEvents: https://cloudevents.io/

.. literalinclude:: post_basic_listener.yaml
   :language: yaml

Below find a similar example showing how to customise the CloudEvents fields as well as the HTTP headers.

.. literalinclude:: post_complete_listener.yaml
   :language: yaml
