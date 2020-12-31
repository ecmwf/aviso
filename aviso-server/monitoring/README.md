# Aviso Monitoring

This package allows the implementation of the monitoring system designed for the Aviso service.
It is a library that any other components can use either for:
- Collecting telemetries inside the component application, aggregate them and send them via UDP package
- Collecting telemetries from other components via a UDP server, aggregate and evaluate them and send them to a monitoring server.

The first capability is currently used by the components Aviso Rest and Aviso Auth.
The second capability is used by the Aviso Admin component.

Install it by, from the main project directory: 

```
 % pip install -e aviso-server/monitoring
```