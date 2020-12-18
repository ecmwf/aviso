.. _testing_my_listener:

Testing my listener
=====================

Aviso provides the capability of submitting test notifications to a local server. This functionality can 
be used to test the listener configuration without any impact to the operational server.

1. Launch the aviso application in test mode. This allows to connect to a local file-based notification 
server, part of the aviso application, that is able to simulate the notification server behaviour.

   .. code-block:: console

      % aviso listen --test
   The console should display a Test Mode message. 

   .. note::
   
      We are assuming the listener is defined in the default configuration file as shown in :ref:`getting_started`.

2. Send a test dissemination notification. From another terminal run the notify command. 
Here an example for a ``mars`` event notification

   .. code-block:: console

      % aviso notify event=mars,class=od,date=20190810,domain=g,expver=1,step=1,stream=enfo,time=0 --test

   Here an example for a ``dissemination`` event notification

   .. code-block:: console

      % aviso notify event=dissemination,target=E1,class=od,date=20190810,destination=<user_destination>,domain=g,expver=1,step=1,stream=enfo,time=0,location=xxxx --test

   .. note::
     
      The order of the fields is not important, but the command requires all of them. ``destination`` has to match the one of the listener configuration. 
      To submit a test ``mars`` notification the fields ``destination``, ``target`` and ``location`` have to be removed.

3. After a few seconds, the trigger defined should be executed. 