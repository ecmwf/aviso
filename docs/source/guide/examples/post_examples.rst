.. _post_examples:

Post
=================

Below find an example of a basic event listener for ``dissemination`` events that will execute a ``post`` trigger 
in case of notifications. Specifically this trigger will format the notification according to the CloudEvent_ 
specification and will send it to the endpoint defined by the user.

.. _CloudEvent: https://cloudevents.io/

.. literalinclude:: post_basic_listener.yaml
   :language: yaml

Below find a similar example showing how to customise the CloudEvent fields as well as the HTTP headers.

.. literalinclude:: post_complete_listener.yaml
   :language: yaml
