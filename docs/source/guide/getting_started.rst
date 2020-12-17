.. _getting_started:

Getting Started
===============
Aviso can be used as a Python API or as Command-Line Interface (CLI) application. Here a few steps to quickly get a working configuration listening to notifications.
Note that Aviso is a client application, this assumes that a notification server is up and running.

Installing
----------

.. warning::
  Aviso requires Python 3.6 or above.


To install Aviso, simply run the following command:

.. code-block:: console

   % python3 -m pip install --upgrade git+https://git.ecmwf.int/scm/aviso/aviso.git@{tag_name}

.. note::

   Once on PyPI
   
   .. code-block:: console

      % pip install pyaviso


Configuring
-----------------

1. Create a configuration file in the default location `~/.aviso/config.yaml` with the following settings:

   .. code-block:: yaml

      username: <ECMWF user email>
      listeners:
         - event: mars
         request:
            class: od
            expver: 1
            domain: g
            stream: enfo
            step: [1,2,3]
         triggers:
            - type: echo

   This file defines who is running Aviso, the event to listen to and the triggers to execute in case of notifications. 
   This is a basic example of a listener to real-time forecast events, this is identified by the keyword ``mars``. 
   The block ``request`` describes for which events the user wants to execute the triggers. It is made by a list of attributes. The users 
   have to specify only the attributes that they wants to use as filters. Only the notifications complying with all the 
   attributes defined will execute the triggers. 

   The trigger in this example is ``echo``. This will simply print out the notification to the console output.

   The username is the email associated to the user' ECMWF account. The email can be obtained by logging at https://api.ecmwf.int/v1/key/.

2. Save the ECMWF key in `/etc/aviso/key`. The key can be obtained by logging at https://api.ecmwf.int/v1/key/ . A 
different location can be defined in the configuration file above described. More information are available in the :ref:`configuration`.

Launching
-----------------

Launch Aviso application by running the following:

.. code-block:: console

   % aviso listen

Once in execution this command will create a process waiting for notifications compliant with the listener defined above.
    
The user can terminate the application by pressing the key combination ``CTRL`` + ``C``

.. note::
   The configuration file is only read at start time, therefore every time users make changes to it they need to restart the listening process.