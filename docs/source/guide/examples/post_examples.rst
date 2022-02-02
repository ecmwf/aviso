.. _post_examples:

Post
=================

Below find an example of an event listener for ``flight`` events that will execute a ``post`` trigger 
in case of notifications. Specifically, this trigger will format the notification according to the CloudEvents_ 
specification and will send it to either a endpoint as HTTP POST request or to a AWS Simple Notification Service (SNS) topic.
The following example shows how to send it to a HTTP endpoint defined by the user. The type is ``cloudevents_http`` and ``url`` is the only mandatory parameter.

.. _CloudEvents: https://cloudevents.io/

.. literalinclude:: post_basic_http_listener.yaml
   :language: yaml

Below find a similar example showing how to customise the CloudEvents fields as well as the HTTP headers using optional parameters.

.. literalinclude:: post_complete_http_listener.yaml
   :language: yaml

In the case of a notification to a AWS SNS topic defined by the user, the structure of the trigger is similar; 
the type has to be ``cloudevents_aws`` and ``arn`` and ``region_name`` are the only mandatory parameters. 

The optional parameters 
are: ``MessageAttributes``, ``aws_access_key_id``, ``aws_secret_access_key`` for the AWS topic fields and
``cloudevents`` for the CloudEvents fields. Note that if ``aws_access_key_id`` and ``aws_secret_access_key`` are not specified the 
AWS credentials are taken from `~/.aws/credentials` if available. 

AWS SNS protocol does not enforce any specification on the message payload. Aviso uses the CloudEvents_ specification also in this case 
for consistency.

.. literalinclude:: post_aws_listener.yaml
   :language: yaml

In case of a AWS FIFO topic ``MessageGroupId`` is required.

.. literalinclude:: post_aws_fifo_listener.yaml
   :language: yaml