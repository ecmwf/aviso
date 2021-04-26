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

Schema Parser
^^^^^^^^^^^^^^^^^^^^^^
Type of parser to use to read the event listener schema. ``ecmwf`` is required if accessing to the ECMWF Aviso service. 

====================   ============================
Type                   Enum [generic, ecmwf]
Defaults               generic
Command Line options   N/A
Environment variable   AVISO_SCHEMA_PARSER
Configuration file     .. code-block:: yaml
                        
                          schema_parser: generic
====================   ============================

Remote Schema
^^^^^^^^^^^^^^^^^^^^
If `False` the listener schema is read locally from the expected default location. In this case all the configuration engine settings are ignored. If `True` the listener schema is retrieved dynamically from the configuration server when the application starts. More info in :ref:`config_manage`

====================   ============================
Type                   boolean
Defaults               False
Command Line options   N/A
Environment variable   AVISO_REMOTE_SCHEMA
Configuration file     .. code-block:: yaml
                        
                          remote_schema: False
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
In case of ``file_based`` Aviso will run in `TestMode` by connecting to a local store, part of Aviso itself. In this mode, users can execute any of the commands described in :ref:`notification_cli`. The only restriction applies to retrieving past notifications that are not available. See :ref:`testing_my_listener` for more info.
In case of ``etcd_grpc`` or``etcd_rest`` Aviso will connect to a etcd store either by its native gRPC API or by the RESTfull API implemented by the etcd gRPC gateway_.

.. _gateway: https://etcd.io/docs/v3.4.0/dev-guide/api_grpc_gateway/

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
If True the application will start retrieving first the missed notifications and then listening to the new ones. See :ref:`catch_up` for more information.

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
Key identifying Aviso application in the configuration management system. See :ref:`config_manage` for more information.

====================   ============================
Values                 string
Defaults               aviso/v1
Command Line options   N/A
Environment variable   AVISO_NOTIFICATION_SERVICE
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            service: "aviso/v1"
====================   ============================

AUTOMATIC RETRY DELAY
^^^^^^^^^^^^^^^^^^^^^
Number of seconds to wait before retrying to connect to the notification sever. This prevents the application to terminate in case of temporarily network issues for example.

====================   ============================
Type                   integer, seconds
Defaults               15
Command Line options   N/A
Environment variable   AVISO_AUTOMATIC_RETRY_DELAY
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            automatic_retry_delay: 15
====================   ============================

Configuration Engine
--------------------

This group of settings defines the connection to the configuration management server. The current defaults allows connecting to a default `etcd` local installation. 
This is however not a requirement and different servers can be used. See :ref:`config_manage` for more information.

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
Type                   Enum: [ etcd_rest, etcd_grpc ]
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

AUTOMATIC RETRY DELAY
^^^^^^^^^^^^^^^^^^^^^
Number of seconds to wait before retrying to connect to the configuration sever. This prevents the application to terminate in case of temporarily network issues for example.

====================   ============================
Type                   integer, seconds
Defaults               15
Command Line options   N/A
Environment variable   AVISO_AUTOMATIC_RETRY_DELAY
Configuration file     .. code-block:: yaml
                        
                          configuration_engine:
                            automatic_retry_delay: 15
====================   ============================
