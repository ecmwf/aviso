# Development

## Installation
After cloning the Git repository, follow these steps:
1. Setup the virtual environment (this assumes virtualenv is already installed):
    ```
    $ virtualenv -p python3 envName
    ```
    envName can be a folder of your project or outside of it.

1. Activate the virtual env
    ```
    $ source envName/bin/activate
    ```
1. Install all the dependencies needed included those for testing.
    ```
    $ pip3 install --ignore-installed -r dev_requirements.txt
    ```
1. Install setup tools from inside the project directory
    ```
    $ pip install --editable .
    ```

## Run

You can the application from the terminal:
```
$ aviso -h
```
this has to be executed from inside the project directory.

For debugging from your IDE, use any of the integration tests in `tests/integration`

## Tools

* Unit tests can be run with `pytest` with:
    ```
    $ pytest -v --cov=ecmwf_aviso --cov-report=html --cache-clear
    ```
* Enforcing PEP8 code style by running `black` with:
    ```
    $ black --line-length=120 ecmwf_aviso
    ```

## Design
A system design diagram is available at https://confluence.ecmwf.int/display/DS/aviso+Design