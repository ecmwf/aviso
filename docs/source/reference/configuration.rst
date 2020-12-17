.. _configuration:

Configuration
=============

.. Warning::
   This documentation is work in progress.

This section lists the various settings available. For each of them, in general, the user can override the 
defaults by means of one or a combination of the following mechanisms: 

* Command line options
* Environment variables
* Configuration file in Home directory, `~/.aviso/config.yaml`
* Configuration file in system directory, `/etc/aviso/config.yaml`

This list is in priority order meaning that the environment variables override the configuration files
while the command line options override the environment variables and the configuration files. 
Please note that this priority order is applied per each setting individually.

Notification Engine
-------------------
This group of settings defines the connection to the notification server

Host
^^^^

====================   ============================
Values                 string
Defaults               aviso.ecmwf.int
Command Line options   ``-H``, ``--host``
Environment variable   AVISO_NOTIFICATION_HOST
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            host: aviso.ecmwf.int
====================   ============================

Port
^^^^

====================   ============================
Values                 integer
Defaults               443
Command Line options   ``-P``, ``--port``
Environment variable   AVISO_NOTIFICATION_PORT
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            port: 443
====================   ============================

Type
^^^^

====================   ============================
Values                 [ etcd_rest, etcd_grpc, test ]
Defaults               etcd_rest
Command Line options   N/A
Environment variable   AVISO_NOTIFICATION_ENGINE
Configuration file     .. code-block:: yaml
                        
                          notification_engine:
                            type: etcd_rest
====================   ============================