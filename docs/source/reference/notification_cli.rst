.. _notification_cli:

.. highlight:: console

CLI for Notification
====================

Aviso provides a Command Line Interface (CLI) for listening to notifications from the server system described in :ref:`aviso_server`. 
This section describes in details the various commands associated with this functionality.


Listen
------
This command allows to listen to notifications compliant with the listeners defined:

.. code-block:: console

    Usage: aviso listen [OPTIONS] [LISTENER_FILES]...

    This method allows the user to execute the listeners defined in the YAML
    listener file

    :param listener_files: YAML file used to define the listeners

    Options:
    -c, --config TEXT    User configuration file path.
    -l, --log TEXT       Logging configuration file path.
    -d, --debug          Enable the debug log.
    -q, --quiet          Suppress non-error messages from the console output.
    -u, --username TEXT  Username required to authenticate to the server.
    -k, --key TEXT       File path to the key required to authenticate to the
                        server.
    -H, --host TEXT      Notification server host.
    -P, --port INTEGER   Notification server port.
    --test               Activate TestMode.
    --from [%Y-%m-%dT%H:%M]  Replay notification from this date.
    --to [%Y-%m-%dT%H:%M]    Replay notification to this date.
    -h, --help           Show this message and exit.


The parameter ``listener_files`` is used to define the event listeners and the triggers to execute in case 
of notifications. If not present the system will look for the default listeners which can be 
defined in the configuration files. Here an example of invoking this command with one listener file::

    % aviso listen examples/echoListener.yaml

Once in execution this command will create a background process waiting for notifications and a foreground process in busy 
waiting mode. Multiple files can also be indicated as  shown below::

   % aviso listen listener1.yaml listener2.yaml


Key
---
This command can be used to generate the key accepted by the notification server as part of the notification key-value 
pair. This command is mostly used for debugging.

.. code-block:: console

    Usage: aviso key [OPTIONS] PARAMETERS

    Generate the key to send to the notification server according to the
    current schema using the parameters defined

    :param parameters: key1=value1,key2=value2,...

    Options:
    -c, --config TEXT    User configuration file path.
    -l, --log TEXT       Logging configuration file path.
    -d, --debug          Enable the debug log.
    -q, --quiet          Suppress non-error messages from the console output.
    -u, --username TEXT  Username required to authenticate to the server.
    -k, --key TEXT       File path to the key required to authenticate to the
                        server.
    -H, --host TEXT      Notification server host.
    -P, --port INTEGER   Notification server port.
    --test               Activate TestMode.
    -h, --help           Show this message and exit.

Here an example of this command::

    % aviso key event=dissemination,target=E1,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0

Note the various parameters required by the notification. The output from this command will be something like::

    /ec/diss/FOO/target=E1,class=od,expver=0001,domain=g,date=20190810,time=00,stream=enfo,step=001

Note how the format and the order of the parameters have been adjusted to complying with the internal key schema.


Value
-----
This command is used to retrieve from the server the value associated to a set of key-value pairs using the same syntax 
of the command ``key``.

.. code-block:: console

    Usage: aviso value [OPTIONS] PARAMETERS

    Return the value on the server corresponding to the key which is generated
    according to the current schema and the parameters defined

    :param parameters: key1=value1,key2=value2,...

    Options:
    -c, --config TEXT    User configuration file path.
    -l, --log TEXT       Logging configuration file path.
    -d, --debug          Enable the debug log.
    -q, --quiet          Suppress non-error messages from the console output.
    -u, --username TEXT  Username required to authenticate to the server.
    -k, --key TEXT       File path to the key required to authenticate to the
                        server.
    -H, --host TEXT      Notification server host.
    -P, --port INTEGER   Notification server port.
    --test               Activate TestMode.
    -h, --help           Show this message and exit.

Here an example of this command::

    % aviso value event=dissemination,target=E1,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0

Note the list of parameters required, it is the same list required by the ``key`` command.


Notify
------
This command is used to directly send a notification to the server using the same syntax of the command ``key``

.. code-block:: console

    Usage: aviso notify [OPTIONS] PARAMETERS

    Create a notification with the parameters passed and submit it to the
    notification server :param parameters: key1=value1,key2=value2,...

    Options:
    -c, --config TEXT    User configuration file path.
    -l, --log TEXT       Logging configuration file path.
    -d, --debug          Enable the debug log.
    -q, --quiet          Suppress non-error messages from the console output.
    -u, --username TEXT  Username required to authenticate to the server.
    -k, --key TEXT       File path to the key required to authenticate to the
                        server.
    -H, --host TEXT      Notification server host.
    -P, --port INTEGER   Notification server port.
    --test               Activate TestMode.
    -h, --help           Show this message and exit.

Here an example of this command::

    % aviso notify event=dissemination,target=E1,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0,location=xxxxxxxx

Note the list of parameters required, it is the same list required by the ``key`` command with the addition of the ``location``
pair. This is needed only for the ``dissemination`` event. 

In the case of a ``mars`` event the command looks like this::

    % aviso notify event=mars,class=od,date=20190810,domain=g,expver=1,step=1,stream=enfo,time=0

with no ``destination``, ``target`` and ``location`` pair.

