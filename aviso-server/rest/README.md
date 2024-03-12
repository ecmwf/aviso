# Aviso Rest

This component is a REST frontend that allows notification providers to submit notifications to the Aviso service 
via REST. Internally it uses Aviso API as if it is a client towards the notification store.

Run the following commands in the main project directory to install aviso-rest:
```
 % pip install -e .
 % pip install -e aviso-server/monitoring
 % pip install -e aviso-server/rest
```
The aviso and aviso-monitoring packages are required by aviso-rest.

Aviso rest can be launched by:

```
% aviso-rest
```