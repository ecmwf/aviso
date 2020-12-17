# Aviso

Table of content:

* [Configuring Aviso](#configuring-aviso)
    * [Command line options](#command-line-options)
    * [Environment variables](#environment-variables)
    * [Configuration files](#configuration-files)
* [Notification client](#notification-client)
    * [listen](#listen)
    * [key](#key)
    * [value](#value)
    * [notify](#notify)
    * [Testing Listener Configuration](#testing)
* [Configuration client](#configuration-client)
    * [push](#push)
    * [pull](#pull)
    * [remove](#remove)
    * [revert](#revert)
    * [status](#status)
    * [Case study - Aviso Service](#case-study---aviso-service)

<a name="configuring-aviso"></a> 
## Configuring Aviso

In absence of any user settings the application run by using its internal default settings, here listed:
```
notification_engine:
  type: etcd_rest
  host: aviso.ecmwf.int
  port: 443
  polling_interval: 60
  timeout: 60
  service: aviso/v1
  https: true
configuration_engine:
  type: etcd_rest
  host: aviso.ecmwf.int
  port: 443
  max_file_size: 100
  timeout: 60
  https: true
debug: False
quiet: False
no_fail: False
username: <UNIX user>
key_path: /etc/aviso/key
auth_type: ecmwf
```
The user can override the defaults by means of one or a combination of the following mechanisms: 
* Command line options
* Environment variables
* Configuration file in Home directory, _~/.aviso/config.yaml_
* Configuration file in system directory, _/etc/aviso/config.yaml_

This list is in priority order meaning that the environment variables override the configuration files
while the command line options override the environment variables and the configuration files. Please note that this 
priority order is applied per each setting.

With regards of the logging, the user can customise the system logging as well as the console output using a file based 
configuration. The user can indicate a file path using the command line option or environment variable as explained in 
the next paragraphs. Alternatively, the system will look for the _logging_ section in the configuration files.  
In absence of any configuration file the system logs the debug log to the location 
_~/.aviso/log/aviso.debug.log_ in json format and output the info log to the console standard error stream.

With regards to the endpoints, the system allows configuring a notification server, where the application will listen to
and a configuration server, used by the application for internal configuration.

Please note that the configuration file in the system directory is meant for the Aviso execution as a system service. 
More details in section [running as a service](#service).

<a name="command-line-options"></a> 
### Command line options

`$ aviso listen --help` gives some information on the options accepted for the listening mode. They are vastly 
identical for all commands.
```
Options:
  -c, --config TEXT    User configuration file path.
  -l, --log TEXT       Logging configuration file path.
  -d, --debug          Enable the debug log.
  -q, --quiet          Suppress non-error messages from the console output.
  --no-fail            Suppress any error exit code.
  -u, --username TEXT  Username required to authenticate to the server.
  -k, --key TEXT       File path to the key required to authenticate to the
                       server.
  -H, --host TEXT      Notification server host.
  -P, --port INTEGER   Notification server port.
  --test               Activate TestMode.
  --version            Show the version and exit.
  -h, --help           Show this message and exit.
```

Using the command -l allows to configure the logging system using a file-based configuration that would override the 
default one. Please note that only the most common configuration settings can be edited using command line options.

Using the command -c allows to specify a different path for the configuration file. This file would take priority over
the other default configuration files and the `AVISO_CONFIG` environment variable. However, the other user settings 
specified by CLI options or environment variables would take priority over it. 

<a name="environment-variables"></a> 
### Environment variables
Users can define the following environment variables with similar scope as for the command line options:
* `AVISO_NOTIFICATION_HOST`      Notification server host.
* `AVISO_NOTIFICATION_PORT`      Notification server port.
* `AVISO_NOTIFICATION_HTTPS`     If True the connection will go through HTTPS. Note the gRPC engine ignores this settings, it is only using HTTP
* `AVISO_NOTIFICATION_ENGINE`    Type of notification server to connect to. Current options are: `etcd_rest`, `etcd_grpc`, `test`.
* `AVISO_NOTIFICATION_SERVICE`   Location in the configuration server associated to the notification service for the event listeners validation
* `AVISO_POLLING_INTERVAL`       Number of seconds between pull requests of key updates during listening to the notification server.
* `AVISO_CONFIGURATION_HOST`     Notification server host.
* `AVISO_CONFIGURATION_PORT`     Notification server port.
* `AVISO_CONFIGURATION_HTTPS`    If True the connection will go through HTTPS. Note the gRPC engine ignores this settings, it is only using HTTP
* `AVISO_CONFIGURATION_ENGINE`   Type of configuration server to connect to. Current options are: `etcd_rest`, `etcd_grpc`.
* `AVISO_MAX_FILE_SIZE`          Maximum file size allowed to be pushed in KiB to the configuration server.
* `AVISO_CONFIG`                 User configuration file path.
* `AVISO_LOG`                    Logging configuration file path.
* `AVISO_DEBUG`                  Enable the debug log.
* `AVISO_QUIET`                  Suppress non-error messages from the console output.
* `AVISO_USERNAME`               Username required by the notification server.
* `AVISO_USERNAME_FILE`          File path containing the username required to authenticate the user.
* `AVISO_NO_FAIL`                Suppress any error exit code. This is meant to be used when the application is part of 
                                 of a critical chain and any error generated shall not stop the chain.
* `AVISO_KEY_FILE`               Path to the key file required for authentication.
* `AVISO_AUTH_TYPE`              Type of authentication used by the system. Current options are `etcd`-only and `ecmwf`.
* `AVISO_TIMEOUT`                Number of seconds of waiting before timing-out the request to the server. Note that this variable
                                 set the timeout for the notification and for the configuration server. Use the configuration file
                                 to set them differently. A value of `null` will make it wait until the connection is closed.

<a name="configuration-files"></a> 
### Configuration files
Configuration files can be created at the default paths _~/.aviso/config.yaml_ or _/etc/aviso/config.yaml_ and they would be 
automatically parsed by the application. Alternatively, its path needs to be indicated using the command line option or 
the environment variable.

Below and example of a complete user configuration file. The omitted field will be replaced by defaults. Any 
extra field will not be considered. Apart from the single settings, the configuration file accepts a `listeners` and 
a `logging` section.

The `listeners` section helps defining defaults listeners. More information on how to define them is in the dedicated 
[section](#defining-the-listener).

The `logging` section encapsulates the logging configuration as required by the python 
[logging module](https://docs.python.org/2/library/logging.html). This configuration is automatically loaded, overriding
the default configuration described in the previous section.
```
notification_engine:
  type: etcd_rest
  host: aviso.ecmwf.int
  port: 443
  polling_interval: 30
  timeout: None
  service: aviso/v1
  https: true
configuration_engine:
  type: etcd_rest
  host: aviso.ecmwf.int
  port: 443
  max_file_size: 100
  https: true
debug: False
quiet: False
username: <user>
key_path: ~/.aviso/key
listeners:
  - event: dissemination
    request:
      destination: FOO
      stream: enfo
    triggers:
      - type: echo
logging:
  version: 1
  disable_existing_loggers: False
  formatters:
    precise:
      format: '%(asctime)s - %(process)d - %(thread)d - %(name)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s'
    json:
      format: '%(asctime)s - %(process)d - %(thread)d - %(name)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s'
      class: pythonjsonlogger.jsonlogger.JsonFormatter
    brief:
      format: '%(message)s'
  handlers:
    console:
      class: logging.StreamHandler
      level: INFO
      formatter: brief
      stream: ext://sys.stderr
    debug_json:
      class: logging.FileHandler
      level: DEBUG
      formatter: json
      filename: ~/.aviso/log/aviso.debug-json.log
    debug_file:
      class: logging.FileHandler
      level: DEBUG
      formatter: precise
      filename: ~/.aviso/log/aviso.debug.log
  root:
    level: DEBUG
    handlers: [console, debug_file, debug_json]
```
Please note that the configuration path cannot be defined using the configuration file.

<a name="notification-client"></a> 
## Notification client
Aviso provides the capability for listening to and for submitting notifications. This section describes in details 
the various commands.


<a name="testing"></a> 
### Testing Listener Configuration
Aviso provides a test mode that can be used to test the listener configuration. Once enabled the application will 
point to a local file-based notification server, part of Aviso itself. Thanks to this internal server the users will be 
able to send notifications and listen to them in the same way as they would do when pointing to the real notification 
server.

To enable the test mode, the following configuration needs to be defined:
```
notification_engine:
  type: test 
```
Once activated the user can execute any of the commands described in this section, 
[notification client](#notification-client), including the `notify` [command](#notify). The only restriction apply to 
the [Catch-up](#catch-up) feature that is not available.

Alternatively, the user can add the `--test` option to any of these commands.

<a name="configuration-client"></a> 
## Configuration client 

Aviso can be used to store and retrieve configuration files for various services including Aviso itself.

```
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
```
Each of these commands inherits the options described above for aviso and the same configuration/logging system. These
options will then be omitted from the descriptions that follow.

<a name="push"></a> 
### Push
The push operation is used to push configuration files of a specific service.
```
Usage: aviso-config push [OPTIONS] SERVICE

  Push all files from the directory selected to the service defined,
  respecting the subdirectory structure.

Options:
  -H, --host TEXT      Configuration server host.
  -P, --port INTEGER   Configuration server port.
  -D, --dir TEXT       Directory to push.  [required]
  -m, --message TEXT   Message to associate to the push.  [required]
  --delete             Allows delete of files on server if they don`t exist locally.
```
An example of use is the following:
```
$ aviso-config push aviso/v1 --dir config/event_listener/ -m 'event listener schema update'
```
In this case the content of the directory _config/event_listener_ is pushed under the service _aviso/v1_
Note that every time something is pushed to a service location, the service status is update with the message 
passed and the user information and the version are incremented.

Note that the option _-H_ and _-P_ are used to set the configuration server as aviso-config does not use any 
notification server.

<a name="pull"></a> 
### Pull
The pull operation is used to retrieve the configuration files of a specific service.
```
Usage: aviso-config pull [OPTIONS] SERVICE

  Pull all files associated with the service defined.

Options:
  -H, --host TEXT      Configuration server host.
  -P, --port INTEGER   Configuration server port.
  -D, --dir TEXT       Destination directory to pull into.
  --delete             Allows delete of local files if they don`t exist on server.
```
An example of use is the following:
```
$ aviso-config pull aviso/v1 --dir config/event_listener/
```
In this case the configuration files associated to the service passed will be pulled and saved in the directory 
indicated. If any of these files is already present it will be overridden.

<a name="remove"></a> 
### Remove
The remove operation is used to remove all the configuration files of a specific service.
```
Usage: aviso-config remove [OPTIONS] SERVICE

  Remove all files associated with the service defined.

Options:
  -H, --host TEXT      Configuration server host.
  -P, --port INTEGER   Configuration server port.
  -f, --doit           Remove without prompt.
```
An example of use is the following:
```
$ aviso-config remove aviso/v1 -f
```
In this case the configuration files associated to the service passed will all be removed from the configuration server.

Without the option -f the application only lists the files associated to the service. It can therefore be used just to 
list the files associated with the service.

<a name="revert"></a> 
### Revert
The revert operation is used to restore the previous version of all the configuration files of a specific service.
```
Usage: aviso-config revert [OPTIONS] SERVICE

  Revert all files associated with the service defined to the previous
  version.

Options:
  -H, --host TEXT      Configuration server host.
  -P, --port INTEGER   Configuration server port.

```
An example of use is the following:
```
$ aviso-config revert aviso/v1
```
Note that if this command is run twice consecutively results in no changes to the files on the server but the version 
will be incremented.

<a name="status"></a> 
### Status
The status operation is used to retrieve the status of a specific service.
```
Usage: aviso-config status [OPTIONS] SERVICE

  Retrieve the status of the service defined.

Options:
  -H, --host TEXT      Configuration server host.
  -P, --port INTEGER   Configuration server port.

```
An example of use is the following:
```
$ aviso-config status aviso/v1
```
this would return something on these lines:
```
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
```

<a name="case-study---aviso-service"></a> 
### Case study - Aviso Service

As mentioned, the aviso-config functionality is used also for the Aviso service itself.
Specifically, the Aviso service uses aviso-config to dynamically pull the system configuration files such as the event 
listener schema at the beginning of every listening operation.

This allows this schema to be shared with any notification source. Each notification source is required to comply with 
the notification format otherwise the notification will be wrongly filtered out by the listeners.

The notification source can use the `aviso-config pull` command to retrieve the configuration files or a REST interface
provided by the server. The server is currently implemented as a `etcd` cluster. 

The REST interface is `etcd` native. Here how to use it:

First an authentication token is required:

```
$ curl -L http://<host>/v3/auth/authenticate -X POST -d '{"name": "<user>", "password": "<password>"}'
```
this returns:
```
{
    "header":{
        "cluster_id":"11503685501326358934",
        "member_id":"12315796303939566423",
        "revision":"188560",
        "raft_term":"5"
    },
    "token":"<TOKEN>"
}
```
This request assumes the server is available in HTTP with no extra authentication, in case of ECMWF authentication, the 
ECMWF key has to be passed in the `X-ECMWF-Key` header. 

Assuming we want to retrieve the configuration files for the service `aviso/v1`, the endpoint has to be base64 encoded. We also 
need to specify the `range end` of our pull. Without going too much in details on how the etcd key store is built, what 
we need here is just to append a `0` at the end of the endpoint as shown below.
```
$ echo -n /ec/config/aviso/v1 | base64
L2VjL2NvbmZpZy9hdmlzby92MQ==

$ echo -n /ec/config/aviso/v10 | base64
L2VjL2NvbmZpZy9hdmlzby92MTA=
```
Note the `-n`. This is needed to avoid a newline character at end of the output.

The following is the REST call to perform an atomic pull of the configuration files:
```
$ curl -L http://<host>/v3/kv/range -H 'Authorization: <TOKEN>' \
-X POST -d '{"key": "L2VjL2NvbmZpZy9hdmlzby92MQ==", "range_end": "L2VjL2NvbmZpZy9hdmlzby92MTA="}'
```
this returns a list of key-value pairs. Each configuration file is stored in the value as base64 encoded that can be 
visualised on the shell by: 
```
$ echo <value> | base64 -d
```
Note that among these files there is also the status json file that gives information on the last push to this service.
