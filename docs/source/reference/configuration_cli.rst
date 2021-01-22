.. _configuration_cli:

Configuration Management
========================

Aviso can also be used to store and retrieve configuration files for external applications. In this 
case it acts as a configuration management system. 

From the sever side storing configurations equates to a key-value pair where the key is the configuration file path
and the value is the configuration content. This means that the two Aviso functionalities, notification and 
configuration, share the same server technology and architecture, and therefore most of user options 
presented in :ref:`notification_cli`.

.. note::

   This functionality can be used as part of the Aviso notification workflow.
   Specifically, it can dynamically pull the event 
   listener schema when Aviso client startups. This allows to share and update this schema with the notification providers. The notification provider is required to comply with the notification format otherwise the notification will be wrongly identified by the listeners.
   Given the high-throughput of the system this solution exploits the scalability of the server architecture already in place. See :ref:`configuration` on how to enable it.

The following section presents the commands available with the configuration CLI.

.. code-block:: console

   % aviso-config -h
   Usage: aviso-config [OPTIONS] COMMAND [ARGS]...

   Options:
   --version   Show the version and exit.
   -h, --help  Show this message and exit.

   Commands:
   pull    Pull all files associated with the service defined.
   push    Push all files from the directory selected to the service...
   remove  Remove all files associated with the service defined.
   revert  Revert all files associated with the service defined to the...
   status  Retrieve the status of the service defined.

.. note::

   The commands above inherit the options and configuration described in :ref:`notification_cli` and
   in :ref:`configuration`. These options are then omitted from the descriptions that follow.


Pull
------
The pull operation is used to retrieve the configuration files of a specific service.

.. code-block:: console

   % aviso-config pull -h
   Usage: aviso-config pull [OPTIONS] SERVICE

   Pull all files associated with the service defined.

   Options:
   -H, --host TEXT      Configuration server host.
   -P, --port INTEGER   Configuration server port.
   -D, --dir TEXT       Destination directory to pull into.
   --delete             Allows delete of local files if they do not exist on the server.

Below is an example of how to use it:

.. code-block:: console

   % aviso-config pull aviso/v1 --dir config/event_listener/

In this case the configuration files associated to the service ``aviso/v1`` will be pulled and saved in the directory 
indicated. If any of these files is already present it will be overridden.

.. note::

   Options ``-H`` and ``-P`` are used to set the configuration server as aviso-config does not use any 
   notification server.

Push
------
The push operation is used to push configuration files of a specific service.

.. code-block:: console

   % aviso-config push -h
   Push all files from the directory selected to the service defined,
   respecting the subdirectory structure.

   Options:
   -H, --host TEXT      Configuration server host.
   -P, --port INTEGER   Configuration server port.
   -D, --dir TEXT       Directory to push.  [required]
   -m, --message TEXT   Message to associate to the push.  [required]
   --delete             Allows delete of files on server if they do not exist locally.

Below is an example of how to use it:

.. code-block:: console

   % aviso-config push aviso/v1 --dir config/event_listener/ -m 'event listener schema update'

In this case the content of the directory `config/event_listener` is pushed under the service ``aviso/v1``
Note that every time something is pushed to a service location, the service status is updated with the message 
passed and the user information and the version are incremented.

Remove
------
The remove operation is used to remove all the configuration files of a specific service.

.. code-block:: console

   % aviso-config remove -h
   Usage: aviso-config remove [OPTIONS] SERVICE

   Remove all files associated with the service defined.

   Options:
   -H, --host TEXT      Configuration server host.
   -P, --port INTEGER   Configuration server port.
   -f, --doit           Remove without prompt.

Below is an example of how to use it:

.. code-block:: console

   % aviso-config remove aviso/v1 -f

In this case the configuration files associated to the service passed will all be removed from the configuration server.

Without the option ``-f`` the application only lists the files associated to the service. It can therefore be used just to 
list the files associated with the service.

Revert
------
The revert operation is used to restore the previous version of all the configuration files of a specific service.

.. code-block:: console

   % aviso-config revert -h
   Usage: aviso-config revert [OPTIONS] SERVICE

   Revert all files associated with the service defined to the previous
   version.

   Options:
   -H, --host TEXT      Configuration server host.
   -P, --port INTEGER   Configuration server port.

Below is an example of how to use it:

.. code-block:: console

   % aviso-config revert aviso/v1

.. note:: 

   If this command is run twice consecutively, this results in no changes to the files on the server but the version 
   will be incremented.

Status
------
The status operation is used to retrieve the status of a specific service.

.. code-block:: console

   % aviso-config status -h
   Usage: aviso-config status [OPTIONS] SERVICE

   Retrieve the status of the service defined.

   Options:
   -H, --host TEXT      Configuration server host.
   -P, --port INTEGER   Configuration server port.

Below is an example of how to use it:

.. code-block:: console

   % aviso-config status aviso/v1

This would return something on these lines:

.. code-block:: json

   {
      "aviso_version": "0.3.0",
      "date_time": "2020-02-04T16:25:45.521Z",
      "engine": "ETCD_REST",
      "etcd_user": "root",
      "hostname": "viron",
      "message": "test",
      "prev_rev": 55054,
      "unix_user": "maci",
      "version": 23
   }

