# Aviso Admin

This component performs maintenance operations to the store in order to keep it at constant size.
Currently the implementation is specific for an etcd store. This store requires the following operations:
- Compaction, this operation removes the history older than a certain date
- Deletion, this operation deletes all the keys older than a certain date

This component also uses the _monitoring_ package to run a UDP server to receive telemetries from all the other
components on the server. It runs a periodic aggregation and evaluation of these telemetries and it 
then communicates the status of the components to the ECMWF monitoring server.


Install it by, from the main project directory: 

```
 % pip install -e aviso-server/monitoring
 % pip install -e aviso-server/admin
```
The aviso-monitoring package is required by aviso-admin.

Launch it by:

```
% aviso-admin
```