.. _testing_my_listener:

Testing my Listener
=====================

Aviso provides the capability of submitting test notifications to a local server. This functionality can 
be used to test the listener configuration without any impact to the operational server.

1. Launch the aviso application in test mode. This allows connection to a local file-based notification server, part of the aviso application, that is able to simulate the notification server behaviour.

   .. code-block:: console

      aviso listen --test
      
   The console should display a Test Mode message. 

   .. note::
   
      We are assuming the listener is defined in the default configuration file as shown in :ref:`getting_started`.

2. Send a test notification. From another terminal, run the notify command. 
Here is an example for a ``flight`` event notification.

   .. code-block:: console

      aviso notify event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Landed --test


3. After a few seconds, the trigger defined should be executed. 

Test mode can be activated at global level by setting the notification engine type to ``file_based`` In this way the ``--test`` option is not needed. See :ref:`configuration` for more info.

.. note::

   The catch_up functionality is not available in Test Mode.