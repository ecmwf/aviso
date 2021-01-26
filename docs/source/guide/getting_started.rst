.. _getting_started:

Getting Started
===============
Aviso Client can be used as a Python API or as Command-Line Interface (CLI) application. Below find a few steps to quickly get a working configuration on Linux.

.. note::

   Currently Aviso supports only etcd_ as key-value store for the server side. The following quick start shows how to connect to a local basic installation of etcd_. See :ref:`configuration` on how to connect to a remote cluster.

.. _etcd: https://etcd.io/

Installing
----------

.. warning::
  Aviso requires Python 3.6+ and etcd 3.4+


1. Install Aviso Client, simply run the following command:

.. code-block:: console

   pip install pyaviso

2. Install etcd_, below the basic steps to install a local server:

.. code-block:: console

   ETCD_VER=v3.4.14
   DOWNLOAD_URL=https://github.com/etcd-io/etcd/releases/download

   curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
   tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1

   # start a local etcd server
   /tmp/etcd-download-test/etcd

For more advanced configuration or installation on different platforms please refer to the official documentation on the release_ page. Note that the etcd version mentioned in the script above is the latest available at the time of writing this documentation. Use any compatible version.

.. _release: https://github.com/etcd-io/etcd/releases

Configuring
-----------------

All the examples of this guide are based on a representative use case, the broadcast of flight events, such as landing or take-off, that could trigger workflows for flight trackers and related applications. This use case is available by default. The following steps show how to try it out. See :ref:`make_your_event` to customise it to your application.

Create a configuration file in the default location `~/.aviso/config.yaml` with the following settings:

.. code-block:: yaml

   listeners:
   - event: flight
      request:
         country: Italy
      triggers:
         - type: echo

This file defines how to run Aviso, the event to listen to and the triggers to execute in case of notifications. 
This is a basic example of a generic listener to events of type ``flight``. 
``request`` describes for which events the user wants to execute the triggers. It is made by a list of keys. The users have to specify only the keys that they want to use to identify the events they are interested into. Only the notifications complying with all the keys defined will execute the triggers. In this example the trigger will be executed only when flight events for Italy will be received. These keys are defined by the listener schema file, see :ref:`make_your_event` for more info.

The trigger in this example is ``echo``. This will simply print out the notification to the console output.

Check :ref:`define_my_listener` to create a more complex listener.

Launching
-----------------

1. Launch Aviso application by running the following:

   .. code-block:: console

      aviso listen

   Once in execution this command will create a process waiting for notifications compliant with the listener defined above.
      
   The user can terminate the application by pressing the key combination ``CTRL`` + ``C``

   .. note::
      The configuration file is only read at start time, therefore every time users make changes to it they need to restart the listening process.

2. Submit a example notification, from another terminal:

   .. code-block:: console

      aviso notify event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Landed

This example represents the landing event for the flight AZ203 in Fiumicino(FCO) Airport in Rome on 01-01-2021.

3. After a few seconds, the trigger defined should be executed. The terminal where the listening process is running should display the following:

   .. code-block:: console

      "event": "flight",
      "payload": "Landed",
      "request": {
         "country": "italy",
         "date": "20210101",
         "airport": "FCO",
         "number": "AZ203"
      }

   .. note::

      ``payload`` is used to assign a value to the specific event notified. It is, however, optional. If not given the payload will be `None`. This last case is used when only an acknowledgement that something happened is needed.
   
The complete list of available commands can be found in :ref:`notification_cli`