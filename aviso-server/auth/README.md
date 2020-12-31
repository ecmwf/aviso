# Aviso Auth

Aviso Auth is a web application implementing a proxy responsible for authenticating the end-users' 
requests directed to the store. This allows to not rely on the store native authentication and authorisation 
capability while using ECMWF centralised resources. It follows a 2-steps process:
 1. The request is validated against the ECMWF authentication server by checking the token associated to the request.
 1. The user associated to the token is checked if he can access to the resource is asking notifications for. This is
 performed by requesting the allowed resources associated to the user from the ECMWF authorisation server.
If both steps are successful the request is forwarded to the store.

Note that currently only the _listen_ command is allowed by this component. Any other operation is not authorised.

Install it by, from the main project directory: 

```
 % pip install -e aviso-server/monitoring
 % pip install -e aviso-server/auth
```
The aviso-monitoring package is required by aviso-auth.

Launch it by:

```
% aviso-auth
```