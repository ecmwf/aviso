.. _configuration:

Configuration
=============

A number of settings can be edited. For each of them users can override the 
defaults by means of one or a combination of mechanisms.
The final configuration used by the application is the result of the following sequence 
where each step merges on the previous one:

1. Loading defaults
2. Loading system config file `/etc/aviso/config.yaml`
3. Loading Home config file `~/.aviso/config.yaml`
4. Loading config defined by environment variables, AVISO_CONFIG
5. Loading config defined by command line option, ``-c``, ``--config``
6. Loading all environnement variables
7. Loading all command line options

System and Home config files are optional.

The rest of this chapter presents all the settings available. For each of them, we present the
type, the default value, how to change them using command line options, environment variables or
the configuration file. Not all these mechanisms are available for all settings.

Application
-------------------
These settings are applied at application level.

Logging
^^^^^^^
The application takes advantage for the Python logging_ module. Users can define a custom file configuration
and pass it using any of the following methods. 

====================   ============================
Type                   string, file path
Defaults               Info log on console output
Command Line options   ``-l``, ``--log``, 
Environment variable   AVISO_LOG
Configuration file     .. code-block:: yaml
                        
                          logging: <logging configuration>
====================   ============================

.. note::

   The configuration file method accepts directly the logging configuration rather than a file path to it.

.. _logging: https://docs.python.org/3/library/logging.html

Debug
^^^^^
If True the application will show the debug logs to the console output.

====================   ============================
Type                   boolean
Defaults               False
Command Line options   ``-d``, ``--debug``
Environment variable   AVISO_DEBUG
Configuration file     .. code-block:: yaml
                        
                          debug: False
====================   ============================

Quiet
^^^^^
If True the application will not show any info logs to the console output. Only errors will be displayed.

====================   ============================
Type                   boolean
Defaults               False
Command Line options   ``-q``, ``--quiet``
Environment variable   AVISO_QUIET
Configuration file     .. code-block:: yaml
                        
                          quiet: False
====================   ============================

No Fail
^^^^^^^
If True the application will always exit with error code 0, even in case of errors. This can be
useful when used in a automated workflow that is required not to stop even if Aviso exits because of errors.

====================   ============================
Type                   boolean
Defaults               False
Command Line options   ``--no-fail``
Environment variable   AVISO_NO_FAIL
Configuration file     .. code-block:: yaml
                        
                          no_fail: False
====================   ============================

Authentication Type
^^^^^^^^^^^^^^^^^^^
Type of authentication to use when talking to the server. ``ecmwf`` is required if accessing to the ECMWF Aviso service. See :ref:`aviso_ecmwf` for more information.
In case of talking directly to the store the other authentication methods may be used. If ``none`` is selected, settings as ``username``, ``username_file`` or ``key`` will be ignored.

====================   ============================
Type                   Enum [ecmwf, etcd, none]
Defaults               none
Command Line options   N/A
Environment variable   AVISO_AUTH_TYPE
Configuration file     .. code-block:: yaml
                        
                          auth_type: none
====================   ============================

Username
^^^^^^^^
This is used to authenticate the requests to the server.

====================   ============================
Type                   string
Defaults               None
Command Line options   ``-u``, ``--username``
Environment variable   AVISO_USERNAME
Configuration file     .. code-block:: yaml
                        
                          username: xxxx
====================   ============================

Username File
^^^^^^^^^^^^^
If set, the username will be read from the file defined. This takes priority over `username`.

====================   ============================
Type                   string, file path
Defaults               None
Command Line options   N/A
Environment variable   AVISO_USERNAME_FILE
Configuration file     .. code-block:: yaml
                        
                          username_file: xxxx
====================   ============================

Key
^^^
File from where to read the password to use to authenticate the requests to the server.

====================   ============================
Type                   string, file path
Defaults               /etc/aviso/key
Command Line options   ``-k``, ``--key``
Environment variable   AVISO_KEY_FILE
Configuration file     .. code-block:: yaml
                        
                          key_file: /etc/aviso/key
====================   ============================

Listener Schema Parser
^^^^^^^^^^^^^^^^^^^^^^
Type of parser to use to read the event listener schema. ``ecmwf`` is required if accessing to the ECMWF Aviso service. 

====================   ============================
Type                   Enum [generic, ecmwf]
Defaults               generic
Command Line options   N/A
Environment variable   AVISO_LISTENER_SCHEMA_PARSER
Configuration file     .. code-block:: yaml
                        
                          listener_schema_parser: generic
====================   ============================

Remote configuration
^^^^^^^^^^^^^^^^^^^^
TBC

====================   ============================
Type                   boolean
Defaults               True
Command Line options   N/A
Environment variable   AVISO_REMOTE_CONFIGURATION
Configuration file     .. code-block:: yaml
                        
                          remote_configuration: True
====================   ============================

Notification Engine
-------------------
This group of settings defines the connection to the notification server. The current defaults allow the connection to a default `etcd` local installation.

Host
^^^^
====================   ============================
Type                   string
Defaults               localhost
Command Line options   ``-H``, ``--host``
Environment variable   AVISO_NOTIFICATION_HOST
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            host: localhost
====================   ============================

Port
^^^^
====================   ============================
Type                   integer
Defaults               2379
Command Line options   ``-P``, ``--port``
Environment variable   AVISO_NOTIFICATION_PORT
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            port: 2379
====================   ============================

Type
^^^^
This defines the protocol to use to connect to the server.
In case of ``file_based`` the application will run in `TestMode` by connecting to a local store, part of Aviso itself. 
In this mode, users can execute any of the commands described in :ref:`notification_cli`. The only restriction applies to retrieving past notifications that are not available. See :ref:`testing_my_listener` for more info.

====================   ============================
Type                   Enum: [ etcd_rest, etcd_grpc, file_based ]
Defaults               etcd_rest
Command Line options   N/A
Environment variable   AVISO_NOTIFICATION_ENGINE
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            type: etcd_rest
====================   ============================

Polling Interval
^^^^^^^^^^^^^^^^
Number of seconds between successive requests of new notifications to the server .

====================   ============================
Type                   integer, seconds
Defaults               30
Command Line options   N/A
Environment variable   AVISO_POLLING_INTERVAL
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            polling_interval: 30
====================   ============================

Timeout
^^^^^^^
Timeout for the requests to the notification sever

====================   ============================
Type                   integer, seconds
Defaults               60
Command Line options   N/A
Environment variable   AVISO_TIMEOUT
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            timeout: 60
====================   ============================

HTTPS
^^^^^
====================   ============================
Type                   boolean
Defaults               False
Command Line options   N/A
Environment variable   AVISO_NOTIFICATION_HTTPS
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            https: False
====================   ============================

Catchup
^^^^^^^
If True the application will start retrieving first the missed notifications and then listening to the new ones. See :ref:`past_notifications` for more information.

====================   ============================
Type                   boolean
Defaults               True
Command Line options   ``--catchup``
Environment variable   AVISO_NOTIFICATION_CATCHUP
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            catchup: True
====================   ============================

Service
^^^^^^^
Key identifying Aviso application in the configuration management system. See :ref:`configuration_cli` for more information.

====================   ============================
Values                 string
Defaults               aviso/v1
Command Line options   N/A
Environment variable   AVISO_NOTIFICATION_SERVICE
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            service: "aviso/v1"
====================   ============================



Configuration Engine
--------------------

This group of settings defines the connection to the configuration management server. The current defaults allows connecting to a default `etcd` local installation. 
This is however not a requirement and different servers can be used. See :ref:`configuration_cli` for more information.

Host
^^^^
====================   ============================
Type                   string
Defaults               localhost
Command Line options   ``-H``, ``--host``
Environment variable   AVISO_CONFIGURATION_HOST
Configuration file     .. code-block:: yaml
                        
                          configuration_engine:
                            host: localhost
====================   ============================

Port
^^^^
====================   ============================
Type                   integer
Defaults               2379
Command Line options   ``-P``, ``--port``
Environment variable   AVISO_CONFIGURATION_PORT
Configuration file     .. code-block:: yaml
                        
                          configuration_engine:
                            port: 2379
====================   ============================

Type
^^^^
====================   ============================
Type                   Enum: [ etcd_rest, etcd_grpc, file_based ]
Defaults               etcd_rest
Command Line options   N/A
Environment variable   AVISO_CONFIGURATION_ENGINE
Configuration file     .. code-block:: yaml
                        
                          configuration_engine:
                            type: etcd_rest
====================   ============================

Timeout
^^^^^^^
Timeout for the requests to the notification sever

====================   ============================
Type                   integer, seconds
Defaults               60
Command Line options   N/A
Environment variable   AVISO_TIMEOUT
Configuration file     .. code-block:: yaml
                        
                          configuration_engine:
                            timeout: 60
====================   ============================

HTTPS
^^^^^
====================   ============================
Type                   boolean
Defaults               False
Command Line options   N/A
Environment variable   AVISO_CONFIGURATION_HTTPS
Configuration file     .. code-block:: yaml
                        
                          configuration_engine:
                            https: False
====================   ============================

Max File Size
^^^^^^^^^^^^^
This is the maximum file size allowed by during a push operation.

====================   ============================
Type                   integer, KiB
Defaults               500
Command Line options   ``--catchup``
Environment variable   AVISO_MAX_FILE_SIZE
Configuration file     .. code-block:: yaml
                        
                          configuration_engine:
                            max_file_size: 500
====================   ============================


