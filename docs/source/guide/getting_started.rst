.. _getting_started:

Getting Started
===============
Aviso can be used as a Python API or as Command-Line Interface (CLI) application. Below find a few steps to quickly get a working configuration, able to listen to notifications.
Note that Aviso is a client application, the following quick start shows how to connect to the ECMWF notification service, that is the current default configuration. For alternative configurations 
see :ref:`configuration`.

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

      username: <...>
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
   have to specify only the attributes that they want to use as filters. Only the notifications complying with all the 
   attributes defined will execute the triggers. These attributes are a subset of the ECMWF MARS_ language.

   .. _MARS: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets

   The trigger in this example is ``echo``. This will simply print out the notification to the console output.

   In the default configuration, the authentication have to comply with ECMWF authentication requirements. In this case, the username is the 
   email associated to the user's ECMWF account. The email can be obtained by logging on to https://api.ecmwf.int/v1/key/. Similarly a key 
   is required as shown by next step.

2. Save the ECMWF key in `/etc/aviso/key`. The key can be obtained by logging on to https://api.ecmwf.int/v1/key/ A 
different location can be defined in the configuration file above described. More information is available in the :ref:`configuration`.

Launching
-----------------

Launch Aviso application by running the following:

.. code-block:: console

   % aviso listen

Once in execution this command will create a process waiting for notifications compliant with the listener defined above.
    
The user can terminate the application by pressing the key combination ``CTRL`` + ``C``

.. note::
   The configuration file is only read at start time, therefore every time users make changes to it they need to restart the listening process.