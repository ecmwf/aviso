.. _whats_new:

.. highlight:: console

What's New
==============

Version 1.0.0 (09 January 2024)
--------------------------------

- **File-based Engine Update**
  The backend for the file-based engine has been upgraded from Pyinotify to Watchdog, enhancing performance and reliability.

- **MacOS Support**
  Version 1.0.0 introduces initial support for MacOS, broadening the platform compatibility.

- **Test Enhancements**
  Tests have been improved to utilize relative paths, increasing the robustness and portability of the testing process.

- **Prometheus Metrics**
  Added token support for Prometheus metrics.

- **Kubernetes Compatibility**
  Enhancements in aviso-monitoring to offer better support for Kubernetes environments.


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