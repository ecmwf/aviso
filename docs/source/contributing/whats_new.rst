.. _whats_new:

.. highlight:: console

What's New
==============

v0.11.1 (02 February 2022)
--------------------------

HTTP 404 has been added among the exceptions handled by the automatic restart mechanism of aviso listeners. This is needed during maintenance sessions.


v0.11.0 (14 December 2021)
--------------------------

The main new feature of this release is the extension of the Post trigger to support AWS topics. More info available in the dedicated page :ref:`post_examples`.

Breaking changes
++++++++++++++++

Post trigger of type ``cloudevents`` is now of type ``cloudevents_http``. This to distinguish it from the Post trigger to AWS topic that is of
type ``cloudevents_aws``


v0.10.0 (26 April 2021)
--------------------------

The main new feature of this release is the implementation of an automatic retry mechanism for the listening process to 
reconnect in case of network issues or sever unavailability. Thanks to this the listening process should never require 
a manual restart.



v0.9.2 (4 February 2021)
--------------------------

First public release.