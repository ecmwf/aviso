# Install

## Installation on EWC image  `Ubuntu 18.04.4 ECMWF built`

1. Prepare the python3 environment needed
    ```
    $ sudo apt update
    $ sudo apt install build-essential
    $ sudo apt-get install python3-dev
    $ sudo apt-get install python3-pip
    $ sudo pip3 install setuptools 
    $ sudo pip3 install wheel 
    ```
1. Install Aviso
    ```
    $ sudo pip3 install -e git+https://git.ecmwf.int/scm/lex/aviso.git@master#egg=aviso    
    ```
## Installation on EWC image `CentOS 7.5 with Mars client`

1. Prepare the python3 environment needed
    ```
    $ sudo yum update
    
    $ sudo yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    
    $ sudo yum -y install python36u
    ```
1. Install Aviso, from the Aviso folder
    ```
    $ sudo pip3 install -e git+ssh://git@git.ecmwf.int/lex/aviso.git@master#egg=aviso    
    ```