# Aviso Authentication Proxy

Aviso Authentication Proxy is a web application implementing a proxy responsible for authenticating the end-users' 
requests directed to the etcd cluster. This allows to not rely on the etcd native authentication and authorisation 
capability while using ECMWF centralised resources. It follows a 2-steps process:
 1. The request is validated against the ECMWF authentication server by checking the token associated to the request.
 1. The user associated to the token is checked if he can access to the resource is asking notifications for. This is
 performed by requesting the allowed resources associated to the user from the ECMWF authorisation WebAPI.


For more information on the implementation please refer to the <a href="https://confluence.ecmwf.int/display/~maci/Aviso+Authorisation+Proxy" target="_top">architecture diagram</a>.