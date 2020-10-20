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

<a name="listen"></a> 
### Listen
This command allows to application to enter in listening mode:
```
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
```

Below an example of how to run the application. We assume the configuration is done all by environment variables and/or
configuration file.

```
$ aviso listen examples/echoListener.yaml
``` 
Note the yaml file added as a parameter. It is used to define the event listeners and the triggers to execute in case 
of notifications. If not present the system will look for the default listeners which can be 
defined in the configuration files. Multiple files can also be indicated. Once in execution this command will create a 
background process waiting for notifications and a foreground process in busy waiting mode.

The user can terminate the application by typing:

```
CTRL+C, CTRL+D, CTRL+\
```

<a name="service"></a> 
#### Running as a service
Aviso can be executed as a system service. In this case, it can run under the same user or under a different user. 
In the latter users would refer to the configuration file 
in the system directory _/etc/aviso/config.yaml_ and they would add a system logging path in there.
The following steps are required to configure Aviso to run as a service that would automatically restart:

1. Identify the location of the Aviso executable:
    ```
    $ whereis aviso
    ```
1. Create a system service unit, by creating the following file in _/etc/systemd/system/aviso.service_:
    ```
    [Unit]​
    Description=Aviso​
    
    [Service]​
    User = <username> (if omitted it will run as root)
    Group= <groupname> (optional)
    WorkingDirectory= <home_directory> (optional)
    ExecStart=<aviso_location> listen​
    Restart=always
    
    [Install]​
    WantedBy=multi-user.target​
    ```
1. Enable the aviso service:
    ```
    $ sudo systemctl enable aviso.service​
    ```
1. Reload systemd:
    ```
    $ sudo systemctl daemon-reload​
    ```
1. Start the service:
    ```
    $ sudo systemctl start aviso.service
    ```
Note that if the user changes the Aviso configuration the Aviso service must be restarted otherwise the change will be 
ineffective.

<a name="catch-up"></a> 
#### Catch-up feature
Aviso can also replay past notifications. The user can retrieve notifications from the ECMWF server of several days 
before. This can also be used to test the listener configuration with real notifications.​

Here an example, launch Aviso with the following options:​

```
$ aviso listen your_listener.yaml --from 2020-01-20T00:00:00.0Z --to 2020-01-21T00:00:00.0Z
```

It will replay all the notifications sent from 20 January to 21 January and the ones complying with 
the listener request will execute the triggers.

Note that the dates must be in the past and `--to` can only be defined together with `--from`. The dates are defined in 
ISO format and they are in UTC.

In absence of `--to`, the system after having retrieved the past notifications, it ​will continue listening for future 
notifications. If `--to` is defined Aviso will terminate once retrieved all the past notifications.

In absence of `--from` and `--to`, Aviso before starting listening for new notifications, checks what was the last 
notification received and it will then return immediately all the notifications that have been missed since. It will 
then continue listening for new ones. The first ever time the application runs however no previous notification will be
returned. This behaviour is obtained by saving the state of the last notification received in 
~/.aviso/last/revision.yaml_. If users want to reset the state, they have to delete the file.


#### Defining the Listener
Here a basic example of the `dissemination` event listener file structure:
```
listeners:
  - event: dissemination
    request:
      destination: FOO
      stream: enfo
      step: [1,2,3]
    triggers:
      - type: echo
```
`listeners` is a list of event listeners. Each listener is defined by an event type that defines the structure of the 
listener request. The `request` describes for which events the users
want to be notified and to execute the triggers. It is made by a list of attributes. The users have to specify only the 
attributes that they wants to use as filters. Each attribute accepts one or multiple values as list. 
Only the notifications complying with all filters defined will execute the triggers.

The `triggers` keyword defines the list of triggers to execute.

Multiple listener files can be passed as argument, moreover multiple listeners can be defined in the same file, as below:
```
listeners:
  - event: dissemination
    request:
      destination: FOO
      stream: enfo
      date: 20190810
      step: [1]
    triggers:
      - type: echo

  - event: dissemination
    request:
      destination: FOO
      stream: enfo
      date: 20190810
    triggers:
      - type: echo

  - event: dissemination
    request:
      destination: FOO
      stream: enfo
    triggers:
      - type: echo

```
##### Event Listeners types

* The `dissemination` event listener is designed to notify about product generation. 
In this case the only mandatory attribute in the `request` is the `destination` field. 
Note that a notification received by a `dissemination` listener will contain the field `location` containing the URL to 
the product notified.

* The `mars` event listener is designed for real-time data from the model output. In this case the `request`
does not have the `destination` field and has no mandatory fields. Moreover the notification received by this listeners
will not contain the `location` field because the users will be able to access to it by the conventional MARS API. 

For the full list of values accepted refer to the schema at _~/.aviso/service_configuration/event_listener_schema.yaml_. 
Note that this schema is dynamically retrieved by the application from the configuration server at every operation. 
Run the application once to populate this location.
 

#### Triggers
There are a number of triggers defined in the system, each accepts different parameters. 
Below a list of the current implementation.

##### Echo
This is the most basic trigger as it simply prints the notification to the console output. It does not accept any 
extra parameters.
```    
triggers:
  - type: echo
```

##### Log
This trigger logs the event to the log file specified. Please note that it will fail if the directory does not exist.
```    
triggers:
  - type: log
    path: testLog.log

```

##### Command
This trigger allows the user to define a command to be executed in shell once a notification is received. 
```    
triggers:
  - type: command
    working_dir: $HOME/aviso/examples
    command: ./script.sh --date ${request.date} -s ${request.stream}
    environment:
      STEP: ${request.step}
      TIME: "The time is ${request.time}"

```
The trigger requires the `command` field, this will be executed for each notification received. 

`environment` is a user defined list of local variables that will be passed to the command shell. This is an optional 
field.

`working_dir` defines the working directory that will be set before executing the command. This is an optional field.

Moreover, the system performs a parameter substitution. Every sequence of the patterns `${name}` in the command and 
environment attributes are substituted with the value found in the corresponding notification.

An example can be executed by:
```
$ aviso listen examples/commandListener.yaml
```

The notification is a dictionary and key can be used in the parameter substitution mechanism described above. Here 
an example of the dictionary:
```
{
    "event": "dissemination",
    "request": {
        "class": "od",
        "date": "20191112",
        "destination": "FOO",
        "domain": "g",
        "expver": "0001",
        "step": "001",
        "stream": "enfo",
        "time": "18"
    },
    "location": "https://xxx.ecmwf.int/xxx/xxx.xx"
}    
```

The full notification data structure can be passed in the command by using the keyword ${json} that will translate the 
structure in a JSON inline string. 
An example can be executed by:
```
$ aviso listen examples/commandJsonListener.yaml
```

Finally, the notification data structure can be directly saved to a JSON file. The file name can be retrieved using the 
keyword ${jsonpath}
An example can be executed by:
```
$ aviso listen examples/commandJsonPathListener.yaml
```

##### Python Function
Differently from the previous triggers, this trigger is not file based. It allows the user to define a Python function 
to be executed directly by Aviso. This is intended for users that want to integrate Aviso in a bigger workflow written 
in Python or that simply have their trigger defined as a Python function. 

Below an example of a python script that defines a function to be executed once a notification is received, 
creates a listener that references to this function trigger and finally passes it to aviso to execute.

The listening will happen in a background thread defined as daemon therefore it is responsibility of the user to keep 
the main thread alive.

```
from pyaviso import NotificationManager

# define function to be called
def do_something(notification):
    # do something with the notification
    ...

# define the trigger
trigger = {"type": "function", "function": do_something}

# create a event listener request that uses that trigger
request = {"destination": "FOO", "stream": "enfo", "date": 20190810, "time": 0}
listener = {"event": "dissemination", "request": request, "triggers": [trigger]}
listeners = {"listeners": [listener]}

# run it
aviso = NotificationManager()
aviso.listen(listeners=listeners)

# wait ...
```

<a name="key"></a> 
### Key
This command can be used to generate the key accepted by the notification server as part of the notification key-value 
pair.
```
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
```
Here an example of this command:
```
$ aviso key event=dissemination,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0
```
Note the various parameters required by the notification. The output from this command will be something like:
```
/ec/diss/FOO/class=od,expver=0001,domain=g,date=20190810,time=00,stream=enfo,step=001
```
Note how the format and the order of the parameters have been adjusted to complying with the key schema.

<a name="value"></a> 
### Value
This command is used to retrieve from the server the value associated to a set of key-value pairs using the same syntax 
of the command _key_
```
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
```
Here an example of this command:
```
$ aviso value event=dissemination,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0
```
Note the list of parameters required, it is the same list required by the _key_ command.

<a name="notify"></a> 
### Notify
This command is used to directly send a notification to the server using the same syntax of the command _key_
```
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
```
Here an example of this command:
```
$ aviso notify event=dissemination,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0,location=xxxxxxxx
```
Note the list of parameters required, it is the same list required by the _key_ command with the addition of the `location` 
pair. This is needed only for the `dissemination` event. 

In the case of a `mars` event the command looks like this:
```
$ aviso notify event=mars,class=od,date=20190810,domain=g,expver=1,step=1,stream=enfo,time=0
```
with no `destination` and `location` pair.


#### Notifying using the Python API
The command presented above can be equally executed from the Python API. This is intended for users that want to send 
notifications from custom workflow written in Python. The script below briefly shows how.
```
from pyaviso import NotificationManager

aviso = NotificationManager()

# define the parameters of the notification
params = "event=dissemination,class=od,date=20190810,destination=FOO,domain=g,expver=1,step=1,stream=enfo,time=0,location=xxx"

# send the notification
aviso.notify(params)
```

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
