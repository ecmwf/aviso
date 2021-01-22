.. _testing_my_listener:

Testing my listener
=====================

Aviso provides the capability of submitting test notifications to a local server. This functionality can 
be used to test the listener configuration without any impact to the operational server.

1. Launch the aviso application in test mode. This allows connection to a local file-based notification server, part of the aviso application, that is able to simulate the notification server behaviour.

   .. code-block:: console

      % aviso listen --test
      
   The console should display a Test Mode message. 

   .. note::
   
      We are assuming the listener is defined in the default configuration file as shown in :ref:`getting_started`.

2. Send a test notification. From another terminal, run the notify command. 
Here is an example for a ``generic1`` event notification.

   .. code-block:: console

      % aviso notify event=generic1,key1=value1,key2=20210101,key3=a,location=xxx --test


   .. note::
     
      The order of the keys is not important, but the command requires all of them. `location`
      is optional as it translates in the value associated to the key-value pair in the store.
      If not defined the value in the store will be `None`

3. After a few seconds, the trigger defined should be executed. 