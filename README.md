# Aviso

> [!WARNING]
> **This repository is deprecated and will be archived soon. It is no longer maintained.**
>
> Aviso has been re-engineered and is now developed as two separate, actively
> maintained projects. Please migrate to them — this repository (the legacy
> `pyaviso` client and bundled server) will receive no further updates.
>
> | | Source code | Documentation |
> | --- | --- | --- |
> | **Aviso server** | <https://github.com/ecmwf/aviso-server> | <https://sites.ecmwf.int/docs/aviso-server/main/> |
> | **Aviso client** | <https://github.com/ecmwf/aviso-client> | <https://sites.ecmwf.int/docs/aviso-client/main/> |
>
> The Python client continues from the `aviso-client` project. Existing
> `pyaviso` users should follow the migration guidance in its documentation.

Aviso is a software developed by ECMWF that allows the notification of  **time-critical events** across HPC and Cloud systems in 
order to enable workflows among multiple domains.

It allows users to:

* Define events that require notification
* Define triggers to be executed once a notification is received
* Send and receive notifications

This enables the creation of automatic workflows, timely triggered as events are notified.
 

The documentation can be found at https://pyaviso.readthedocs.io/ \
Examples demonstrating the usage of aviso for ECMWF notifications can be found at https://github.com/ecmwf/aviso-examples