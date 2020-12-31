# Aviso Rest

This component is a REST frontend that allows notification providers to submit notifications to the Aviso service 
via REST. Internally it uses Aviso API as if it was a client towards the store.

Install it by, from the main project directory:
```
 % pip install -e .
 % pip install -e aviso-server/monitoring
 % pip install -e aviso-server/rest
```
The aviso and aviso-monitoring packages are required by aviso-rest.

Launch it by:

```
% aviso-rest
```

